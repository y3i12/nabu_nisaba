# Nabu File Watcher

Elegant file system monitoring module for automatic incremental database updates.

## Overview

The file watcher module provides automatic monitoring of codebase changes with:

- **Debounced events** - Accumulates changes and processes them after inactivity period
- **Gitignore filtering** - Respects .gitignore-style patterns to exclude unwanted files
- **Thread-safe operation** - Safe concurrent execution with proper synchronization
- **Decoupled design** - No hard dependencies on nabu internals
- **Easy integration** - Simple API for use with IncrementalUpdater

## Architecture

```
src/nabu/file_watcher/
├── __init__.py           # Module exports
├── watcher.py            # Main FileWatcher class
├── debouncer.py          # Debouncing logic
├── filters.py            # File filtering with gitignore support
├── events.py             # Event types and handlers
└── README.md            # This file
```

### Components

#### FileWatcher (`watcher.py`)
Main class that orchestrates file monitoring:
- Uses watchdog library for filesystem events
- Integrates with FileFilter and FileChangeDebouncer
- Executes callbacks in thread pool for safety
- Provides context manager interface

#### FileChangeDebouncer (`debouncer.py`)
Accumulates file changes and triggers callback after inactivity:
- Configurable delay (default: 5 seconds)
- Thread-safe accumulation with locks
- Deduplicates changes automatically
- Supports flush for graceful shutdown

#### FileFilter (`filters.py`)
Filters files based on patterns and extensions:
- Uses pathspec library for gitignore compatibility
- Extension whitelist support
- Default ignore patterns for common files
- Relative path resolution

#### FileChangeEvent (`events.py`)
Event types and data structures:
- FileChangeType enum (CREATED, MODIFIED, DELETED, MOVED)
- FileChangeEvent dataclass with metadata

## Usage

### Basic Usage

```python
from nabu.file_watcher import FileWatcher

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
```

### With Context Manager

```python
with FileWatcher(codebase_path="/path/to/code",
                 on_file_changed=handle_change) as watcher:
    # Watcher is running
    pass
# Watcher automatically stopped
```

### With IncrementalUpdater

```python
from nabu.incremental import IncrementalUpdater
from nabu.file_watcher import FileWatcher

updater = IncrementalUpdater("nabu.kuzu")

watcher = FileWatcher(
    codebase_path="/path/to/code",
    on_file_changed=updater.update_file,
    debounce_seconds=5.0,
    watch_extensions=['.py', '.java', '.cpp']
)

watcher.start()
```

### Custom Filtering

```python
watcher = FileWatcher(
    codebase_path="/path/to/code",
    on_file_changed=handle_change,
    ignore_patterns=[
        '.git/**',
        '__pycache__/**',
        '*.pyc',
        'build/**',
    ],
    watch_extensions=['.py']  # Only Python files
)
```

## Configuration

### MCP Server Integration

The file watcher is automatically integrated with the nabu MCP server when enabled in configuration.

**Configuration file** (`src/nabu/mcp/config/contexts/development.yml`):

```yaml
watch_enabled: true
watch_debounce_seconds: 5.0
extra_ignore_patterns:
  - .git/**
  - __pycache__/**
  - "*.pyc"
  - .venv/**
watch_extensions:
  - .py
  - .java
  - .cpp
```

### NabuConfig Fields

- `watch_enabled: bool` - Enable/disable file watching (default: False)
- `watch_debounce_seconds: float` - Seconds to wait after last change (default: 5.0)
- `extra_ignore_patterns: List[str]` - Gitignore-style patterns to exclude (default: FileFilter.default_ignores())
- `watch_extensions: List[str]` - File extensions to watch (default: None = all)

## Thread Safety

The module is designed for thread-safe operation:

- **KuzuConnectionManager** - Thread-safe singleton with locks
- **IncrementalUpdater** - Each instance has own connection
- **Watchdog observer** - Runs in separate thread
- **ThreadPoolExecutor** - Callbacks executed serially (max_workers=1) by default
- **Debouncer** - Thread-safe with locks and timers

### Important Note

The default configuration uses `max_workers=1` for the callback executor to ensure serial execution. This prevents concurrent writes to the database which could cause issues since `IncrementalUpdater` has a persistent connection.

## Dependencies

Required packages (automatically installed):
- `watchdog>=3.0.0` - File system event monitoring
- `pathspec>=0.11.0` - Gitignore pattern matching

## Design Decisions

### 5-Second Debounce
- LLM agents can work with slightly stale data
- Batch updates are more efficient than per-file updates
- Reduces database write contention
- Prevents redundant updates during rapid file changes

### Serial Callback Execution
- Prevents concurrent database writes
- Simpler than managing multiple updater instances
- Acceptable performance for typical file change frequency

### Graceful Degradation
- File watcher is optional - system works without it
- Missing dependencies logged as warnings
- Failures don't crash MCP server

### Decoupled Design
- No hard dependencies on nabu internals
- Callback pattern for flexibility
- Can be instantiated independently
- Easy to test in isolation

## Example: MCP Server Integration

The file watcher is integrated into `NabuMCPFactorySingleProcess`:

```python
# In server_lifespan():
if self.config.watch_enabled and self.incremental_updater:
    self._file_watcher = FileWatcher(
        codebase_path=str(self.config.repo_path),
        on_file_changed=self._handle_file_change,
        debounce_seconds=self.config.watch_debounce_seconds,
        ignore_patterns=self.config.extra_ignore_patterns,
        watch_extensions=self.config.watch_extensions
    )
    self._file_watcher.start()

# Callback handler:
def _handle_file_change(self, file_path: str) -> None:
    result = self.incremental_updater.update_file(file_path)
    if result.success:
        logger.info(f"✓ Auto-updated {file_path}")
```

## Logging

The module uses Python's standard logging:

- `DEBUG` - Individual file events, debouncer activity
- `INFO` - Batch processing, successful updates
- `WARNING` - Filtered files, failed updates, missing dependencies
- `ERROR` - Callback exceptions, observer failures

## Future Enhancements

Potential improvements (not implemented):

- [ ] Rate limiting for extremely busy directories
- [ ] Configurable callback parallelism
- [ ] File change statistics/metrics
- [ ] Integration with git hooks for pre-commit updates
- [ ] Support for remote file systems (networked drives)
- [ ] Selective file watching by directory

## Testing

Basic smoke test:
```python
python3 -c "from nabu.file_watcher import FileWatcher; print('✓ Import successful')"
```

## Troubleshooting

### "watchdog library not available"
Install dependencies: `pip install watchdog pathspec`

### "pathspec library not available"
Ignore patterns won't work. Install: `pip install pathspec`

### File watcher not starting
- Check `watch_enabled: true` in configuration
- Verify `incremental_updater` is initialized
- Check logs for initialization errors

### Too many events
- Increase `watch_debounce_seconds`
- Add more patterns to `extra_ignore_patterns`
- Restrict with `watch_extensions`

## License

Same as nabu project (MIT).
