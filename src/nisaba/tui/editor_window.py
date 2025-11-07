"""Editor window dataclasses for persistent code editing."""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Any, Dict
from uuid import uuid4


@dataclass
class Edit:
    """Record of a single edit operation."""
    timestamp: float
    operation: str  # 'replace', 'replace_lines', 'insert', 'delete'
    target: str  # old string or line range description
    old_content: str
    new_content: str


@dataclass
class EditorWindow:
    """
    Represents an open editor window with change tracking.
    
    One editor per file - no duplicates allowed.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    file_path: Path = field(default_factory=Path)
    line_start: int = 1
    line_end: int = -1  # -1 means end of file
    content: List[str] = field(default_factory=list)  # Current state
    original_content: List[str] = field(default_factory=list)  # For diffing
    edits: List[Edit] = field(default_factory=list)
    last_mtime: float = 0.0
    opened_at: float = field(default_factory=lambda: time.time())
    
    @property
    def is_dirty(self) -> bool:
        """Check if editor has unsaved changes."""
        return len(self.edits) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON persistence."""
        return {
            "id": self.id,
            "file_path": str(self.file_path),
            "line_start": self.line_start,
            "line_end": self.line_end,
            "opened_at": self.opened_at,
            "last_mtime": self.last_mtime,
            "edit_count": len(self.edits)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], content: List[str]) -> "EditorWindow":
        """Restore from JSON (content re-read from file)."""
        return cls(
            id=data["id"],
            file_path=Path(data["file_path"]),
            line_start=data["line_start"],
            line_end=data["line_end"],
            content=content,
            original_content=content.copy(),
            edits=[],  # Fresh start on reload
            last_mtime=data.get("last_mtime", 0.0),
            opened_at=data.get("opened_at", time.time())
        )
