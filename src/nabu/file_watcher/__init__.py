"""
File watcher module for automatic codebase monitoring and incremental updates.

This module provides elegant, decoupled file watching capabilities with:
- Debounced file change events
- Gitignore-style pattern filtering  
- Thread-safe operation
- Easy integration with IncrementalUpdater
"""

from nabu.file_watcher.watcher import FileWatcher
from nabu.file_watcher.debouncer import FileChangeDebouncer
from nabu.file_watcher.filters import FileFilter
from nabu.file_watcher.events import FileChangeEvent

__all__ = [
    'FileWatcher',
    'FileChangeDebouncer', 
    'FileFilter',
    'FileChangeEvent',
]
