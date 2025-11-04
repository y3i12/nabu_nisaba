"""File window dataclass for persistent code visibility."""

from dataclasses import dataclass, field
from typing import Dict, Any, List
from pathlib import Path
from uuid import uuid4


@dataclass(slots=True)
class FileWindow:
    """Single persistent file window."""
    id: str = field(default_factory=lambda: str(uuid4()))
    file_path: Path = field(default_factory=Path)
    start_line: int = 1
    end_line: int = 1
    content: List[str] = field(default_factory=list)
    window_type: str = "range"  # "frame_body", "range", "search_result"
    metadata: Dict[str, Any] = field(default_factory=dict)
    opened_at: float = field(default_factory=lambda: __import__('time').time())
