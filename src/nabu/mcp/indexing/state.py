"""State management for auto-indexing."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IndexingState(str, Enum):
    """States for codebase indexing lifecycle."""
    UNINDEXED = "unindexed"      # Detected as empty, not queued yet
    QUEUED = "queued"            # In queue, waiting for worker
    INDEXING = "indexing"        # Currently being processed
    INDEXED = "indexed"          # Complete, ready for queries
    ERROR = "error"              # Failed, needs manual rebuild


@dataclass
class IndexingStatus:
    """Status information for a codebase indexing operation."""
    codebase: str
    state: IndexingState
    error_message: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
