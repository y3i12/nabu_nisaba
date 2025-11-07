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
class Split:
    """Split view of an editor window."""
    id: str = field(default_factory=lambda: str(uuid4()))
    parent_id: str = ""
    line_start: int = 1
    line_end: int = 1
    opened_at: float = field(default_factory=lambda: time.time())
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON."""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "opened_at": self.opened_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Split":
        """Restore from JSON."""
        return cls(
            id=data["id"],
            parent_id=data["parent_id"],
            line_start=data["line_start"],
            line_end=data["line_end"],
            opened_at=data.get("opened_at", time.time())
        )


@dataclass
class EditorWindow:
    """
    Represents an open editor window with change tracking.
    
    One editor per file - no duplicates allowed.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    file_path: Path = field(default_factory=Path)
    line_start: int = 1
    line_end: int = -1
    content: List[str] = field(default_factory=list)
    original_content: List[str] = field(default_factory=list)
    edits: List[Edit] = field(default_factory=list)
    splits: Dict[str, Split] = field(default_factory=dict)
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
            "edit_count": len(self.edits),
            "splits": {sid: split.to_dict() for sid, split in self.splits.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], content: List[str]) -> "EditorWindow":
        """Restore from JSON (content re-read from file)."""
        # Restore splits
        splits = {}
        for sid, split_data in data.get("splits", {}).items():
            splits[sid] = Split.from_dict(split_data)
        
        return cls(
            id=data["id"],
            file_path=Path(data["file_path"]),
            line_start=data["line_start"],
            line_end=data["line_end"],
            content=content,
            original_content=content.copy(),
            edits=[],  # Fresh start on reload
            splits=splits,
            last_mtime=data.get("last_mtime", 0.0),
            opened_at=data.get("opened_at", time.time())
        )
