"""
File change event types for the watcher.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FileChangeType(Enum):
    """Types of file system changes."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileChangeEvent:
    """
    Represents a file system change event.
    
    Attributes:
        file_path: Absolute path to the changed file
        change_type: Type of change that occurred
        is_directory: Whether the path is a directory
    """
    file_path: str
    change_type: FileChangeType
    is_directory: bool = False
    
    @property
    def path(self) -> Path:
        """Get Path object for file_path."""
        return Path(self.file_path)
    
    def __str__(self) -> str:
        return f"{self.change_type.value}: {self.file_path}"
