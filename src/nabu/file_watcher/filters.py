"""
File filtering logic with gitignore-style pattern support.
"""

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class FileFilter:
    """
    Filters files based on gitignore-style patterns and extensions.
    
    Uses pathspec library for gitignore compatibility. Supports:
    - Extension whitelist (only watch specific file types)
    - Ignore patterns (exclude files/directories)
    - Standard gitignore syntax
    
    Example:
        filter = FileFilter(
            ignore_patterns=['.git/**', '*.pyc', '__pycache__/**'],
            watch_extensions=['.py', '.java', '.cpp'],
            codebase_path=Path('/path/to/code')
        )
        
        if filter.should_watch('/path/to/code/src/main.py'):
            # Process this file
    """
    
    def __init__(
        self,
        ignore_patterns: List[str],
        watch_extensions: Optional[List[str]] = None,
        codebase_path: Optional[Path] = None
    ):
        """
        Initialize file filter.
        
        Args:
            ignore_patterns: List of gitignore-style patterns to exclude
            watch_extensions: Optional list of extensions to watch (e.g., ['.py', '.java'])
                            If None, all extensions are watched
            codebase_path: Base path for computing relative paths
        """
        self.watch_extensions = set(watch_extensions) if watch_extensions else None
        self.codebase_path = codebase_path.resolve() if codebase_path else None
        
        # Load gitignore patterns using pathspec
        try:
            import pathspec
            self.spec = pathspec.PathSpec.from_lines(
                'gitwildmatch',
                ignore_patterns
            )
            logger.debug(f"Loaded {len(ignore_patterns)} ignore patterns")
        except ImportError:
            logger.warning(
                "pathspec library not available - ignore patterns will not work. "
                "Install with: pip install pathspec"
            )
            self.spec = None
        except Exception as e:
            logger.error(f"Failed to load ignore patterns: {e}")
            self.spec = None
    
    def should_watch(self, file_path: str) -> bool:
        """
        Check if file should be watched.
        
        Args:
            file_path: Absolute or relative path to file
            
        Returns:
            True if file should be watched, False otherwise
        """
        path = Path(file_path)
        
        # Skip directories
        if path.is_dir():
            return False
        
        # Extension check (whitelist)
        if self.watch_extensions and path.suffix not in self.watch_extensions:
            return False
        
        # Gitignore check
        if self.spec and self.codebase_path:
            try:
                # Compute relative path for pattern matching
                if path.is_absolute():
                    rel_path = path.relative_to(self.codebase_path)
                else:
                    rel_path = path
                
                # Check if path matches any ignore pattern
                if self.spec.match_file(str(rel_path)):
                    return False
            except ValueError:
                # Path is outside codebase_path - don't watch
                return False
            except Exception as e:
                logger.warning(f"Error checking ignore patterns for {file_path}: {e}")
                # On error, allow watching (fail-open)
        
        return True
    
    @staticmethod
    def default_ignores() -> List[str]:
        """
        Get default ignore patterns.
        
        Covers common temporary files, build artifacts, and version control.
        
        Returns:
            List of gitignore-style patterns
        """
        return [
            # Version control
            '.git/**',
            '.svn/**',
            '.hg/**',
            
            # Python
            '__pycache__/**',
            '*.pyc',
            '*.pyo',
            '*.pyd',
            '.Python',
            '*.so',
            '*.egg',
            '*.egg-info/**',
            'dist/**',
            'build/**',
            '.pytest_cache/**',
            '.mypy_cache/**',
            '.tox/**',
            '.venv/**',
            'venv/**',
            'ENV/**',
            'env/**',
            
            # Node.js
            'node_modules/**',
            'npm-debug.log',
            'yarn-error.log',
            
            # Java
            'target/**',
            '*.class',
            '*.jar',
            '*.war',
            
            # C/C++
            '*.o',
            '*.obj',
            '*.a',
            '*.lib',
            '*.exe',
            '*.out',
            
            # IDE
            '.idea/**',
            '.vscode/**',
            '*.swp',
            '*.swo',
            '*~',
            '.DS_Store',
            
            # Databases
            '*.kuzu/**',
            '.kuzu/**',
            '*.db',
            '*.sqlite',
            '*.sqlite3',
            
            # Logs
            '*.log',
            'logs/**',
            
            # Temporary files
            '*.tmp',
            '*.temp',
            '.cache/**',
        ]
