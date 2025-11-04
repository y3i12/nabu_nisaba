"""
Debouncing logic for file change events.
"""

import logging
import threading
from typing import Callable, Set, Optional

logger = logging.getLogger(__name__)


class FileChangeDebouncer:
    """
    Accumulates file changes and triggers callback after inactivity period.
    
    Thread-safe debouncing mechanism:
    - Accumulates file paths in a set (deduplicates)
    - Resets timer on each new event
    - Calls callback after delay_seconds of inactivity
    - Ensures callback is only executed once per batch
    
    Example:
        def process_files(files: Set[str]):
            print(f"Processing {len(files)} files: {files}")
        
        debouncer = FileChangeDebouncer(
            callback=process_files,
            delay_seconds=5.0
        )
        
        # Add changes as they occur
        debouncer.add_change('/path/to/file1.py')
        debouncer.add_change('/path/to/file2.py')
        debouncer.add_change('/path/to/file1.py')  # Deduplicated
        
        # After 5 seconds of no new changes:
        # -> process_files({'/path/to/file1.py', '/path/to/file2.py'})
    """
    
    def __init__(
        self, 
        callback: Callable[[Set[str]], None], 
        delay_seconds: float
    ):
        """
        Initialize debouncer.
        
        Args:
            callback: Function to call with accumulated file paths
            delay_seconds: Seconds to wait after last change before firing
        """
        self.callback = callback
        self.delay_seconds = delay_seconds
        self.pending_files: Set[str] = set()
        self.timer: Optional[threading.Timer] = None
        self.lock = threading.Lock()
        self._stopped = False
        
        logger.debug(f"FileChangeDebouncer initialized with {delay_seconds}s delay")
    
    def add_change(self, file_path: str) -> None:
        """
        Add file to pending changes and reset timer.
        
        Thread-safe. Can be called from multiple threads.
        
        Args:
            file_path: Absolute path to changed file
        """
        if self._stopped:
            logger.debug(f"Debouncer stopped, ignoring change: {file_path}")
            return
        
        with self.lock:
            self.pending_files.add(file_path)
            self._reset_timer()
            
        logger.debug(
            f"Added change: {file_path} "
            f"(total pending: {len(self.pending_files)})"
        )
    
    def _reset_timer(self) -> None:
        """
        Cancel existing timer and start new one.
        
        Must be called with lock held.
        """
        # Cancel existing timer
        if self.timer is not None:
            self.timer.cancel()
        
        # Start new timer
        self.timer = threading.Timer(
            self.delay_seconds,
            self._fire_callback
        )
        self.timer.daemon = True  # Don't block program exit
        self.timer.start()
        
        logger.debug(f"Timer reset: will fire in {self.delay_seconds}s")
    
    def _fire_callback(self) -> None:
        """
        Execute callback with accumulated changes.
        
        Runs in timer thread. Acquires lock only briefly to copy files.
        """
        # Get copy of pending files while holding lock
        with self.lock:
            if not self.pending_files or self._stopped:
                return
            
            files_to_process = self.pending_files.copy()
            self.pending_files.clear()
            self.timer = None
        
        # Execute callback outside lock to avoid blocking add_change
        logger.info(
            f"Debounce timer fired: processing {len(files_to_process)} file(s)"
        )
        
        try:
            self.callback(files_to_process)
            logger.info(f"Callback completed successfully")
        except Exception as e:
            logger.error(
                f"Error in debounce callback: {e}",
                exc_info=True
            )
    
    def flush(self) -> None:
        """
        Immediately process pending changes without waiting for timer.
        
        Useful for graceful shutdown or testing.
        """
        with self.lock:
            # Cancel timer if running
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None
            
            # Process pending files if any
            if self.pending_files:
                files_to_process = self.pending_files.copy()
                self.pending_files.clear()
        
        if files_to_process:
            logger.info(f"Flushing {len(files_to_process)} pending file(s)")
            try:
                self.callback(files_to_process)
            except Exception as e:
                logger.error(f"Error in flush callback: {e}", exc_info=True)
    
    def stop(self) -> None:
        """
        Stop debouncer and cancel pending timer.
        
        Does not flush pending changes. Call flush() first if needed.
        """
        with self.lock:
            self._stopped = True
            
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None
            
            pending_count = len(self.pending_files)
            self.pending_files.clear()
        
        if pending_count > 0:
            logger.warning(
                f"Debouncer stopped with {pending_count} pending file(s) "
                "(not processed)"
            )
        else:
            logger.debug("Debouncer stopped")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.stop()
        return False
