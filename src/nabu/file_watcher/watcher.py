"""
Main file watcher implementation using watchdog library.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Any, Optional, List, Set

from nabu.file_watcher.debouncer import FileChangeDebouncer
from nabu.file_watcher.filters import FileFilter
from nabu.file_watcher.events import FileChangeEvent, FileChangeType

logger = logging.getLogger(__name__)


class FileWatcher:
    """
    Elegant file system watcher with debouncing and filtering.
    
    Features:
    - Monitors codebase directory for file changes
    - Debounces events (accumulates changes, fires after inactivity)
    - Filters files using gitignore-style patterns
    - Thread-safe callback execution via thread pool
    - Graceful start/stop with cleanup
    - Decoupled design - no hard dependencies on nabu internals
    
    Example:
        # Simple usage
        def handle_change(file_path: str):
            print(f"File changed: {file_path}")
        
        watcher = FileWatcher(
            codebase_path="/path/to/code",
            on_file_changed=handle_change,
            debounce_seconds=5.0
        )
        watcher.start()
        
        # ... watcher runs in background ...
        
        watcher.stop()
    
    Example with incremental updater:
        from nabu.incremental import IncrementalUpdater
        
        updater = IncrementalUpdater("nabu.kuzu")
        
        watcher = FileWatcher(
            codebase_path="/path/to/code",
            on_file_changed=updater.update_file,
            debounce_seconds=5.0,
            watch_extensions=['.py', '.java', '.cpp']
        )
        watcher.start()
    """
    
    def __init__(
        self,
        codebase_path: str,
        on_file_changed: Callable[[str], Any],
        debounce_seconds: float = 5.0,
        ignore_patterns: Optional[List[str]] = None,
        watch_extensions: Optional[List[str]] = None,
        executor: Optional[ThreadPoolExecutor] = None
    ):
        """
        Initialize file watcher.
        
        Args:
            codebase_path: Root directory to watch
            on_file_changed: Callback function(file_path: str) -> Any
                           Called for each changed file (in thread pool)
            debounce_seconds: Seconds to wait after last change before processing
            ignore_patterns: Gitignore-style patterns to exclude (None = use defaults)
            watch_extensions: File extensions to watch (None = watch all)
            executor: Optional ThreadPoolExecutor for callbacks
                     (None = create with max_workers=1 for serial execution)
        """
        self.codebase_path = Path(codebase_path).resolve()
        self.on_file_changed = on_file_changed
        self.debounce_seconds = debounce_seconds
        
        # Validate codebase path
        if not self.codebase_path.exists():
            raise ValueError(f"Codebase path does not exist: {self.codebase_path}")
        if not self.codebase_path.is_dir():
            raise ValueError(f"Codebase path is not a directory: {self.codebase_path}")
        
        # Setup file filter
        if ignore_patterns is None:
            ignore_patterns = FileFilter.default_ignores()
        
        self.file_filter = FileFilter(
            ignore_patterns=ignore_patterns,
            watch_extensions=watch_extensions,
            codebase_path=self.codebase_path
        )
        
        # Setup debouncer
        self.debouncer = FileChangeDebouncer(
            callback=self._process_batch,
            delay_seconds=debounce_seconds
        )
        
        # Thread pool for callback execution (serial by default for thread safety)
        self.executor = executor or ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="nabu_watcher"
        )
        self._owns_executor = (executor is None)
        
        # Watchdog components (initialized on start)
        self.observer = None
        self._event_handler = None
        self._running = False
        
        logger.info(
            f"FileWatcher initialized: path={self.codebase_path}, "
            f"debounce={debounce_seconds}s, "
            f"extensions={watch_extensions or 'all'}"
        )
    
    def start(self) -> None:
        """
        Start watching for file changes.
        
        Spawns watchdog observer in background thread.
        
        Raises:
            RuntimeError: If already started
            ImportError: If watchdog library not available
        """
        if self._running:
            raise RuntimeError("FileWatcher is already running")
        
        try:
            from watchdog.observers import Observer
            from watchdog.events import (
                FileSystemEventHandler,
                FileModifiedEvent,
                FileCreatedEvent,
                FileDeletedEvent,
                FileMovedEvent
            )
        except ImportError:
            raise ImportError(
                "watchdog library not available. Install with: pip install watchdog"
            )
        
        # Create custom event handler
        class NabuFileEventHandler(FileSystemEventHandler):
            """Handles file system events and forwards to debouncer."""
            
            def __init__(self, watcher: 'FileWatcher'):
                super().__init__()
                self.watcher = watcher
            
            def on_modified(self, event):
                if not event.is_directory:
                    self.watcher._handle_event(event.src_path, FileChangeType.MODIFIED)
            
            def on_created(self, event):
                if not event.is_directory:
                    self.watcher._handle_event(event.src_path, FileChangeType.CREATED)
            
            def on_deleted(self, event):
                if not event.is_directory:
                    self.watcher._handle_event(event.src_path, FileChangeType.DELETED)
            
            def on_moved(self, event):
                if not event.is_directory:
                    # Treat move destination as creation
                    self.watcher._handle_event(event.dest_path, FileChangeType.MOVED)
        
        # Create observer and event handler
        self._event_handler = NabuFileEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(
            self._event_handler,
            str(self.codebase_path),
            recursive=True
        )
        
        # Start observer thread
        self.observer.start()
        self._running = True
        
        logger.info(f"FileWatcher started: watching {self.codebase_path}")
    
    def stop(self, timeout: float = 10.0) -> None:
        """
        Stop watching and cleanup resources.
        
        Args:
            timeout: Seconds to wait for observer thread to stop
        """
        if not self._running:
            logger.debug("FileWatcher already stopped")
            return
        
        logger.info("Stopping FileWatcher...")
        
        # Stop observer
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=timeout)
                if self.observer.is_alive():
                    logger.warning(
                        f"Observer thread did not stop within {timeout}s"
                    )
            except Exception as e:
                logger.error(f"Error stopping observer: {e}")
            finally:
                self.observer = None
        
        # Flush pending changes
        try:
            self.debouncer.flush()
        except Exception as e:
            logger.error(f"Error flushing debouncer: {e}")
        
        # Stop debouncer
        self.debouncer.stop()
        
        # Shutdown executor if we own it
        if self._owns_executor and self.executor:
            try:
                self.executor.shutdown(wait=True, cancel_futures=False)
            except Exception as e:
                logger.error(f"Error shutting down executor: {e}")
        
        self._running = False
        logger.info("FileWatcher stopped")
    
    def _handle_event(self, file_path: str, change_type: FileChangeType) -> None:
        """
        Handle file system event.
        
        Filters file and adds to debouncer if it should be watched.
        Runs in watchdog observer thread.
        
        Args:
            file_path: Path to changed file
            change_type: Type of change
        """
        # Apply filter
        if not self.file_filter.should_watch(file_path):
            logger.debug(f"Filtered out: {file_path}")
            return
        
        # Normalize to absolute path
        abs_path = str(Path(file_path).resolve())
        
        logger.debug(f"Event: {change_type.value} - {abs_path}")
        
        # Add to debouncer
        self.debouncer.add_change(abs_path)
    
    def _process_batch(self, file_paths: Set[str]) -> None:
        """
        Process batch of changed files.
        
        Runs in debouncer timer thread. Submits callbacks to executor.
        
        Args:
            file_paths: Set of absolute file paths to process
        """
        logger.info(f"Processing batch of {len(file_paths)} file(s)")
        
        # Submit each file to executor
        futures = []
        for file_path in sorted(file_paths):
            future = self.executor.submit(
                self._execute_callback,
                file_path
            )
            futures.append(future)
        
        # Wait for all callbacks to complete (for logging purposes)
        success_count = 0
        error_count = 0
        
        for future in futures:
            try:
                future.result()
                success_count += 1
            except Exception as e:
                error_count += 1
                # Error already logged in _execute_callback
        
        logger.info(
            f"Batch complete: {success_count} succeeded, {error_count} failed"
        )
    
    def _execute_callback(self, file_path: str) -> None:
        """
        Execute user callback for single file.
        
        Runs in executor thread pool.
        
        Args:
            file_path: Absolute path to changed file
        """
        try:
            logger.debug(f"Executing callback for: {file_path}")
            result = self.on_file_changed(file_path)
            logger.debug(f"Callback completed for: {file_path}")
            return result
        except Exception as e:
            logger.error(
                f"Error in callback for {file_path}: {e}",
                exc_info=True
            )
            raise
    
    def is_running(self) -> bool:
        """Check if watcher is currently running."""
        return self._running
    
    def __enter__(self):
        """Context manager entry - starts watcher."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stops watcher."""
        self.stop()
        return False
    
    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return (
            f"FileWatcher(path={self.codebase_path}, "
            f"debounce={self.debounce_seconds}s, "
            f"status={status})"
        )
