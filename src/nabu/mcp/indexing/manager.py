"""Auto-indexing manager for nabu MCP."""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

from .state import IndexingState, IndexingStatus

if TYPE_CHECKING:
    from nabu.mcp.factory import NabuMCPFactory

logger = logging.getLogger(__name__)


class AutoIndexingManager:
    """
    Manages automatic indexing of unindexed codebases.

    Responsibilities:
    - Detect unindexed codebases (DB file doesn't exist)
    - Queue them for background indexing
    - Process indexing jobs sequentially (CPU-bound, one at a time)
    - Track indexing state in-memory
    """

    def __init__(self, factory: "NabuMCPFactory"):
        """
        Initialize auto-indexing manager.

        Args:
            factory: The NabuMCPFactory instance
        """
        self.factory = factory
        self.indexing_queue: asyncio.Queue = asyncio.Queue()
        self.status: Dict[str, IndexingStatus] = {}
        self.worker_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """
        Start auto-indexing worker and detect unindexed codebases.

        This is called during server startup. It:
        1. Starts the background worker task
        2. Detects which codebases need indexing
        3. Queues them for processing
        """
        # Start background worker
        self.worker_task = asyncio.create_task(self._indexing_worker())
        self.logger.info("Auto-indexing worker started")

        # Detect and queue unindexed codebases
        for name, cb_config in self.factory.config.codebases.items():
            if self._is_unindexed(name):
                self.logger.info(f"Detected unindexed codebase: '{name}'")
                self.status[name] = IndexingStatus(
                    codebase=name,
                    state=IndexingState.QUEUED
                )
                await self.indexing_queue.put(name)
            else:
                # Already indexed
                self.status[name] = IndexingStatus(
                    codebase=name,
                    state=IndexingState.INDEXED
                )

    async def stop(self):
        """Stop auto-indexing worker gracefully."""
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Auto-indexing worker stopped")

    def _is_unindexed(self, codebase: str) -> bool:
        """
        Check if codebase needs indexing.

        Detection logic: DB file doesn't exist

        Args:
            codebase: Codebase name to check

        Returns:
            True if codebase needs indexing, False if already indexed
        """
        cb_config = self.factory.config.codebases[codebase]
        db_path = cb_config.db_path

        # Simple check: does DB file exist?
        return not db_path.exists()

    def get_status(self, codebase: str) -> IndexingStatus:
        """
        Get current indexing status for a codebase.

        Args:
            codebase: Codebase name

        Returns:
            IndexingStatus for the codebase (defaults to INDEXED if unknown)
        """
        return self.status.get(
            codebase,
            IndexingStatus(codebase=codebase, state=IndexingState.INDEXED)
        )

    async def queue_for_indexing(self, codebase: str):
        """
        Manually queue a codebase for indexing.

        Args:
            codebase: Codebase name to index
        """
        if codebase not in self.factory.config.codebases:
            raise ValueError(f"Unknown codebase: {codebase}")

        self.status[codebase] = IndexingStatus(
            codebase=codebase,
            state=IndexingState.QUEUED
        )
        await self.indexing_queue.put(codebase)
        self.logger.info(f"Queued '{codebase}' for indexing")

    async def _indexing_worker(self):
        """
        Background worker that processes indexing jobs sequentially.

        Runs as an async task throughout server lifetime.
        Processes one codebase at a time to avoid CPU/GPU saturation.
        """
        self.logger.info("Auto-indexing worker loop started")

        try:
            while True:
                codebase = await self.indexing_queue.get()

                # Update status to INDEXING
                self.status[codebase] = IndexingStatus(
                    codebase=codebase,
                    state=IndexingState.INDEXING,
                    started_at=time.time()
                )

                self.logger.info(f"Starting indexing for '{codebase}'...")

                try:
                    # Run CPU-bound parsing in thread to avoid blocking event loop
                    await asyncio.to_thread(self._do_index_codebase, codebase)

                    # Success
                    self.status[codebase] = IndexingStatus(
                        codebase=codebase,
                        state=IndexingState.INDEXED,
                        started_at=self.status[codebase].started_at,
                        completed_at=time.time()
                    )

                    elapsed = time.time() - self.status[codebase].started_at
                    self.logger.info(f"✓ Auto-indexing completed for '{codebase}' ({elapsed:.1f}s)")

                except Exception as e:
                    self.logger.error(f"✗ Auto-indexing failed for '{codebase}': {e}", exc_info=True)
                    self.status[codebase] = IndexingStatus(
                        codebase=codebase,
                        state=IndexingState.ERROR,
                        error_message=str(e),
                        started_at=self.status[codebase].started_at,
                        completed_at=time.time()
                    )
                finally:
                    self.indexing_queue.task_done()

        except asyncio.CancelledError:
            self.logger.info("Auto-indexing worker cancelled")
            raise

    def _do_index_codebase(self, codebase: str):
        """
        Execute full codebase indexing (sync, CPU-bound).

        This runs in a thread pool to avoid blocking the async event loop.

        Args:
            codebase: Codebase name to index
        """
        import nabu.main
        from nabu.db import KuzuConnectionManager

        cb_config = self.factory.config.codebases[codebase]
        repo_path = str(cb_config.repo_path)
        db_path = str(cb_config.db_path)

        self.logger.info(f"Indexing codebase '{codebase}': {repo_path} -> {db_path}")

        # Close existing manager if present
        if codebase in self.factory.db_managers:
            self.factory.db_managers[codebase].close()
            del self.factory.db_managers[codebase]

        # Delete existing DB files if they exist
        if cb_config.db_path.exists():
            self.logger.info(f"Removing existing database files for '{codebase}'")
            cb_config.db_path.unlink()
            cb_config.db_path.with_suffix(".wal").unlink(missing_ok=True)
            cb_config.db_path.with_suffix(".wal.shadow").unlink(missing_ok=True)

        # Parse codebase and export to database
        nabu.main.parse_codebase(
            codebase_path=repo_path,
            output_db=db_path,
            extra_ignore_patterns=self.factory.config.extra_ignore_patterns
        )

        # Re-initialize db_manager
        self.factory.db_managers[codebase] = KuzuConnectionManager.get_instance(db_path)
        self.logger.info(f"Database manager re-initialized for '{codebase}'")

        # Initialize incremental updater
        from nabu.incremental import IncrementalUpdater
        self.factory.incremental_updaters[codebase] = IncrementalUpdater(db_path)
        self.logger.info(f"Incremental updater initialized for '{codebase}'")

        # Update active codebase pointers if needed
        if codebase == self.factory.config.active_codebase:
            self.factory.db_manager = self.factory.db_managers[codebase]
            self.factory.incremental_updater = self.factory.incremental_updaters[codebase]
            self.logger.info(f"Active codebase pointers updated to '{codebase}'")
