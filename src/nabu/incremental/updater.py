"""
Incremental file updater - orchestrates the update workflow.

Main entry point for incremental updates. Coordinates parsing, diff computation,
database mutations, and validation.
"""

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import logging
import time

try:
    import kuzu
except ImportError:
    raise ImportError("kuzu package not available. Install with: pip install kuzu")

from nabu.incremental.diff_calculator import StableDiffCalculator, FrameDiff
from nabu.incremental.db_mutator import DatabaseMutator
from nabu.incremental.relationship_repairer import RelationshipRepairer
from nabu.parsing.multi_pass_parser import MultiPassParser

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    """
    Result of incremental update operation.
    
    Provides metrics for debugging, validation, and user feedback.
    """
    file_path: str
    success: bool
    
    # Frame changes
    frames_deleted: int
    frames_added: int
    frames_stable: int
    total_old_frames: int
    total_new_frames: int
    stability_percentage: float
    
    # Edge changes
    edges_deleted: int = 0
    edges_added: int = 0
    edges_preserved: int = 0
    
    # Edge repair details (Phase 3.1)
    calls_edges_added: int = 0
    imports_edges_added: int = 0
    contains_edges_added: int = 0
    inherits_edges_added: int = 0
    uses_edges_added: int = 0
    
    # Performance metrics
    parse_time_ms: float = 0.0
    diff_time_ms: float = 0.0
    database_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    # Validation
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        """Initialize mutable default fields."""
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    @property
    def churn_percentage(self) -> float:
        """Percentage of frames that changed."""
        if self.total_new_frames == 0:
            return 0.0
        return ((self.frames_deleted + self.frames_added) / self.total_new_frames) * 100.0
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Incremental Update: {self.file_path}",
            f"  Status: {'SUCCESS' if self.success else 'FAILED'}",
            f"  Frames: {self.frames_deleted} deleted, {self.frames_added} added, {self.frames_stable} stable",
            f"  Stability: {self.stability_percentage:.1f}% ({self.frames_stable}/{self.total_new_frames})",
            f"  Time: {self.total_time_ms:.1f}ms total (parse: {self.parse_time_ms:.1f}ms, diff: {self.diff_time_ms:.1f}ms, db: {self.database_time_ms:.1f}ms)",
        ]
        
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
            for error in self.errors[:3]:  # Show first 3
                lines.append(f"    - {error}")
        
        if self.warnings:
            lines.append(f"  Warnings: {len(self.warnings)}")
            for warning in self.warnings[:3]:
                lines.append(f"    - {warning}")
        
        return "\n".join(lines)


