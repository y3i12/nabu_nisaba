"""
Codebases markdown formatters.

Formatters for list_codebases and activate_codebase tools.
"""

from typing import Any, Dict
from pathlib import Path
from ..tool_base import BaseToolMarkdownFormatter

class ListCodebasesMarkdownFormatter(BaseToolMarkdownFormatter):
    """
    Compact markdown formatter for list_codebases tool output.
    
    Emphasizes codebase configuration in scannable format.
    """
    
    def format(self, data: Dict[str, Any],) -> str:
        """Format list_codebases output in compact style."""
        lines = []
        
        # Header
        total_count = data.get("total_count", 0)
        active_codebase = data.get("active_codebase", "unknown")
        lines.append(f"# Registered Codebases ({total_count})")
        lines.append(f"Active: **{active_codebase}**")
        lines.append("")
        
        # Codebases - table format
        codebases = data.get("codebases", [])
        if codebases:
            lines.append("## Codebases")
            lines.append("| Name | Role | Watch | Active |")
            lines.append("|------|------|-------|--------|")
            for cb in codebases:
                name = cb.get("name", "unknown")
                role = cb.get("role", "unknown")
                watch = "👁" if cb.get("watch_enabled", False) else "-"
                active = "✓" if cb.get("is_active", False) else "-"
                
                lines.append(f"| {name} | {role} | {watch} | {active} |")
            lines.append("")
            
            # Paths section
            lines.append("## Paths")
            for cb in codebases:
                name = cb.get("name", "unknown")
                repo_path = cb.get("repo_path", "unknown")
                db_path = cb.get("db_path", "unknown")
                lines.append(f"**{name}**:")
                lines.append(f"  Repo: {repo_path}")
                lines.append(f"  DB: {db_path}")
            lines.append("")
        else:
            lines.append("*(No codebases registered)*")
            lines.append("")

        return "\n".join(lines)


class ActivateCodebaseMarkdownFormatter(BaseToolMarkdownFormatter):
    """
    Compact markdown formatter for activate_codebase tool output.
    
    Emphasizes activation confirmation with before/after state.
    Designed for quick verification of codebase switching.
    """
    
    def format(self, data: Dict[str, Any],) -> str:
        """Format activate_codebase output in compact style."""
        lines = []
        
        # Extract data
        status = data.get("status", "unknown")
        codebase = data.get("codebase", "unknown")
        previous = data.get("previous_active", "unknown")
        role = data.get("role", "unknown")
        
        # Header with status icon
        status_icon = "✅" if status == "activated" else "❌"
        lines.append(f"# Codebase Activation {status_icon}")
        lines.append("")
        
        # Activation summary
        lines.append("## Status")
        lines.append(f"**Previous**: {previous}")
        lines.append(f"**Current**: {codebase} [{role}]")
        lines.append("")
        
        # Paths
        repo_path = data.get("repo_path", "unknown")
        db_path = data.get("db_path", "unknown")
        lines.append("## Paths")
        lines.append(f"**Repo**: {repo_path}")
        lines.append(f"**DB**: {db_path}")
        lines.append("")
        
        return "\n".join(lines)

