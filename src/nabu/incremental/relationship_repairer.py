"""
Relationship Repairer

Repairs CALLS and IMPORTS edges affected by frame changes during incremental updates.

Strategy:
- Query database for target frames (instead of in-memory registries)
- Use language handlers to extract call sites and imports
- Create edges with proper confidence and metadata
"""

import logging
from typing import List, Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass, field

from nabu.core.frames import AstFrameBase, AstEdge
from nabu.core.frame_types import FrameNodeType, EdgeType
from nabu.core.confidence import ConfidenceCalculator
from nabu.core.pattern_confidence import adjust_field_usage_confidence
from nabu.core.resolution_strategy import DatabaseResolutionStrategy
from nabu.core.cpp_utils import extract_cpp_class_from_signature
from nabu.language_handlers import language_registry
from nabu.incremental.edge_inserter import EdgeInserter

logger = logging.getLogger(__name__)


@dataclass
class RepairResult:
    """Results from edge repair operation."""
    edges_deleted: int = 0
    edges_added: int = 0
    calls_edges_added: int = 0
    imports_edges_added: int = 0
    contains_edges_added: int = 0
    inherits_edges_added: int = 0  # Phase 3.1: INHERITS edge repair
    uses_edges_added: int = 0      # Phase 1: Field usage tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class RelationshipRepairer:
    """
    Repair CALLS and IMPORTS edges for changed frames.

    Unlike SymbolResolver (which uses in-memory registries), this class
    queries the database to resolve symbol names to frame IDs.

    This is necessary because during incremental updates, only the changed
    file is parsed - the rest of the codebase exists only in the database.
    """

    def __init__(self):
        """
        Initialize RelationshipRepairer.

        Connection is now passed to repair_edges() method instead of stored.
        This allows proper use of KuzuConnectionManager context managers.
        """
        # conn and resolution_strategy will be set in repair_edges()
        self.conn = None
        self.resolution_strategy = None

    def repair_edges(
        self,
        conn,
        diff: 'FrameDiff',
        file_path: str,
        parsed_edges: List[AstEdge]
    ) -> RepairResult:
        """
        Main orchestrator for edge repair.

        Strategy:
        1. Orphaned edges are already deleted by DETACH DELETE
        2. Recompute CALLS edges for changed CALLABLEs
        3. Recompute IMPORTS edges for changed PACKAGEs
        4. Recompute CONTAINS edges for added frames

        Args:
            conn: KuzuDB connection for querying and inserting
            diff: Frame diff with added/deleted/stable sets
            file_path: Path to changed file (for context)
            parsed_edges: All edges from parse_single_file() (includes CONTAINS)

        Returns:
            RepairResult with metrics
        """
        # Store connection temporarily for use by helper methods
        # This avoids refactoring all helper methods to pass conn as parameter
        self.conn = conn
        # Initialize resolution strategy with database connection
        self.resolution_strategy = DatabaseResolutionStrategy(conn)

        result = RepairResult()

        logger.info(f"Repairing edges for {len(diff.added_frames)} added frames")

        try:
            # Filter added frames for CALLABLEs
            changed_callables = [
                f for f in diff.added_frames
                if f.type == FrameNodeType.CALLABLE and f.content
            ]

            # Recompute CALLS edges
            if changed_callables:
                calls_edges_data = self.recompute_calls_edges(changed_callables)
                result.calls_edges_added = len(calls_edges_data)
                result.edges_added += len(calls_edges_data)

                # Insert edges if any created
                if calls_edges_data:
                    self._insert_edges_bulk(calls_edges_data)
                    logger.info(f"Created {len(calls_edges_data)} CALLS edges")

            # Filter added frames for PACKAGEs (for IMPORTS)
            changed_packages = [
                f for f in diff.added_frames
                if f.type == FrameNodeType.PACKAGE
            ]

            # Recompute IMPORTS edges
            if changed_packages:
                imports_edges_data = self.recompute_imports_edges(
                    changed_packages,
                    file_path
                )
                result.imports_edges_added = len(imports_edges_data)
                result.edges_added += len(imports_edges_data)

                # Insert edges if any created
                if imports_edges_data:
                    self._insert_edges_bulk(imports_edges_data)
                    logger.info(f"Created {len(imports_edges_data)} IMPORTS edges")

            # Recompute CONTAINS edges for added frames
            # These are the structural hierarchy edges (parent→child relationships)
            contains_edges_data = self.recompute_contains_edges(
                diff.added_frames,
                parsed_edges
            )
            result.contains_edges_added = len(contains_edges_data)
            result.edges_added += len(contains_edges_data)

            # Insert CONTAINS edges if any created
            if contains_edges_data:
                self._insert_edges_bulk(contains_edges_data)
                logger.info(f"Created {len(contains_edges_data)} CONTAINS edges")

            # DEBUG: Log added frames
            logger.info(f"Added frames ({len(diff.added_frames)}):")
            for af in diff.added_frames:
                logger.info(f"  - {af.type.value} {af.name} (id={af.id[:16]})")
            
            # Filter ALL frames (stable + added) for CLASSes (for INHERITS)
            # Note: CLASS frame content doesn't include inheritance declaration,
            # so adding/removing inheritance doesn't change the frame's stable ID.
            # We must recompute INHERITS for all classes in the file.
            stable_frames = [diff.new_id_to_frame[frame_id] for frame_id in diff.stable_ids]
            all_class_frames = stable_frames + diff.added_frames
            changed_classes = [
                f for f in all_class_frames
                if f.type == FrameNodeType.CLASS and f.content
            ]

            # Delete existing INHERITS edges from these classes first
            if changed_classes:
                class_ids = [f.id for f in changed_classes]
                delete_inherits_query = """
                    MATCH (child:Frame)-[e:Edge {type: 'INHERITS'}]->()
                    WHERE child.id IN $class_ids
                    DELETE e
                """
                self.conn.execute(delete_inherits_query, {'class_ids': class_ids})
                logger.debug(f"Deleted old INHERITS edges for {len(changed_classes)} classes")

            # Recompute INHERITS edges
            if changed_classes:
                logger.info(f"Recomputing INHERITS edges for {len(changed_classes)} classes")
                inherits_edges_data = self.recompute_inherits_edges(changed_classes)
                result.inherits_edges_added = len(inherits_edges_data)
                result.edges_added += len(inherits_edges_data)

                # Insert edges if any created
                if inherits_edges_data:
                    self._insert_edges_bulk(inherits_edges_data)
                    logger.info(f"Created {len(inherits_edges_data)} INHERITS edges")

            # Recompute USES edges for changed CALLABLEs
            # We reuse the same changed_callables from CALLS edge repair
            if changed_callables:
                uses_edges_data = self.recompute_uses_edges(changed_callables)
                result.uses_edges_added = len(uses_edges_data)
                result.edges_added += len(uses_edges_data)
                
                # Insert edges if any created
                if uses_edges_data:
                    self._insert_edges_bulk(uses_edges_data)
                    logger.info(f"Created {len(uses_edges_data)} USES edges")

            # Recompute C++ CLASS→CALLABLE edges for cross-file methods
            if changed_callables:
                cpp_parent_edges_data = self.recompute_cpp_method_parent_edges(changed_callables)
                result.edges_added += len(cpp_parent_edges_data)
                
                if cpp_parent_edges_data:
                    self._insert_edges_bulk(cpp_parent_edges_data)
                    logger.info(f"Created {len(cpp_parent_edges_data)} C++ method-parent edges")

            logger.info(
                f"Edge repair complete: {result.edges_added} edges added "
                f"({result.calls_edges_added} CALLS, {result.imports_edges_added} IMPORTS, "
                f"{result.contains_edges_added} CONTAINS, {result.inherits_edges_added} INHERITS, "
                f"{result.uses_edges_added} USES)"
            )

        except Exception as e:
            error_msg = f"Edge repair failed: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
        finally:
            # Clean up temporary connection reference
            self.conn = None

        return result

    def recompute_calls_edges(
        self,
        changed_callables: List[AstFrameBase]
    ) -> List[Dict[str, Any]]:
        """
        Recompute CALLS edges for changed CALLABLE frames.

        For each CALLABLE:
        1. Extract call sites using language handler
        2. Resolve callee names to frame IDs (database query)
        3. Create CALLS edge data

        Args:
            changed_callables: List of CALLABLE frames that changed

        Returns:
            List of edge data dictionaries for insertion
        """
        edges_data = []

        for caller_frame in changed_callables:
            # Get language handler
            handler = self._get_handler_for_frame(caller_frame)
            if not handler:
                logger.warning(f"No handler for frame {caller_frame.id} (language: {caller_frame.language})")
                continue

            # Extract call sites
            call_sites = self._extract_call_sites_for_frame(caller_frame, handler)

            if not call_sites:
                continue

            # Resolve each call to a target frame
            for callee_name, line_number in call_sites:
                callee_id = self._resolve_callable_by_name_in_db(
                    callee_name,
                    caller_frame
                )

                if callee_id:
                    # Create edge data
                    edge_data = {
                        'subject_frame_id': caller_frame.id,
                        'object_frame_id': callee_id,
                        'type': EdgeType.CALLS.value,
                        'confidence': 0.85,  # Default confidence for calls
                        'confidence_tier': 'HIGH',
                        'metadata': f'{{"line": {line_number}}}'
                    }
                    edges_data.append(edge_data)
                else:
                    logger.debug(f"Could not resolve call to '{callee_name}' from {caller_frame.qualified_name}")

        return edges_data

    def recompute_imports_edges(
        self,
        changed_packages: List[AstFrameBase],
        file_path: str
    ) -> List[Dict[str, Any]]:
        """
        Recompute IMPORTS edges for changed PACKAGE frames.

        For each PACKAGE:
        1. Read file content
        2. Extract import statements using language handler
        3. Resolve import paths to frame IDs (database query)
        4. Create IMPORTS edge data

        Args:
            changed_packages: List of PACKAGE frames that changed
            file_path: Path to changed file

        Returns:
            List of edge data dictionaries for insertion
        """
        edges_data = []

        # Read file content once
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return edges_data

        # Get language from first package (all should have same language)
        if not changed_packages:
            return edges_data

        language = changed_packages[0].language
        handler = language_registry.get_handler(language)

        if not handler:
            logger.warning(f"No handler for language: {language}")
            return edges_data

        # Extract imports
        try:
            imports = handler.extract_imports(file_content)
        except Exception as e:
            logger.warning(f"Failed to extract imports: {e}")
            return edges_data

        # For each import, try to resolve to a frame
        for import_stmt in imports:
            import_path = import_stmt.import_path

            # Find the most appropriate source package
            # (Use first package as source for now - could be refined)
            source_frame = changed_packages[0]

            # Resolve import to target frame ID
            target_id = self._resolve_import_by_path_in_db(import_path, language)

            if target_id:
                edge_data = {
                    'subject_frame_id': source_frame.id,
                    'object_frame_id': target_id,
                    'type': EdgeType.IMPORTS.value,
                    'confidence': 0.8,  # Default confidence for imports
                    'confidence_tier': 'HIGH',
                    'metadata': f'{{"import_path": "{import_path}"}}'
                }
                edges_data.append(edge_data)
            else:
                logger.debug(f"Could not resolve import '{import_path}'")

        return edges_data

    def recompute_contains_edges(
        self,
        added_frames: List[AstFrameBase],
        parsed_edges: List[AstEdge]
    ) -> List[Dict[str, Any]]:
        """
        Recompute CONTAINS edges for added frames from parsed edges.
        
        During parsing, FrameStack creates CONTAINS edges for the frame hierarchy.
        These edges are in parsed_edges list. We need to filter for edges that
        involve the added frames and insert them.
        
        Strategy:
        1. Get IDs of all added frames
        2. Filter parsed_edges for CONTAINS edges where:
           - subject_frame.id is in added_frames OR
           - object_frame.id is in added_frames
        3. Convert to edge data dicts for database insertion
        
        Args:
            added_frames: List of newly added frames
            parsed_edges: All edges from parse_single_file() (includes CONTAINS)
        
        Returns:
            List of edge data dictionaries ready for database insertion
        """
        edges_data = []
        
        # Build set of added frame IDs for fast lookup
        added_frame_ids = {frame.id for frame in added_frames}
        
        # Filter for CONTAINS edges involving added frames
        for edge in parsed_edges:
            if edge.type != EdgeType.CONTAINS:
                continue
            
            # Check if this CONTAINS edge involves an added frame
            # We want edges where EITHER subject OR object is in added_frames
            subject_is_added = edge.subject_frame.id in added_frame_ids
            object_is_added = edge.object_frame.id in added_frame_ids
            
            if subject_is_added or object_is_added:
                # Convert edge to database format
                edge_data = {
                    'subject_frame_id': edge.subject_frame.id,
                    'object_frame_id': edge.object_frame.id,
                    'type': EdgeType.CONTAINS.value,
                    'confidence': edge.confidence,
                    'confidence_tier': edge.confidence_tier.value if edge.confidence_tier else 'HIGH',
                    'metadata': '{}'  # CONTAINS edges typically have no metadata
                }
                edges_data.append(edge_data)
        
        logger.info(
            f"Found {len(edges_data)} CONTAINS edges for {len(added_frames)} added frames"
        )
        
        return edges_data

    def _extract_call_sites_for_frame(
        self,
        frame: AstFrameBase,
        handler
    ) -> List[Tuple[str, int]]:
        """
        Extract call sites from a CALLABLE frame.

        Uses language handler's extract_call_sites() method.
        Requires frame.content and frame._tree_sitter_node.

        Args:
            frame: CALLABLE frame to extract calls from
            handler: Language handler instance

        Returns:
            List of (callee_name, line_number) tuples
        """
        if not frame.content:
            return []

        # Check if tree-sitter node is available
        if not hasattr(frame, '_tree_sitter_node') or not frame._tree_sitter_node:
            logger.warning(f"No tree-sitter node for frame {frame.id}, cannot extract call sites")
            return []

        try:
            call_sites = handler.extract_call_sites(
                frame.content,
                frame._tree_sitter_node
            )
            return call_sites
        except Exception as e:
            logger.warning(f"Failed to extract call sites from {frame.qualified_name}: {e}")
            return []

    def _resolve_callable_by_name_in_db(
        self,
        callee_name: str,
        caller_frame: AstFrameBase
    ) -> Optional[str]:
        """
        Resolve callable name to frame ID using strategy pattern.

        Delegates to DatabaseResolutionStrategy which implements the 3-strategy
        algorithm (exact/context/partial) using KuzuDB queries.

        Args:
            callee_name: Name of the callable (e.g., 'foo', 'module.func')
            caller_frame: Frame where the call originates (for context)

        Returns:
            Frame ID if found, None otherwise
        """
        # Strategy 1: Exact match
        result = self.resolution_strategy.resolve_callable_exact(callee_name)
        if result:
            return result.frame_id

        # Strategy 2: Context-based match
        caller_package = self.resolution_strategy.get_package_qualified_name(caller_frame.id)
        if caller_package:
            result = self.resolution_strategy.resolve_callable_with_context(
                callee_name,
                caller_package
            )
            if result:
                return result.frame_id

        # Strategy 3: Partial match
        simple_name = callee_name.split('.')[-1]
        result = self.resolution_strategy.resolve_callable_partial(simple_name)
        if result:
            return result.frame_id

        return None

    def _resolve_import_by_path_in_db(
        self,
        import_path: str,
        language: str
    ) -> Optional[str]:
        """
        Resolve import path to frame ID using database query.

        Looks for PACKAGE or CLASS frames matching the import path.

        Args:
            import_path: Import path (e.g., 'nabu.core.frames')
            language: Language context

        Returns:
            Frame ID if found, None otherwise
        """
        # Try PACKAGE match first
        try:
            result = self.conn.execute("""
                MATCH (f:Frame {type: 'PACKAGE', language: $lang})
                WHERE f.qualified_name = $path OR f.qualified_name ENDS WITH $path
                RETURN f.id
                LIMIT 1
            """, {'path': import_path, 'lang': language})

            rows = list(result)
            if rows:
                return rows[0][0]
        except Exception as e:
            logger.debug(f"Package import query failed: {e}")

        # Try CLASS match (for class imports)
        try:
            result = self.conn.execute("""
                MATCH (f:Frame {type: 'CLASS', language: $lang})
                WHERE f.qualified_name = $path OR f.qualified_name ENDS WITH $path
                RETURN f.id
                LIMIT 1
            """, {'path': import_path, 'lang': language})

            rows = list(result)
            if rows:
                return rows[0][0]
        except Exception as e:
            logger.debug(f"Class import query failed: {e}")

        return None

    def _get_package_qualified_name_from_db(
        self,
        frame_id: str
    ) -> Optional[str]:
        """
        Get the qualified name of the PACKAGE containing a frame.

        Delegated to resolution strategy.

        Args:
            frame_id: ID of the frame

        Returns:
            Qualified name of containing package, or None
        """
        return self.resolution_strategy.get_package_qualified_name(frame_id)

    def _resolve_class_by_name_in_db(
        self,
        class_name: str,
        language: str
    ) -> Optional[str]:
        """
        Resolve class name to frame ID using strategy pattern.

        Delegates to DatabaseResolutionStrategy which implements the resolution
        algorithm using KuzuDB queries.

        Args:
            class_name: Class name to resolve (simple or qualified)
            language: Programming language for filtering (currently unused by strategy)

        Returns:
            Frame ID if found, None otherwise

        Note:
            TODO: Consider implementing package context resolution
            similar to _resolve_callable_by_name_in_db for better
            disambiguation when multiple classes share the same name.
        """
        # Strategy 1: Exact match
        result = self.resolution_strategy.resolve_class_exact(class_name)
        if result:
            return result.frame_id

        # Strategy 2: Partial match (shortest qualified name)
        simple_name = class_name.split('.')[-1]
        result = self.resolution_strategy.resolve_class_partial(simple_name)
        if result:
            return result.frame_id

        return None

    def _insert_external_frame(self, frame: AstFrameBase) -> None:
        """
        Insert a single external frame into database.
        
        Uses same insertion pattern as DatabaseMutator but for single frame.
        Executed within current transaction.
        
        Args:
            frame: External frame to insert
            
        Raises:
            Exception: If insertion fails (propagated, not caught)
        """
        import pandas as pd
        import json
        
        # Prepare frame data - MUST have all 20 columns to match Frame table schema
        frame_data = {
            'id': frame.id,
            'type': frame.type.value,
            'name': frame.name,
            'qualified_name': frame.qualified_name,
            'confidence': frame.confidence,
            'confidence_tier': frame.confidence_tier.value if frame.confidence_tier else 'LOW',
            'provenance': frame.provenance,
            'resolution_pass': frame.resolution_pass or 0,
            'language': frame.language,
            'file_path': frame.file_path,
            'start_line': frame.start_line or 0,
            'end_line': frame.end_line or 0,
            'start_byte': frame.start_byte or 0,
            'end_byte': frame.end_byte or 0,
            'content': frame.content or "",
            'instance_fields': [],  # External classes have no field details
            'static_fields': [],    # External classes have no field details
            'parameters': [],       # External classes have no parameter details
            'return_type': "",      # Not applicable for CLASS frames
            'metadata': frame.metadata if frame.metadata else {}
        }
        
        # Insert using pandas DataFrame (same as bulk insert)
        df = pd.DataFrame([frame_data])
        self.conn.execute("COPY Frame FROM $df", {'df': df})
        logger.debug(f"Inserted external frame: {frame.qualified_name} (id={frame.id})")

    def _create_external_class_frame(
        self,
        class_name: str,
        language: str,
        child_frame: AstFrameBase
    ) -> str:
        """
        Create external class frame during incremental update.
        
        Similar to SymbolResolver._create_external_class() but adapted for
        incremental updates where we only have database connection, not full
        CodebaseContext.
        
        Args:
            class_name: Parent class name (simple or dotted path)
            language: Programming language
            child_frame: Child class frame (for context)
            
        Returns:
            Frame ID of created external class
            
        Raises:
            Exception: If frame creation or insertion fails
            
        Note:
            Creates frame within current transaction. Frame is persisted
            to database immediately.
        """
        from nabu.core.frames import AstClassFrame
        
        # Split dotted path: 'abc.ABC' -> 'abc', 'ABC'
        parts = class_name.split('.')
        
        if len(parts) == 1:
            # Simple case: just class name
            simple_name = parts[0]
            # Infer qualified name from child's package context
            child_package = self._get_package_qualified_name_from_db(child_frame.id)
            if child_package:
                qualified_name = f"{child_package}.{simple_name}"
            else:
                # Fallback: use language root
                qualified_name = f"{language}.{simple_name}"
        else:
            # Complex case: dotted path (e.g., 'abc.ABC')
            # Use full path as qualified name
            simple_name = parts[-1]
            qualified_name = f"{language}.{class_name}"
        
        # Check if external class already exists in database
        # (Prevent duplicates across multiple inheritance edges)
        existing_result = self.conn.execute("""
            MATCH (f:Frame {type: 'CLASS', qualified_name: $qname, provenance: 'external'})
            RETURN f.id
            LIMIT 1
        """, {'qname': qualified_name})
        
        existing_rows = list(existing_result)
        if existing_rows:
            logger.debug(f"External class '{qualified_name}' already exists in database")
            return existing_rows[0][0]
        
        # Create external class frame instance
        external_class = AstClassFrame(
            id="",  # Will be computed
            type=FrameNodeType.CLASS,
            name=simple_name,
            qualified_name=qualified_name,
            confidence=0.3,  # Low confidence for external
            provenance="external",
            language=language,
            file_path="<external_or_unresolved>",
            metadata={
                'created_by': 'incremental_updater',
                'parent_of': child_frame.qualified_name,
                'resolution_strategy': 'create_on_demand'
            }
        )
        
        # Compute stable ID
        external_class.compute_id()
        
        # Insert into database within transaction
        self._insert_external_frame(external_class)
        logger.info(f"Created external class frame: {qualified_name} (id={external_class.id})")
        
        return external_class.id

    def recompute_inherits_edges(
        self,
        changed_classes: List[AstFrameBase]
    ) -> List[Dict[str, Any]]:
        """
        Recompute INHERITS edges for changed CLASS frames.
        
        For each CLASS:
        1. Extract base classes using language handler
        2. Resolve parent class names to frame IDs (database query)
        3. Create external frames for unresolved parents (within transaction)
        4. Create INHERITS edge data
        
        Args:
            changed_classes: List of CLASS frames that changed
            
        Returns:
            List of edge data dictionaries for bulk insertion
            
        Raises:
            Exception: If handler errors or frame creation fails (errors propagate)
            
        Note:
            Creates external frames for unresolved parent classes.
            All operations occur within active transaction.
        """
        import json
        
        edges_data = []
        
        # DEBUG: Log what we're processing
        logger.info(f"Processing {len(changed_classes)} CLASS frames for INHERITS edges")
        for cf in changed_classes:
            logger.info(f"  - {cf.type.value} {cf.name} (id={cf.id[:16]})")
        
        for child_frame in changed_classes:
            # DEBUG: Log frame details
            logger.info(f"  Processing child_frame: name={child_frame.name} type={child_frame.type.value} id={child_frame.id[:16]}")
            
            # Get language handler
            handler = self._get_handler_for_frame(child_frame)
            if not handler:
                raise ValueError(f"No handler for language: {child_frame.language}")
            
            # Extract base classes from content
            if not child_frame.content:
                logger.debug(f"No content for class {child_frame.qualified_name}, skipping")
                continue
            
            # Extract base classes using tree-sitter node if available
            ts_node = None
            if hasattr(child_frame, '_tree_sitter_node') and child_frame._tree_sitter_node:
                ts_node = child_frame._tree_sitter_node
            
            base_classes = handler.extract_base_classes(child_frame.content, ts_node)
            
            if not base_classes:
                logger.debug(f"No base classes found for {child_frame.qualified_name}")
                continue
            
            # Resolve each parent class
            for parent_name in base_classes:
                # Try to resolve parent in database
                parent_id = self._resolve_class_by_name_in_db(
                    parent_name,
                    child_frame.language
                )
                
                if not parent_id:
                    # Parent not found in database - create external frame
                    logger.info(
                        f"Creating external frame for unresolved parent: "
                        f"{parent_name} (child: {child_frame.qualified_name})"
                    )
                    # Let errors propagate from frame creation
                    parent_id = self._create_external_class_frame(
                        class_name=parent_name,
                        language=child_frame.language,
                        child_frame=child_frame
                    )
                
                # Get parent frame confidence (for edge confidence calculation)
                parent_conf_result = self.conn.execute("""
                    MATCH (f:Frame {id: $parent_id})
                    RETURN f.confidence
                    LIMIT 1
                """, {'parent_id': parent_id})
                parent_conf_rows = list(parent_conf_result)
                if not parent_conf_rows:
                    raise RuntimeError(
                        f"Parent frame {parent_id} not found in database after creation/resolution"
                    )
                parent_confidence = parent_conf_rows[0][0]
                
                # Calculate edge confidence
                # Formula: min(child_conf, parent_conf) * base_confidence
                edge_confidence = min(child_frame.confidence, parent_confidence) * 0.95
                
                # DEBUG: Log edge creation
                logger.info(f"Creating INHERITS edge: child={child_frame.name}(type={child_frame.type.value},id={child_frame.id[:16]}) -> parent={parent_name}(id={parent_id[:16]})")
                
                # Create edge data
                edge_data = {
                    'subject_frame_id': child_frame.id,
                    'object_frame_id': parent_id,
                    'type': EdgeType.INHERITS.value,
                    'confidence': edge_confidence,
                    'confidence_tier': 'HIGH' if edge_confidence > 0.8 else 'MEDIUM',
                    'metadata': json.dumps({'parent_name': parent_name})
                }
                edges_data.append(edge_data)
                
                logger.debug(
                    f"Created INHERITS edge: {child_frame.qualified_name} -> "
                    f"{parent_name} (confidence={edge_confidence:.2f})"
                )
        
        return edges_data

    def recompute_cpp_method_parent_edges(
        self,
        changed_callables: List[AstFrameBase]
    ) -> List[Dict[str, Any]]:
        """
        Recompute C++ CLASS → CALLABLE edges for changed methods.
        
        Follows same pattern as recompute_calls_edges but specifically
        handles C++ cross-file method-to-class relationships.
        
        Args:
            changed_callables: List of CALLABLE frames that were added/modified
        
        Returns:
            List of edge data dicts for bulk insertion
        """
        import json
        
        edges_data = []
        
        for callable_frame in changed_callables:
            # Only process C++ callables
            if callable_frame.language != 'cpp':
                continue
            
            if not callable_frame.content:
                continue
            
            # Extract class name from signature
            class_name = self._extract_cpp_class_from_signature(callable_frame.content)
            
            if not class_name:
                continue  # Not a class method
            
            # Find CLASS frame ID from database
            class_frame_id = self._find_cpp_class_id_by_name(
                class_name,
                callable_frame.language
            )
            
            if not class_frame_id:
                continue  # Class not found
            
            # Get class confidence from database
            class_confidence = self._get_frame_confidence(class_frame_id)
            
            # Calculate edge confidence
            confidence = ConfidenceCalculator.calculate_edge_confidence(
                EdgeType.CONTAINS,
                class_confidence,
                callable_frame.confidence
            )
            confidence_tier = ConfidenceCalculator.calculate_tier(confidence)
            
            # Create edge data
            edge_data = {
                'subject_frame_id': class_frame_id,
                'object_frame_id': callable_frame.id,
                'type': EdgeType.CONTAINS.value,
                'confidence': confidence,
                'confidence_tier': confidence_tier.value,
                'metadata': {
                    'cross_file_resolved': True,
                    'class_name': class_name
                }
            }
            
            edges_data.append(edge_data)
        
        return edges_data

    def _extract_cpp_class_from_signature(self, method_content: str) -> Optional[str]:
        """
        Extract class name from C++ method signature.

        Delegated to shared cpp_utils to avoid duplication with SymbolResolver.

        Returns:
            Class name or None if not a class method
        """
        return extract_cpp_class_from_signature(method_content)

    def _find_cpp_class_id_by_name(
        self,
        class_name: str,
        language: str
    ) -> Optional[str]:
        """
        Find C++ CLASS frame ID by name from database.
        
        Query: MATCH (c:Frame {type: 'CLASS', language: 'cpp', name: $class_name})
        """
        query = """
        MATCH (c:Frame {type: 'CLASS', language: $language, name: $class_name})
        RETURN c.id
        LIMIT 1
        """
        
        try:
            result = self.conn.execute(query, {
                'language': language,
                'class_name': class_name
            })
            
            if result.has_next():
                rows = result.get_next()
                if rows and len(rows) > 0:
                    return rows[0]  # c.id
            
            return None
        except Exception as e:
            logger.error(f"Failed to find CLASS '{class_name}': {e}")
            return None

    def _get_frame_confidence(self, frame_id: str) -> float:
        """Get frame confidence from database."""
        query = """
        MATCH (f:Frame {id: $frame_id})
        RETURN f.confidence
        """
        
        try:
            result = self.conn.execute(query, {'frame_id': frame_id})
            
            if result.has_next():
                rows = result.get_next()
                if rows and len(rows) > 0:
                    return rows[0]  # f.confidence
            
            return 1.0  # Default
        except Exception as e:
            logger.error(f"Failed to get confidence for frame {frame_id}: {e}")
            return 1.0

    def recompute_uses_edges(
        self,
        changed_callables: List[AstFrameBase]
    ) -> List[Dict[str, Any]]:
        """
        Recompute USES edges for changed CALLABLE frames.
        
        For each CALLABLE:
        1. Find parent CLASS frame (from database)
        2. Extract field names from CLASS.instance_fields + CLASS.static_fields
        3. Extract field usage sites using language handler
        4. Create USES edges: CALLABLE → CLASS with field metadata
        
        Args:
            changed_callables: List of CALLABLE frames that were added/modified
        
        Returns:
            List of edge data dicts for bulk insertion
        """
        import json
        
        edges_data = []
        
        for callable_frame in changed_callables:
            # Get language handler for this callable
            handler = self._get_handler_for_frame(callable_frame)
            if not handler:
                continue
            
            # Skip if no tree-sitter node
            if not hasattr(callable_frame, '_tree_sitter_node') or not callable_frame._tree_sitter_node:
                continue
            
            # Find parent CLASS frame from database
            parent_class_id = self._find_parent_class_id(callable_frame)
            if not parent_class_id:
                continue  # Not a method, no parent class
            
            # Get parent CLASS frame from database
            parent_class_frame = self._get_class_frame_from_db(parent_class_id)
            if not parent_class_frame:
                continue
            
            # Extract field names from parent class
            field_names = self._extract_field_names_from_class_frame(parent_class_frame)
            if not field_names:
                continue  # No fields in parent class
            
            # Extract field usage sites
            try:
                field_usages = handler.extract_field_usages(
                    callable_frame.content,
                    callable_frame._tree_sitter_node,
                    field_names
                )
            except Exception as e:
                logger.warning(f"Failed to extract field usages from {callable_frame.qualified_name}: {e}")
                continue
            
            # Create edge data for each field usage
            for field_name, line_number, access_type, pattern_type in field_usages:
                # Calculate base confidence
                base_confidence = ConfidenceCalculator.calculate_edge_confidence(
                    EdgeType.USES,
                    callable_frame.confidence,
                    parent_class_frame.confidence
                )
                
                # Apply pattern-based adjustment
                confidence = adjust_field_usage_confidence(base_confidence, pattern_type)
                confidence_tier = ConfidenceCalculator.calculate_tier(confidence)
                
                # Create edge data dict
                edge_data = {
                    'subject_frame_id': callable_frame.id,
                    'object_frame_id': parent_class_id,
                    'type': EdgeType.USES.value,
                    'confidence': confidence,
                    'confidence_tier': confidence_tier.value,
                    'metadata': {
                        "field_name": field_name,
                        "access_type": access_type,
                        "line": line_number,
                        "pattern_type": pattern_type
                    }
                }
                
                edges_data.append(edge_data)
        
        return edges_data
    
    def _find_parent_class_id(self, callable_frame: AstFrameBase) -> Optional[str]:
        """
        Find the parent CLASS frame ID for a CALLABLE frame.
        
        Queries database to find CLASS frame that CONTAINS this CALLABLE.
        """
        query = """
        MATCH (class:Frame {type: 'CLASS'})-[:Edge {type: 'CONTAINS'}]->(callable:Frame)
        WHERE callable.id = $callable_id
        RETURN class.id
        LIMIT 1
        """
        
        try:
            result = self.conn.execute(query, {'callable_id': callable_frame.id})
            
            if result.has_next():
                rows = result.get_next()
                if rows and len(rows) > 0:
                    return rows[0]  # class.id
            
            return None
        except Exception as e:
            logger.error(f"Failed to find parent class for {callable_frame.id}: {e}")
            return None
    
    def _get_class_frame_from_db(self, class_id: str) -> Optional[AstFrameBase]:
        """
        Retrieve CLASS frame from database by ID.
        
        Returns minimal frame with id, confidence, instance_fields, static_fields.
        """
        from nabu.core.frames import AstClassFrame
        
        query = """
        MATCH (c:Frame)
        WHERE c.id = $class_id
        RETURN c.id, c.confidence, c.instance_fields, c.static_fields
        """
        
        try:
            result = self.conn.execute(query, {'class_id': class_id})
            
            if not result.has_next():
                return None
            
            rows = result.get_next()
            if not rows or len(rows) == 0:
                return None
            
            # Create minimal CLASS frame for confidence calculation
            class_frame = AstClassFrame(
                id=rows[0],  # c.id
                confidence=rows[1],  # c.confidence
                # Parse STRUCT arrays
                instance_fields=self._parse_field_structs(rows[2]),  # c.instance_fields
                static_fields=self._parse_field_structs(rows[3]),     # c.static_fields
                # Other fields not needed for USES edge creation
                type=FrameNodeType.CLASS,
                name="",
                qualified_name="",
                file_path="",
                start_line=0,
                end_line=0
            )
            
            return class_frame
        except Exception as e:
            logger.error(f"Failed to get class frame {class_id}: {e}")
            return None
    
    def _parse_field_structs(self, struct_array) -> List:
        """
        Parse KuzuDB STRUCT array into FieldInfo list.
        
        STRUCT format: [{name: str, declared_type: str, line: int, confidence: float}, ...]
        """
        from nabu.core.field_info import FieldInfo
        
        if not struct_array:
            return []
        
        fields = []
        for struct_dict in struct_array:
            field = FieldInfo(
                name=struct_dict.get('name', ''),
                declared_type=struct_dict.get('declared_type') or None,
                line=struct_dict.get('line', 0),
                confidence=struct_dict.get('confidence', 1.0)
            )
            fields.append(field)
        
        return fields
    
    def _extract_field_names_from_class_frame(self, class_frame) -> List[str]:
        """
        Extract field names from CLASS frame.
        
        Combines instance_fields and static_fields.
        """
        field_names = []
        
        if hasattr(class_frame, 'instance_fields') and class_frame.instance_fields:
            for field in class_frame.instance_fields:
                field_names.append(field.name)
        
        if hasattr(class_frame, 'static_fields') and class_frame.static_fields:
            for field in class_frame.static_fields:
                field_names.append(field.name)
        
        return field_names

    def _get_handler_for_frame(self, frame: AstFrameBase):
        """
        Get the language handler for a frame.

        Args:
            frame: Frame to get handler for

        Returns:
            Language handler instance or None
        """
        if not frame.language:
            return None

        return language_registry.get_handler(frame.language)

    def _insert_edges_bulk(self, edges_data: List[Dict[str, Any]]) -> None:
        """
        Insert edges using shared EdgeInserter with repairer-specific options.

        Args:
            edges_data: List of edge dictionaries
        """
        if not edges_data:
            return

        EdgeInserter.insert_edges(
            self.conn,
            edges_data,
            serialize_metadata=True,  # Repairer needs JSON serialization
            verbose_logging=True       # Repairer wants detailed logs
        )
