"""Nabu Agent: Stateful orchestrator for nabu resources."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Optional, AsyncIterator, TYPE_CHECKING

from nisaba.agent import Agent

if TYPE_CHECKING:
    from nabu.mcp.factory_impl import NabuMCPFactorySingleProcess
    from nabu.db import KuzuConnectionManager
    from nabu.incremental import IncrementalUpdater
    from nabu.mcp.indexing import AutoIndexingManager
    from nabu.file_watcher import FileWatcher

from nabu.mcp.config.nabu_config import NabuConfig
from nisaba.guidance import WorkflowGuidance
from nisaba.augments import get_augment_manager

logger = logging.getLogger(__name__)


class NabuAgent(Agent):
    """
    Stateful orchestrator for nabu MCP resources.

    Manages:
    - Database managers (multi-codebase)
    - Incremental updaters
    - Auto-indexing
    - File watchers
    - Workflow guidance (augments-based)

    The agent handles resource lifecycle (initialization and cleanup)
    and state mutations (codebase switching).
    """

    def __init__(self, config: NabuConfig, factory: "NabuMCPFactorySingleProcess"):
        """
        Initialize nabu agent with configuration.

        Args:
            config: NabuConfig instance
            factory: Reference to factory (for callbacks like _handle_file_change)
        """
        super().__init__()  # Initialize base agent (sets guidance = None)

        self.config = config
        self.factory = factory  # Needed for _handle_file_change callback

        # Multi-codebase state
        self.db_managers: Dict[str, "KuzuConnectionManager"] = {}
        self.incremental_updaters: Dict[str, "IncrementalUpdater"] = {}

        # Active codebase (backward compatibility)
        self.db_manager: Optional["KuzuConnectionManager"] = None
        self.incremental_updater: Optional["IncrementalUpdater"] = None

        # Lifecycle components
        self.auto_indexer: Optional["AutoIndexingManager"] = None
        self._file_watchers: Dict[str, "FileWatcher"] = {}

        # Augments management
        # Use active codebase's repo path for augments directory
        active_cb_config = config.codebases.get(config.active_codebase)
        if active_cb_config:
            augments_dir = active_cb_config.repo_path / '.nisaba' / 'augments'
            composed_file = active_cb_config.repo_path / '.nisaba' / 'tui' / 'augment_view.md'
        else:
            # Fallback to first codebase if no active codebase
            first_cb = next(iter(config.codebases.values()))
            augments_dir = first_cb.repo_path / '.nisaba' / 'augments'
            composed_file = first_cb.repo_path / '.nisaba' / 'tui' / 'augment_view.md'

        self.augment_manager = get_augment_manager(augments_dir, composed_file)
        logger.info(f"📚 Augments manager initialized: {len(self.augment_manager.available_augments)} augments available")

        # Workflow guidance (augments-based only)
        self.guidance = WorkflowGuidance(augment_manager=self.augment_manager)
        logger.info("✨ Augments-based guidance enabled")

    def activate_codebase(self, name: str) -> None:
        """
        Switch active codebase (state mutation).

        Args:
            name: Codebase name to activate

        Raises:
            ValueError: If codebase not found
        """
        if name not in self.db_managers:
            available = list(self.db_managers.keys())
            raise ValueError(f"Codebase '{name}' not found. Available: {available}")

        self.config.active_codebase = name
        self.db_manager = self.db_managers[name]

        if name in self.incremental_updaters:
            self.incremental_updater = self.incremental_updaters[name]

        logger.info(f"✓ Active codebase switched to '{name}'")

    async def initialize(self) -> None:
        """
        Initialize agent resources (lifecycle startup).

        Handles:
        - Auto-indexing manager startup
        - Database manager initialization
        - Incremental updater initialization
        - File watcher setup
        """
        logger.info("=" * 60)
        logger.info("Nabu Agent - Initializing")
        logger.info("=" * 60)

        if self.config.dev_mode:
            logger.debug("Development mode active - verbose logging enabled")

        # Initialize auto-indexing manager FIRST (before db_managers)
        # This prevents KuzuDB from creating empty databases for unindexed codebases
        try:
            from nabu.mcp.indexing import AutoIndexingManager

            self.auto_indexer = AutoIndexingManager(self.factory)
            await self.auto_indexer.start()
            logger.info("✓ Auto-indexing manager started")
        except Exception as e:
            logger.error(f"Failed to start auto-indexing: {e}")
            raise

        # Initialize database managers ONLY for codebases with existing databases
        # Unindexed codebases will have their db_manager created after indexing completes
        try:
            from nabu.db import KuzuConnectionManager

            for name, cb_config in self.config.codebases.items():
                # Check if database file exists before initializing manager
                # (KuzuDB creates empty DB if file doesn't exist, which breaks auto-indexing detection)
                if not cb_config.db_path.exists():
                    logger.info(f"⏸ Skipping db_manager init for '{name}' (will be indexed)")
                    continue

                self.db_managers[name] = KuzuConnectionManager.get_instance(str(cb_config.db_path))
                logger.info(f"✓ Database manager initialized for '{name}': {cb_config.db_path}")

            # BACKWARD COMPATIBILITY: Set self.db_manager to active codebase
            if self.config.active_codebase and self.config.active_codebase in self.db_managers:
                self.db_manager = self.db_managers[self.config.active_codebase]
                logger.info(f"✓ Active codebase: {self.config.active_codebase}")

        except Exception as e:
            logger.error(f"Failed to initialize database managers: {e}")
            raise

        # Initialize incremental updaters ONLY for codebases with existing databases
        try:
            from nabu.incremental import IncrementalUpdater

            for name, cb_config in self.config.codebases.items():
                # Only initialize updater if database exists
                if not cb_config.db_path.exists():
                    logger.info(f"⏸ Skipping updater init for '{name}' (will be indexed)")
                    continue

                self.incremental_updaters[name] = IncrementalUpdater(str(cb_config.db_path))
                logger.info(f"✓ Incremental updater initialized for '{name}'")

            # BACKWARD COMPATIBILITY: Set self.incremental_updater to active
            if self.config.active_codebase and self.config.active_codebase in self.incremental_updaters:
                self.incremental_updater = self.incremental_updaters[self.config.active_codebase]

        except Exception as e:
            logger.warning(f"Could not initialize incremental updaters: {e}")

        # Initialize file watchers for codebases with watch_enabled
        self._file_watchers = {}
        for name, cb_config in self.config.codebases.items():
            # Only start watcher if codebase is indexed
            if self.auto_indexer:
                from nabu.mcp.indexing import IndexingState
                indexing_status = self.auto_indexer.get_status(name)
                if indexing_status.state != IndexingState.INDEXED:
                    logger.info(f"⏸ Skipping file watcher for '{name}' (state: {indexing_status.state.value})")
                    continue

            if cb_config.watch_enabled and name in self.incremental_updaters:
                try:
                    from nabu.file_watcher import FileWatcher, FileFilter
                    from nabu.language_handlers import language_registry

                    # Build ignore patterns: defaults + .gitignore + extra from config
                    ignore_patterns = FileFilter.default_ignores()

                    # Load repository .gitignore
                    gitignore_path = cb_config.repo_path / ".gitignore"
                    if gitignore_path.exists():
                        try:
                            with open(gitignore_path, 'r', encoding='utf-8') as f:
                                for line in f:
                                    line = line.strip()
                                    if line and not line.startswith('#'):
                                        ignore_patterns.append(line)
                            logger.debug(f"Loaded .gitignore patterns for '{name}'")
                        except Exception as e:
                            logger.warning(f"Failed to load .gitignore for '{name}': {e}")

                    # Add extra patterns from config
                    if self.config.extra_ignore_patterns:
                        ignore_patterns.extend(self.config.extra_ignore_patterns)

                    # Use lambda with default argument to capture codebase name correctly
                    self._file_watchers[name] = FileWatcher(
                        codebase_path=str(cb_config.repo_path),
                        on_file_changed=lambda path, cb=name: self.factory._handle_file_change(path, cb),
                        debounce_seconds=self.config.watch_debounce_seconds,
                        ignore_patterns=ignore_patterns,
                        watch_extensions=language_registry.get_all_extensions()
                    )
                    self._file_watchers[name].start()
                    logger.info(f"✓ File watcher started for '{name}': {cb_config.repo_path}")
                except ImportError as e:
                    logger.warning(
                        f"File watcher dependencies not available: {e}. "
                        "Install with: pip install watchdog pathspec"
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize file watcher for '{name}': {e}")

        logger.info("Nabu Agent - Initialization Complete")
        logger.info("=" * 60)

    async def shutdown(self) -> None:
        """
        Cleanup agent resources (lifecycle shutdown).

        Handles:
        - File watcher cleanup
        - Auto-indexing manager stop
        - Incremental updater cleanup
        - Database manager cleanup
        """
        logger.info("=" * 60)
        logger.info("Nabu Agent - Shutting Down")
        logger.info("=" * 60)

        # Cleanup file watchers
        for name, watcher in self._file_watchers.items():
            try:
                watcher.stop()
                logger.info(f"✓ File watcher stopped for '{name}'")
            except Exception as e:
                logger.warning(f"Error stopping file watcher for '{name}': {e}")

        # Shutdown auto-indexing
        if self.auto_indexer:
            try:
                await self.auto_indexer.stop()
                logger.info("✓ Auto-indexing manager stopped")
            except Exception as e:
                logger.warning(f"Error stopping auto-indexing: {e}")

        # Cleanup incremental updaters
        for name, updater in self.incremental_updaters.items():
            if hasattr(updater, 'conn'):
                try:
                    updater.conn.close()
                    logger.info(f"✓ Incremental updater closed for '{name}'")
                except Exception as e:
                    logger.warning(f"Error closing updater for '{name}': {e}")
        self.incremental_updaters.clear()

        # Cleanup database managers
        for name, manager in self.db_managers.items():
            try:
                manager.close()
                logger.info(f"✓ Database manager closed for '{name}'")
            except Exception as e:
                logger.warning(f"Error closing manager for '{name}': {e}")
        self.db_managers.clear()

        logger.info("Nabu Agent - Shutdown Complete")
        logger.info("=" * 60)
