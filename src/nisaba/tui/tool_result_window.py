"""Tool result window dataclass."""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from uuid import uuid4
import time


@dataclass
class ToolResultWindow:
    """Single persistent tool result window."""
    id: str = field(default_factory=lambda: str(uuid4()))
    window_type: str = "read_result"  # "read_result", "bash_result", "grep_result", "glob_result"
    content: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    opened_at: float = field(default_factory=time.time)

    # Optional fields depending on type
    file_path: str = ""  # for read_result
    start_line: int = 0  # for read_result
    end_line: int = 0    # for read_result
    command: str = ""    # for bash_result
    exit_code: int = 0   # for bash_result
    pattern: str = ""    # for grep_result
    glob_pattern: str = ""  # for glob_result