class IncrementalUpdater:
    """
    Orchestrator for incremental file updates.
    
    Workflow:
        1. Parse changed file
        2. Query existing frames from database
        3. Compute diff (deleted, added, stable)
        4. Execute database mutations (delete, insert)
        5. (Phase 2+: Repair relationships)
        6. Return metrics
    
    Usage:
        updater = IncrementalUpdater(db_path="nabu.kuzu")
        result = updater.update_file("src/foo.py")
        print(result.summary())
    """
    
    def __init__(self, db_path: str):
        """
        Initialize updater with database manager.
        
        Args:
            db_path: Path to KuzuDB database file
        """
        from nabu.db import KuzuConnectionManager
        
        self.db_path = db_path
        
        # Get singleton Database manager
        self.db_manager = KuzuConnectionManager.get_instance(db_path)
        
        # Initialize components (no longer need persistent connection)
        self.diff_calculator = StableDiffCalculator()
        self.db_mutator = DatabaseMutator()
        self.relationship_repairer = RelationshipRepairer()
        self.parser = MultiPassParser()

        logger.info(f"IncrementalUpdater initialized with database: {db_path}")
    
    def update_file(self, file_path: str) -> UpdateResult:
        """
        Update database for a single changed file.
        
        Args:
            file_path: Path to changed file (absolute or relative)
            
        Returns:
            UpdateResult with metrics and status
            
        Algorithm:
            1. Validate file exists
            2. Parse file → new frames
            3. Query database → old frames for this file
            4. Compute diff → deleted, added, stable sets
            5. BEGIN TRANSACTION
            6. Delete removed frames
            7. Insert new frames
            8. Repair edges
            9. COMMIT TRANSACTION
            10. Return metrics
        """
        start_time = time.time()
        
        # Validate file exists
        file_path = str(Path(file_path).resolve())  # Normalize to absolute path
        if not Path(file_path).exists():
            return UpdateResult(
                file_path=file_path,
                success=False,
                frames_deleted=0,
                frames_added=0,
                frames_stable=0,
                total_old_frames=0,
                total_new_frames=0,
                stability_percentage=0.0,
                errors=[f"File not found: {file_path}"]
            )
        
        try:
            # Step 1: Parse changed file
            parse_start = time.time()
            codebase_frame, edges = self.parser.parse_single_file(file_path)
            new_frames = self.diff_calculator.collect_all_frames(codebase_frame)
            parse_time_ms = (time.time() - parse_start) * 1000
            
            logger.info(f"Parsed {file_path}: {len(new_frames)} frames")
            
            # Step 2-4: Database operations within connection context
            # Use KuzuConnectionManager to get connection with FTS extension loaded
            with self.db_manager.connection(load_extensions=True) as conn:
                # Step 2: Query existing frames from database
                old_frames_data = self._query_frames_by_file(conn, file_path)
                logger.info(f"Found {len(old_frames_data)} existing frames in database")
                
                # Step 3: Compute diff
                diff_start = time.time()
                diff = self.diff_calculator.compute_diff(old_frames_data, new_frames)
                diff_time_ms = (time.time() - diff_start) * 1000
                
                logger.info(
                    f"Diff computed: {diff.deleted_count} deleted, "
                    f"{diff.added_count} added, {diff.stable_count} stable "
                    f"({diff.stability_percentage:.1f}% stability)"
                )
                
                # Step 4: Execute database mutations in transaction
                db_start = time.time()
                transaction_started = False
                
                try:
                    # BEGIN TRANSACTION
                    conn.execute("BEGIN TRANSACTION;")
                    transaction_started = True
                    
                    # Delete removed frames
                    delete_result = self.db_mutator.delete_frames_by_id(
                        conn,
                        diff.deleted_ids
                    )
                    
                    # Insert new frames
                    insert_result = self.db_mutator.insert_frames(conn, diff.added_frames)

                    # Repair edges for changed frames (pass edges from parsing)
                    repair_result = self.relationship_repairer.repair_edges(conn, diff, file_path, edges)

                    # COMMIT TRANSACTION
                    conn.execute("COMMIT;")
                    transaction_started = False

                    db_time_ms = (time.time() - db_start) * 1000
                    total_time_ms = (time.time() - start_time) * 1000

                    logger.info(f"Database updated successfully in {db_time_ms:.1f}ms")

                    # Build success result
                    return UpdateResult(
                        file_path=file_path,
                        success=True,
                        frames_deleted=diff.deleted_count,
                        frames_added=diff.added_count,
                        frames_stable=diff.stable_count,
                        total_old_frames=diff.total_old,
                        total_new_frames=diff.total_new,
                        stability_percentage=diff.stability_percentage,
                        edges_deleted=delete_result.deleted_edge_count,
                        edges_added=repair_result.edges_added,
                        edges_preserved=0,
                        calls_edges_added=repair_result.calls_edges_added,
                        imports_edges_added=repair_result.imports_edges_added,
                        contains_edges_added=repair_result.contains_edges_added,
                        inherits_edges_added=repair_result.inherits_edges_added,
                        uses_edges_added=repair_result.uses_edges_added,
                        parse_time_ms=parse_time_ms,
                        diff_time_ms=diff_time_ms,
                        database_time_ms=db_time_ms,
                        total_time_ms=total_time_ms,
                        warnings=self._generate_warnings(diff)
                    )
                    
                except Exception as e:
                    # ROLLBACK only if transaction was started
                    if transaction_started:
                        try:
                            conn.execute("ROLLBACK;")
                            logger.error(f"Transaction rolled back due to error: {e}")
                        except Exception as rollback_error:
                            logger.error(f"Failed to rollback transaction. Original error: {e}, Rollback error: {rollback_error}")
                    else:
                        logger.error(f"Database operation failed before transaction started: {e}")
                    raise
        
        except Exception as e:
            total_time_ms = (time.time() - start_time) * 1000
            
            return UpdateResult(
                file_path=file_path,
                success=False,
                frames_deleted=0,
                frames_added=0,
                frames_stable=0,
                total_old_frames=0,
                total_new_frames=0,
                stability_percentage=0.0,
                total_time_ms=total_time_ms,
                errors=[f"Update failed: {str(e)}"]
            )
    
    def _query_frames_by_file(self, conn, file_path: str) -> List[dict]:
        """
        Query all frames for a specific file from database.
        
        Args:
            conn: Active KuzuDB connection
            file_path: Absolute path to file
            
        Returns:
            List of frame data dictionaries with id
        """
        query = """
            MATCH (f:Frame)
            WHERE f.file_path = $file_path
            RETURN f.id
        """
        
        result = conn.execute(query, {'file_path': file_path})
        # KuzuDB returns rows as lists, not dicts
        # Build dict manually from list values
        frames_data = []
        for row in result:
            frame_dict = {
                'id': row[0],  # Frame id (content-hash identifier)
            }
            frames_data.append(frame_dict)
        
        return frames_data
    
    def _generate_warnings(self, diff: FrameDiff) -> List[str]:
        """
        Generate warnings based on diff patterns.
        
        Args:
            diff: Computed frame diff
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Warn on unexpected 100% churn (all frames changed)
        if diff.stability_percentage < 5.0 and diff.total_new > 10:
            warnings.append(
                f"Very low stability ({diff.stability_percentage:.1f}%) - "
                "expected 70-80% for typical edits. File may have been completely rewritten."
            )
        
        # Warn on unexpected 100% stability (nothing changed)
        if diff.stability_percentage > 99.0 and diff.total_new > 0:
            warnings.append(
                "No changes detected (100% stability) - file may be identical to database version"
            )
        
        # Warn on file deletion (all frames removed)
        if diff.total_new == 0 and diff.total_old > 0:
            warnings.append(
                f"All {diff.total_old} frames deleted - file may be empty or unparseable"
            )
        
        return warnings
    
    def close(self):
        """
        Close database connection and release resources.
        
        Note: Since we no longer maintain a persistent connection,
        this method is now a no-op. Kept for backwards compatibility.
        """
        logger.debug("IncrementalUpdater.close() called (no-op, no persistent connection)")

    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.close()
        return False  # Don't suppress exceptions
