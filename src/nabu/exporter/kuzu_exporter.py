import logging
from typing import List, Dict, Any, Optional
import logging
import asyncio
import kuzu
import pandas as pd
from pathlib import Path

from nabu.embeddings import EmbeddingModel, EmbeddingGenerator

try:
    import kuzu
except ImportError:
    raise ImportError("kuzu package not available. Install with: pip install kuzu")

from nabu.core.frames import AstFrameBase, AstEdge


logger = logging.getLogger(__name__)


class KuzuDbExporter:
    """
    Export frame hierarchy and edges to KuzuDB.
    """

    def __init__(self, context=None):
        # Connection management now handled via KuzuConnectionManager
        # No persistent db/conn maintained by this class
        self.context = context  # Optional: CodebaseContext for registry-based export
        
        # Initialize embedding generators (lazy loaded on first use)
        self._embedding_generators: Dict[EmbeddingModel, EmbeddingGenerator] = {}
    
    @property
    def insertion_batch_size(self) -> int:
        return 1000
    
    @property
    def embedding_batch_size(self) -> int:
        return 8

    def _get_generator(self, model: EmbeddingModel) -> EmbeddingGenerator:
        """Lazy-load embedding generator for specific model."""
        if model not in self._embedding_generators:
            from nabu.embeddings import (
                get_unixcoder_generator,
                get_codebert_generator
            )

            if model == EmbeddingModel.UNIXCODER:
                self._embedding_generators[model] = get_unixcoder_generator()
            elif model == EmbeddingModel.CODEBERT:
                self._embedding_generators[model] = get_codebert_generator()
            else:
                raise ValueError(f"Unsupported model: {model}")

        return self._embedding_generators[model]

    def create_database(self, codebase_frame: AstFrameBase, edges: List[AstEdge], db_path: str, context=None) -> None:
        """
        Create KuzuDB database with frame hierarchy and edges.
        
        Args:
            codebase_frame: Root frame (used as fallback if context not available)
            edges: List of edges to export
            db_path: Path to database file
            context: Optional CodebaseContext for registry-based export (recommended)
        """
        from nabu.db import KuzuConnectionManager
        
        logger.info(f"Creating KuzuDB database at: {db_path}")

        # CRITICAL: Close any existing manager for this path BEFORE deleting the database
        # This prevents stale singleton cache issues
        normalized_path = str(Path(db_path).resolve())
        if normalized_path in KuzuConnectionManager._instances:
            logger.info(f"Closing existing manager for {db_path}")
            KuzuConnectionManager._instances[normalized_path].close()
            # close() already removes from _instances
        
        # Remove existing database file if it exists
        db_path_obj = Path(db_path)
        if db_path_obj.exists():
            if db_path_obj.is_dir():
                raise RuntimeError(f"Found directory in db_path '{db_path}'")
            else:
                logger.info(f"Removing existing database file: {db_path}")
                db_path_obj.unlink()  # Remove file if it's not a directory
                db_path_obj.with_suffix(".wal").unlink(missing_ok=True)
                db_path_obj.with_suffix(".wal.shadow").unlink(missing_ok=True)
        
        # Get singleton Database manager (this will create the new empty database)
        db_manager = KuzuConnectionManager.get_instance(db_path)

        # Use context manager for connection lifecycle
        # NOTE: _create_schema loads extensions (bundled in Kuzu 0.11.3)
        with db_manager.connection(load_extensions=False) as conn:
            # Create schema
            self._create_schema_with_connection(conn)

            # Extract and export data using registry-based approach if context available
            # This fixes the 89% frame loss bug caused by multi-parent deduplication
            logger.info(f"Collecting frames")
            frames_data = self._extract_frames_data(codebase_frame, context or self.context)
            logger.info(f"Collected {len(frames_data)} frames from registries")

            logger.info(f"Collecting edges")
            edges_data = self._extract_edges_data(edges)
            logger.info(f"Collected {len(edges_data)} edges from registries")

            logger.info(f"Inserting frames")
            self._bulk_insert_frames_with_connection(conn, frames_data)

            logger.info(f"Inserting edges")
            self._bulk_insert_edges_with_connection(conn, edges_data)

        logger.info(f"Database created with {len(frames_data)} frames and {len(edges_data)} edges")

    def _create_schema_with_connection(self, conn: kuzu.Connection) -> None:
        """
        Create the 2-table schema with STRUCT support for fields/parameters.
        
        Args:
            conn: Active connection to use
        """

        # Extensions bundled in Kuzu 0.11.3 - no INSTALL needed, just LOAD
        try:
            conn.execute("LOAD ALGO;")
        except Exception as e:
            pass  # probably loaded
        
        try:
            conn.execute("LOAD FTS;")
        except Exception as e:
            pass  # probably loaded
        
        try:
            conn.execute("LOAD VECTOR;")
        except Exception as e:
            pass  # probably loaded

        # Create Frame node table with STRUCT columns
        frame_schema = """
        CREATE NODE TABLE Frame(
            id STRING PRIMARY KEY,
            type STRING,
            name STRING,
            qualified_name STRING,
            confidence FLOAT,
            confidence_tier STRING,
            provenance STRING,
            resolution_pass INT,
            language STRING,
            file_path STRING,
            start_line INT,
            end_line INT,
            start_byte INT,
            end_byte INT,
            content STRING,
            heading STRING,
            
            instance_fields STRUCT(
                name STRING,
                declared_type STRING,
                line INT,
                confidence FLOAT
            )[],
            
            static_fields STRUCT(
                name STRING,
                declared_type STRING,
                line INT,
                confidence FLOAT
            )[],
            
            parameters STRUCT(
                name STRING,
                declared_type STRING,
                default_value STRING,
                position INT
            )[],
            
            return_type STRING,
            embedding_non_linear_consensus FLOAT[768],
            metadata STRING
        )
        """

        conn.execute(frame_schema)

        # Create Edge relationship table
        edge_schema = """
        CREATE REL TABLE Edge(
            FROM Frame TO Frame,
            type STRING,
            confidence FLOAT,
            confidence_tier STRING,
            metadata JSON
        )
        """
        conn.execute(edge_schema)

    
        conn.execute("""
            CALL CREATE_FTS_INDEX(
                'Frame',
                'frame_fts_index',
                ['type', 'language', 'confidence_tier', 'content'],
                stemmer := 'porter'
            );
        """)

        conn.execute("""
            CALL CREATE_FTS_INDEX(
                'Frame',
                'frame_resolution_fts_index',
                ['name', 'qualified_name', 'file_path'],
                stemmer := 'porter'
            );
        """)
        
        logger.debug("Creating vector index for P³ consensus embeddings...")
        conn.execute("""
            CALL CREATE_VECTOR_INDEX(
                'Frame',
                'frame_embedding_non_linear_consensus_idx',
                'embedding_non_linear_consensus',
                metric := 'cosine'
            );
        """)

        logger.debug("Database schema created with STRUCT support, FTS index, and vector index")

    def _extract_frames_data(self, codebase_frame: AstFrameBase, context=None) -> List[Dict[str, Any]]:
        """
        Extract frame data for bulk insertion with batched embedding generation.

        Args:
            codebase_frame: Root frame (used for fallback traversal)
            context: Optional CodebaseContext with registries
        """
        if context and hasattr(context, 'get_all_frames'):
            logger.info("Using registry-based frame collection with batched embeddings")
            all_frames = context.get_all_frames()
            
            # Use asyncio.run() to execute async batch embedding generation
            frames_data = asyncio.run(self._extract_frames_data_with_batch_embeddings(all_frames))
            
            return frames_data
        else:
            # FALLBACK: Tree traversal (has multi-parent bug, sequential embeddings)
            logger.warning("Context not provided - using tree traversal (may lose frames in multi-parent graphs)")
            logger.warning("Sequential embedding generation will be slower (no batching)")
            frames_data = []
            visited = set()
            self._extract_frame_recursive(codebase_frame, frames_data, visited, inherited_file_path="")
            return frames_data

    async def _extract_frames_data_with_batch_embeddings(
        self,
        all_frames: List[AstFrameBase]
    ) -> List[Dict[str, Any]]:
        """
        Extract frame data with P3 consensus embeddings (UX×CB).

        Process:
        1. Generate embeddings from UniXcoder and CodeBERT in parallel
        2. Apply Pythagorean³ consensus fusion (proven approach)
        3. Store results in embedding_non_linear_consensus column

        Args:
            all_frames: List of all frames from registry

        Returns:
            List of frame data dictionaries with embeddings populated
        """
        logger.info(f"Extracting data for {len(all_frames)} frames with P3 consensus")

        callable_frames = [f for f in all_frames if f.type.value == 'CALLABLE']
        logger.info(f"Found {len(callable_frames)} CALLABLE frames")

        from nabu.embeddings.base import compute_non_linear_consensus

        if callable_frames:
            # Generate embeddings in parallel (proven UX×CB approach)
            ux_gen = self._get_generator(EmbeddingModel.UNIXCODER)
            cb_gen = self._get_generator(EmbeddingModel.CODEBERT)

            logger.info(f"Generating embeddings for {len(callable_frames)} frames")
            ux_embeddings, cb_embeddings = await asyncio.gather(
                ux_gen.generate_embeddings_batch(callable_frames, batch_size=self.embedding_batch_size),
                cb_gen.generate_embeddings_batch(callable_frames, batch_size=self.embedding_batch_size)
            )

            # Apply Pythagorean³ consensus (experimentally validated)
            logger.info("Applying Pythagorean³ consensus (UX×CB)")
            consensus_embeddings = [
                compute_non_linear_consensus(ux, cb) if ux and cb else None
                for ux, cb in zip(ux_embeddings, cb_embeddings)
            ]

            valid_count = sum(1 for e in consensus_embeddings if e)
            logger.info(f"P3 consensus complete: {valid_count}/{len(consensus_embeddings)} valid embeddings")
        else:
            ux_embeddings = []
            cb_embeddings = []
            consensus_embeddings = []

        # Build embedding lookup
        embedding_map = {}
        for idx, frame in enumerate(callable_frames):
            embedding_map[frame.id] = {
                'unixcoder': ux_embeddings[idx],
                'codebert': cb_embeddings[idx],
                'consensus': consensus_embeddings[idx]
            }

        # Extract frame data and attach embeddings
        frames_data = []
        for frame in all_frames:
            frame_data = self._extract_single_frame_data(frame, generate_embeddings=False)

            if frame.id in embedding_map:
                frame_data['embedding_non_linear_consensus'] = embedding_map[frame.id]['consensus']

            frames_data.append(frame_data)

        logger.info(f"Frame data extraction complete: {len(frames_data)} frames")
        return frames_data

    def _extract_single_frame_data(self, frame: AstFrameBase, generate_embeddings: bool = True, embedding_model: Optional[EmbeddingModel] = None) -> Dict[str, Any]:
        """
        Extract data for a single frame including STRUCT fields.
        
        Args:
            frame: Frame to extract
            generate_embeddings: Whether to generate embeddings
            embedding_model: If specified, only generate for this model
        
        Extracted from _extract_frame_recursive to enable registry-based collection.
        """
        import json
        from nabu.core.frames import AstClassFrame, AstCallableFrame
        
        # Convert metadata to JSON string
        metadata_str = json.dumps(frame.metadata) if frame.metadata else "{}"
        
        # Extract STRUCT arrays
        instance_fields = []
        static_fields = []
        parameters = []
        return_type = ""
        
        if isinstance(frame, AstClassFrame):
            instance_fields = [f.to_dict() for f in frame.instance_fields] if frame.instance_fields else []
            static_fields = [f.to_dict() for f in frame.static_fields] if frame.static_fields else []
        
        elif isinstance(frame, AstCallableFrame):
            parameters = [p.to_dict() for p in frame.parameters] if frame.parameters else []
            return_type = frame.return_type or ""
        
        # Build base frame data, fields need to have same order as DDL
        frame_data = {
            'id': frame.id,
            'type': frame.type.value,
            'name': frame.name,
            'qualified_name': frame.qualified_name,
            'confidence': frame.confidence,
            'confidence_tier': frame.confidence_tier.value,
            'provenance': frame.provenance,
            'resolution_pass': frame.resolution_pass,
            'language': frame.language,
            'file_path': frame.file_path,
            'start_line': frame.start_line,
            'end_line': frame.end_line,
            'start_byte': frame.start_byte,
            'end_byte': frame.end_byte,
            'content': frame.content,
            'heading': frame.heading,
            'instance_fields': instance_fields,
            'static_fields': static_fields,
            'parameters': parameters,
            'return_type': return_type,
            'embedding_non_linear_consensus': None,
            'metadata': metadata_str
        }
        
        ux_gen = self._get_generator(EmbeddingModel.UNIXCODER)
        cb_gen = self._get_generator(EmbeddingModel.CODEBERT)

        # Initialize embedding fields with zero arrays (KuzuDB requires exactly 768 elements)
        
        # Generate embeddings for CALLABLE frames
        if generate_embeddings and frame.type.value == 'CALLABLE':
            try:
                # Generate UniXcoder embedding (ephemeral - used for P³ consensus only)
                ux_embedding = ux_gen.generate_embedding_from_ast_frame(frame)

                # Generate CodeBERT embedding (for fusion only, not persisted)
                cb_embedding = cb_gen.generate_embedding_from_ast_frame(frame)

                # Compute fusion embeddings if both base embeddings are available
                if ux_embedding and cb_embedding:
                    try:
                        from nabu.embeddings.base import compute_non_linear_consensus

                        frame_data['embedding_non_linear_consensus'] = compute_non_linear_consensus(
                            ux_embedding,
                            cb_embedding
                        )
                        logger.debug(f"Computed fusion embeddings for {frame.qualified_name}")
                    except Exception as e:
                        logger.warning(f"Failed to compute fusion embeddings for {frame.qualified_name}: {e}")

                if ux_embedding or cb_embedding:
                    logger.debug(f"Generated embeddings for {frame.qualified_name}")
            except Exception as e:
                logger.warning(f"Failed to generate embeddings for {frame.qualified_name}: {e}")

        # Set content to None for control flows (heading already has the info)
        if frame.type.is_control_flow():
            frame_data['content'] = None

        return frame_data

    def _extract_frame_recursive(self, frame: AstFrameBase, frames_data: List[Dict[str, Any]], visited: set, inherited_file_path: str = "") -> None:
        """
        Recursively extract frame data (LEGACY - has multi-parent bug).

        Skips frames that have already been visited to handle multi-parent graphs
        where a single frame can appear as a child of multiple parents.
        
        WARNING: This approach loses ~89% of frames in multi-parent graphs.
        Use registry-based collection (_extract_frames_data with context) instead.
        
        Propagates file_path from FILE nodes to all descendants.
        """
        # Skip if already visited (handles multi-parent graphs)
        if frame.id in visited:
            return
        visited.add(frame.id)

        # Determine file_path: use frame's own if present, else inherit from parent
        current_file_path = frame.file_path if frame.file_path else inherited_file_path

        # Use the shared extraction method
        frame_data = self._extract_single_frame_data(frame)
        # Override file_path with inherited value if needed
        frame_data['file_path'] = current_file_path
        
        frames_data.append(frame_data)

        # Recursively process children, passing down file_path
        for child in frame.children:
            self._extract_frame_recursive(child, frames_data, visited, current_file_path)

    def _extract_edges_data(self, edges: List[AstEdge]) -> List[Dict[str, Any]]:
        """Extract edge data for bulk insertion."""
        edges_data = []
        for edge in edges:
            edge_data = {
                'subject_frame_id': edge.subject_frame.id,
                'object_frame_id': edge.object_frame.id,
                'type': edge.type.value,
                'confidence': edge.confidence,
                'confidence_tier': edge.confidence_tier.value,
                'metadata': edge.metadata if edge.metadata else {}
            }
            edges_data.append(edge_data)

        return edges_data

    def _bulk_insert_frames_with_connection(self, conn: kuzu.Connection, frames_data: List[Dict[str, Any]]) -> None:
        """
        Bulk insert frames with data sanitization and error handling.
        
        Args:
            conn: Active connection to use
            frames_data: List of frame data dictionaries
        
        Addresses KuzuDB Python binding bugs with special characters and long strings.
        """
        if not frames_data:
            logger.warning("No frames data to insert")
            return

        # Sanitize data before DataFrame creation
        sanitized_data = []
        for frame_data in frames_data:
            sanitized_frame = self._sanitize_frame_data(frame_data)
            sanitized_data.append(sanitized_frame)

        # Use batched insertion as primary strategy (more reliable than all-at-once)
        total_frames = len(sanitized_data)
        batch_size = self.insertion_batch_size
        successful = 0
        failed_frames = []
        
        logger.info(f"Inserting {total_frames} frames in batches of {batch_size}...")
        
        for i in range(0, total_frames, batch_size):
            batch = sanitized_data[i:i+batch_size]
            df_batch = pd.DataFrame(batch)
            
            try:
                conn.execute("COPY Frame FROM $df", {'df': df_batch})
                successful += len(batch)
                
                progress_pct = (successful * 100) // total_frames
                logger.info(f"Progress: {successful}/{total_frames} frames ({progress_pct}%)")
                    
            except Exception as batch_error:
                logger.warning(f"Batch {i//batch_size + 1} failed, trying individual inserts: {batch_error}")
                # Fall back to individual insertion for this batch only
                for frame_data in batch:
                    try:
                        df_single = pd.DataFrame([frame_data])
                        conn.execute("COPY Frame FROM $df", {'df': df_single})
                        successful += 1
                    except Exception as single_error:
                        logger.error(f"Failed to insert frame {frame_data.get('id', 'unknown')}: {single_error}")
                        failed_frames.append(frame_data.get('id', 'unknown'))
        
        logger.info(f"Frame insertion complete: {successful}/{total_frames} successful")
        if failed_frames:
            logger.warning(f"Failed to insert {len(failed_frames)} frames")
            logger.debug(f"Failed frame IDs: {failed_frames[:20]}...")

    def _sanitize_frame_data(self, frame_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize frame data to prevent KuzuDB conversion errors.
        
        Addresses:
        - Very long strings (truncate content)
        - Special characters causing encoding issues
        - Malformed STRUCT data
        - JSON metadata serialization for COPY FROM
        """
        import json
        
        sanitized = frame_data.copy()
        
        # Truncate content field if too long (KuzuDB may have limits)
        if sanitized.get('content') and len(sanitized['content']) > 50000:
            sanitized['content'] = sanitized['content'][:50000] + "... [truncated]"
        
        # Ensure all string fields are properly encoded
        for key in ['name', 'qualified_name', 'file_path', 'content', 'heading', 'return_type']:
            if sanitized.get(key) and isinstance(sanitized[key], str):
                try:
                    # Ensure UTF-8 compatibility, replace problematic chars
                    sanitized[key] = sanitized[key].encode('utf-8', errors='replace').decode('utf-8')
                except Exception:
                    sanitized[key] = ''
        
        # Serialize metadata to JSON string for COPY FROM (KuzuDB parses JSON columns from strings)
        if 'metadata' in sanitized:
            if isinstance(sanitized['metadata'], dict):
                sanitized['metadata'] = json.dumps(sanitized['metadata'])
            elif sanitized['metadata'] is None:
                sanitized['metadata'] = '{}'
        
        # Sanitize STRUCT arrays
        for struct_field in ['instance_fields', 'static_fields', 'parameters']:
            if sanitized.get(struct_field):
                sanitized[struct_field] = [
                    self._sanitize_struct_item(item) 
                    for item in sanitized[struct_field]
                ]

        return sanitized
    
    def _sanitize_struct_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize individual STRUCT items."""
        sanitized = {}
        for key, val in item.items():
            if isinstance(val, str):
                try:
                    sanitized[key] = val.encode('utf-8', errors='replace').decode('utf-8')
                    # Limit string length in STRUCT fields
                    if len(sanitized[key]) > 500:
                        sanitized[key] = sanitized[key][:500] + "..."
                except Exception:
                    sanitized[key] = ''
            else:
                sanitized[key] = val
        return sanitized
    
    def _bulk_insert_edges_with_connection(self, conn: kuzu.Connection, edges_data: List[Dict[str, Any]]) -> None:
        """
        Bulk insert edges using pandas DataFrame.
        
        Args:
            conn: Active connection to use
            edges_data: List of edge data dictionaries
        """
        import json
        
        if not edges_data:
            logger.warning("No edges data to insert")
            return

        # Convert to DataFrame
        df = pd.DataFrame(edges_data)
        
        # For COPY FROM, JSON columns must be JSON strings (KuzuDB parses them)
        if 'metadata' in df.columns:
            df['metadata'] = df['metadata'].apply(lambda x: json.dumps(x) if x else '{}')

        # Use KuzuDB's COPY FROM dataframe functionality
        conn.execute("COPY Edge FROM $df", {'df': df})
        logger.debug(f"Bulk inserted {len(edges_data)} edges")

 