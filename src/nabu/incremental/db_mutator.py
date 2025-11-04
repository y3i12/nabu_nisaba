"""
Database mutator for incremental updates.

Executes delete/insert/update operations on KuzuDB based on stable_id diffs.
Maintains referential integrity and handles transactions.
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Any
import logging

try:
    import kuzu
except ImportError:
    raise ImportError("kuzu package not available. Install with: pip install kuzu")

from nabu.core.frames import AstFrameBase, AstClassFrame, AstCallableFrame
from nabu.incremental.edge_inserter import EdgeInserter
import json

logger = logging.getLogger(__name__)


@dataclass
class DeleteResult:
    """Result of frame deletion operation."""
    deleted_frame_count: int
    deleted_edge_count: int  # Edges deleted via CASCADE


@dataclass
class InsertResult:
    """Result of frame insertion operation."""
    inserted_count: int


@dataclass
class InsertEdgeResult:
    """Result of edge insertion operation."""
    inserted_count: int


class DatabaseMutator:
    """
    Execute database mutations for incremental updates.
    
    Responsibilities:
    - Delete frames by stable_id (with CASCADE edge deletion)
    - Insert new frames (with auto-assigned internal_ids)
    - Update frame content (preserving internal_id and relationships)
    
    All operations maintain database consistency and referential integrity.
    """
    
    def __init__(self):
        """
        Initialize DatabaseMutator.
        
        Connection is now passed to individual methods instead of stored.
        This allows proper use of KuzuConnectionManager context managers.
        """
        pass
    
    def delete_frames_by_id(
        self,
        conn: kuzu.Connection,
        frame_ids: Set[str]
    ) -> DeleteResult:
        """
        Delete frames by id.
        
        KuzuDB automatically cascades edge deletions when nodes are deleted.
        
        Args:
            conn: Active KuzuDB connection
            frame_ids: Set of frame ids to delete
            
        Returns:
            DeleteResult with counts of deleted frames and edges
            
        Note:
            Uses parameterized query to handle large stable_id sets efficiently.
        """
        if not frame_ids:
            logger.debug("No frames to delete")
            return DeleteResult(deleted_frame_count=0, deleted_edge_count=0)
        
        frame_id_list = list(frame_ids)
        
        # Count edges before deletion (for reporting)
        edge_count_query = """
            MATCH (f:Frame)-[e:Edge]-()
            WHERE f.id IN $frame_ids
            RETURN count(e) as edge_count
        """
        result = conn.execute(edge_count_query, {'frame_ids': frame_id_list})
        # KuzuDB returns rows as lists, not dicts
        rows = list(result)
        edge_count = rows[0][0] if rows else 0
        
        # Delete frames (DETACH DELETE removes connected edges automatically)
        delete_query = """
            MATCH (f:Frame)
            WHERE f.id IN $frame_ids
            DETACH DELETE f
        """
        
        conn.execute(delete_query, {'frame_ids': frame_id_list})
        
        logger.info(f"Deleted {len(frame_ids)} frames and {edge_count} associated edges")
        
        return DeleteResult(
            deleted_frame_count=len(frame_ids),
            deleted_edge_count=edge_count
        )
    
    def insert_frames(
        self,
        conn: kuzu.Connection,
        frames: List[AstFrameBase]
    ) -> InsertResult:
        """
        Insert new frames into database.
        
        Args:
            conn: Active KuzuDB connection
            frames: List of frames to insert
            
        Returns:
            InsertResult with inserted count
            
        Note:
            Frame.id is already the stable content-hash identifier.
            No mapping is needed since id IS the identifier.
        """
        if not frames:
            logger.debug("No frames to insert")
            return InsertResult(inserted_count=0)
        inserted_count = 0
        
        for frame in frames:
            # Extract frame data (same logic as KuzuDbExporter._extract_single_frame_data)
            frame_data = self._extract_frame_data(frame)
            
            # Insert frame - use CREATE instead of COPY for individual insert
            insert_query = """
                CREATE (f:Frame {
                    id: $id,
                    type: $type,
                    name: $name,
                    qualified_name: $qualified_name,
                    confidence: $confidence,
                    confidence_tier: $confidence_tier,
                    provenance: $provenance,
                    resolution_pass: $resolution_pass,
                    language: $language,
                    file_path: $file_path,
                    start_line: $start_line,
                    end_line: $end_line,
                    start_byte: $start_byte,
                    end_byte: $end_byte,
                    content: $content,
                    instance_fields: $instance_fields,
                    static_fields: $static_fields,
                    parameters: $parameters,
                    return_type: $return_type,
                    metadata: $metadata
                })
            """
            
            try:
                # DEBUG: Log frame insertion
                if frame.type.value == 'CLASS':
                    logger.info(f"Inserting CLASS frame: name={frame.name} id={frame.id[:16]}")
                
                conn.execute(insert_query, frame_data)
                
                # Note: frame.id is already the stable content-hash identifier
                # No need to maintain a separate mapping since id IS the identifier
                inserted_count += 1

                
            except Exception as e:
                logger.error(f"Failed to insert frame {frame.id}: {e}")
                # Continue with other frames
        
        logger.info(f"Inserted {inserted_count} frames")
        
        return InsertResult(inserted_count=inserted_count)
    
    def _extract_frame_data(self, frame: AstFrameBase) -> Dict[str, Any]:
        """
        Extract frame data for database insertion.
        
        Same logic as KuzuDbExporter._extract_single_frame_data but returns
        data dict suitable for parameterized CREATE query.
        """
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
        
        # Ensure stable_id is computed
        # ID is already computed in FrameFactory
        
        return {
            'id': frame.id,
            'type': frame.type.value,
            'name': frame.name or "",
            'qualified_name': frame.qualified_name or "",
            'confidence': frame.confidence,
            'confidence_tier': frame.confidence_tier.value,
            'provenance': frame.provenance,
            'resolution_pass': frame.resolution_pass,
            'language': frame.language or "",
            'file_path': frame.file_path or "",
            'start_line': frame.start_line,
            'end_line': frame.end_line,
            'start_byte': frame.start_byte,
            'end_byte': frame.end_byte,
            'content': frame.content or "",
            'instance_fields': instance_fields,
            'static_fields': static_fields,
            'parameters': parameters,
            'return_type': return_type,
            'metadata': frame.metadata if frame.metadata else {},
            # stable_id removed - id is now the primary key
        }
    
    def update_frame_content(
        self,
        conn: kuzu.Connection,
        frame_id: str,
        new_frame: AstFrameBase
    ) -> bool:
        """
        Update frame content while preserving id and relationships.
        
        Used for rare edge case where content changes need to be updated
        without changing the frame id.
        
        Args:
            conn: Active KuzuDB connection
            frame_id: ID of frame to update
            new_frame: New frame data
            
        Returns:
            True if updated, False if frame not found
        """
        update_query = """
            MATCH (f:Frame {id: $frame_id})
            SET f.content = $content,
                f.start_line = $start_line,
                f.end_line = $end_line,
                f.start_byte = $start_byte,
                f.end_byte = $end_byte,
                f.metadata = $metadata
            RETURN f.id
        """
        
        params = {
            'frame_id': frame_id,
            'content': new_frame.content or "",
            'start_line': new_frame.start_line,
            'end_line': new_frame.end_line,
            'start_byte': new_frame.start_byte,
            'end_byte': new_frame.end_byte,
            'metadata': new_frame.metadata if new_frame.metadata else {}
        }
        
        result = conn.execute(update_query, params)
        updated = len(list(result)) > 0
        
        if updated:
            logger.debug(f"Updated frame content for id {frame_id}")
        else:
            logger.warning(f"Frame with id {frame_id} not found for update")

        return updated

    def insert_edges(self, conn: kuzu.Connection, edges_data: List[Dict[str, Any]]) -> 'InsertEdgeResult':
        """
        Insert edges into database using shared EdgeInserter.

        Args:
            conn: Active KuzuDB connection
            edges_data: List of edge dictionaries

        Returns:
            InsertEdgeResult with inserted count
        """
        result = EdgeInserter.insert_edges(conn, edges_data)
        return InsertEdgeResult(inserted_count=result.inserted_count)
