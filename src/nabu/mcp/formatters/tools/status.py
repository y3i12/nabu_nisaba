"""
Show status markdown formatter.

Unified formatter for show_status tool output.
"""

from typing import Any, Dict
from pathlib import Path
from ..tool_base import BaseToolMarkdownFormatter

class ShowStatusMarkdownFormatter(BaseToolMarkdownFormatter):
    """
    Unified formatter for show_status tool output.
    
    Handles progressive disclosure of codebase health and database diagnostics
    based on detail_level (summary/detailed/debug).
    """
    
    def format(self, data: Dict[str, Any], execution_time_ms: float = 0.0) -> str:
        """Format show_status output with progressive detail levels."""
        lines = []
        
        # Header
        active_codebase = data.get("active_codebase", "unknown")
        lines.append(f"# Status (active: {active_codebase})")
        lines.append("")
        
        # Codebases section
        codebases = data.get("codebases", [])
        if codebases:
            # Determine if this is detailed output based on presence of 'role' field
            has_detail = any(cb.get("role") is not None for cb in codebases)
            
            if has_detail:
                lines.append("## Codebases `name [role] (frames, status) watch? ✓active`")
            else:
                lines.append("## Codebases `name (frames, status) ✓active`")
            
            for cb in codebases:
                name = cb.get("name", "unknown")
                frame_count = cb.get("frame_count", "?")
                status = cb.get("status", "unknown")
                active = "✓" if cb.get("is_active", False) else " "
                
                # Status icon
                status_icon = "✅" if status == "healthy" else "❌"
                
                if has_detail:
                    role = cb.get("role", "unknown")
                    watch = "👁" if cb.get("watch_enabled", False) else "  "
                    lines.append(f"{name} [{role}] ({frame_count}, {status_icon} {status}) {watch} {active}")
                else:
                    lines.append(f"{name} ({frame_count}, {status_icon} {status}) {active}")
            lines.append("")
            
            # Paths section (only for detailed output)
            if has_detail:
                lines.append("## Paths")
                for cb in codebases:
                    name = cb.get("name", "unknown")
                    db_path = cb.get("db_path", "unknown")
                    lines.append(f"**{name}**: {Path(db_path).name}")
                lines.append("")

                # Confidence Distribution section (only for detailed output)
                lines.append("## Confidence Distribution")
                for cb in codebases:
                    name = cb.get("name", "unknown")
                    conf_dist = cb.get("confidence_distribution")

                    if conf_dist:
                        total = sum(conf_dist.values())
                        if total > 0:
                            lines.append(f"**{name}**: {total:,} edges")
                            for tier in ["HIGH", "MEDIUM", "LOW", "SPECULATIVE"]:
                                count = conf_dist.get(tier, 0)
                                percent = (count / total) * 100
                                lines.append(f"  - {tier}: {count:,} ({percent:.1f}%)")
                        else:
                            lines.append(f"**{name}**: No edges found")
                    else:
                        lines.append(f"**{name}**: Distribution unavailable")
                lines.append("")
        else:
            lines.append("*(No codebases configured)*")
            lines.append("")

        # Database diagnostics (if present)
        db_info = data.get("database")
        if db_info:
            lines.append("## Database")
            lines.append(f"- Active connections: {db_info.get('active_connections', '?')}")
            lines.append(f"- Updater connected: {db_info.get('updater_connected', '?')}")
            
            # Debug-level details
            if "dev_mode" in db_info:
                lines.append(f"- Dev mode: {db_info.get('dev_mode', '?')}")
                lines.append(f"- Database path: {Path(db_info.get('database_path', '?')).name}")
                lines.append(f"- Codebase: {db_info.get('codebase_name', '?')}")
            lines.append("")
        
        # Execution time footer
        lines.append(f"*execution_time {execution_time_ms:.2f}ms*")
        
        return "\n".join(lines)

