"""Codebase configuration for multi-codebase support."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List


@dataclass
class CodebaseConfig:
    """
    Configuration for a single codebase.
    
    Multiple codebases can be registered in nabu, each with its own
    database and repository path.
    """
    name: str                           # Identifier: "my_project", "target_lib"
    repo_path: Path                     # Source code location
    db_path: Path                       # KuzuDB database file
    role: str = "active"                # "active" | "reference" | "readonly"
    watch_enabled: bool = True          # Enable file watching for this codebase
    
    def __post_init__(self):
        """Validate configuration."""
        if self.role not in ["active", "reference", "readonly"]:
            raise ValueError(f"Invalid role: {self.role}. Must be active, reference, or readonly")
        
        # Convert to Path if needed
        self.repo_path = Path(self.repo_path)
        self.db_path = Path(self.db_path)
    
    @classmethod
    def from_string(cls, spec: str) -> "CodebaseConfig":
        """
        Parse codebase from CLI string.
        
        Format: name:repo_path:db_path[:role[:watch_enabled]]
        
        Examples:
            "my_project:/path/to/code:/path/to/db.kuzu"
            "my_project:/path/to/code:/path/to/db.kuzu:active"
            "target_lib:/path/to/lib:/path/to/lib.kuzu:reference:false"
        
        Args:
            spec: Colon-separated specification string
            
        Returns:
            CodebaseConfig instance
            
        Raises:
            ValueError: If format is invalid
        """
        parts = spec.split(":")
        
        if len(parts) < 3:
            raise ValueError(
                f"Invalid codebase spec: {spec}. "
                "Expected format: name:repo_path:db_path[:role[:watch_enabled]]"
            )
        
        name = parts[0]
        repo_path = Path(parts[1])
        db_path = Path(parts[2])
        role = parts[3] if len(parts) > 3 else "active"
        watch_enabled = parts[4].lower() == "true" if len(parts) > 4 else True
        
        return cls(
            name=name,
            repo_path=repo_path,
            db_path=db_path,
            role=role,
            watch_enabled=watch_enabled
        )
