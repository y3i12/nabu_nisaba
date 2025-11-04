"""Shared edge insertion utilities with bulk + fallback strategy."""

from dataclasses import dataclass
from typing import List, Dict, Any
import logging

try:
    import kuzu
except ImportError:
    raise ImportError("kuzu package not available. Install with: pip install kuzu")

logger = logging.getLogger(__name__)


@dataclass
class EdgeInsertionResult:
    """Result of edge insertion operation."""
    inserted_count: int
    failed_count: int = 0


class EdgeInserter:
    """Unified edge insertion logic with configurable behavior."""

    @staticmethod
    def insert_edges(
        conn: kuzu.Connection,
        edges_data: List[Dict[str, Any]],
        *,
        serialize_metadata: bool = False,
        verbose_logging: bool = False
    ) -> EdgeInsertionResult:
        """
        Insert edges with automatic bulk→individual fallback.

        Args:
            conn: KuzuDB connection
            edges_data: Edge dictionaries
            serialize_metadata: Convert dict metadata to JSON strings (for COPY FROM)
            verbose_logging: Log detailed edge information

        Returns:
            EdgeInsertionResult with counts
        """
        import pandas as pd
        import json

        if not edges_data:
            logger.debug("No edges to insert")
            return EdgeInsertionResult(inserted_count=0)

        # Optional: JSON serialization
        if serialize_metadata:
            for edge_data in edges_data:
                if 'metadata' in edge_data and isinstance(edge_data['metadata'], dict):
                    edge_data['metadata'] = json.dumps(edge_data['metadata'])
                elif 'metadata' not in edge_data or edge_data['metadata'] is None:
                    edge_data['metadata'] = '{}'

        # Optional: Verbose logging
        if verbose_logging:
            for ed in edges_data:
                if ed.get('type') == 'INHERITS':
                    logger.info(
                        f"Inserting INHERITS edge: "
                        f"subject={ed['subject_frame_id'][:16]} -> "
                        f"object={ed['object_frame_id'][:16]}"
                    )

        # Attempt bulk insert
        try:
            df = pd.DataFrame(edges_data)

            if verbose_logging:
                logger.info(f"Attempting to insert {len(edges_data)} edges via COPY Edge")
                logger.info(f"DataFrame columns: {list(df.columns)}")
                logger.info(f"DataFrame shape: {df.shape}")

            conn.execute("COPY Edge FROM $df", {'df': df})
            logger.debug(f"Bulk inserted {len(edges_data)} edges")
            return EdgeInsertionResult(inserted_count=len(edges_data))

        except Exception as e:
            logger.error(f"Bulk edge insertion failed: {e}")
            return EdgeInserter._insert_individually(conn, edges_data)

    @staticmethod
    def _insert_individually(
        conn: kuzu.Connection,
        edges_data: List[Dict[str, Any]]
    ) -> EdgeInsertionResult:
        """Fallback: insert edges one by one."""
        import pandas as pd

        successful = 0
        failed = 0

        for edge_data in edges_data:
            try:
                df = pd.DataFrame([edge_data])
                conn.execute("COPY Edge FROM $df", {'df': df})
                successful += 1
            except Exception as e:
                logger.error(
                    f"Failed to insert edge {edge_data.get('type', 'UNKNOWN')}: {e}"
                )
                failed += 1

        logger.info(f"Individual edge insertion: {successful} successful, {failed} failed")
        return EdgeInsertionResult(inserted_count=successful, failed_count=failed)
