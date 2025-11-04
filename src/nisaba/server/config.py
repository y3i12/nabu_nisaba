"""Configuration for nisaba MCP server."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from nisaba.config import MCPConfig, MCPContext


@dataclass
class NisabaConfig(MCPConfig):
    """
    Configuration for nisaba MCP server.

    Minimal config - just server settings and augments path.
    """

    # Override server name
    server_name: str = "nisaba"

    # Augments directory (default: cwd/.nisaba/augments)
    augments_dir: Optional[Path] = None

    # Composed augments file (default: cwd/.nisaba/nisaba_composed_augments.md)
    composed_augments_file: Optional[Path] = None

    def __post_init__(self):
        """Set defaults for augments paths if not provided."""
        if self.augments_dir is None:
            self.augments_dir = Path.cwd() / ".nisaba" / "augments"

        if self.composed_augments_file is None:
            self.composed_augments_file = Path.cwd() / ".nisaba" / "nisaba_composed_augments.md"
