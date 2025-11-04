"""
Reindex markdown formatter.

Compact markdown formatter for reindex tool output.
"""

from typing import Any, Dict
from ..tool_base import BaseToolMarkdownFormatter

class ReindexMarkdownFormatter(BaseToolMarkdownFormatter):
    """
    Compact markdown formatter for reindex tool output.
    
    Emphasizes operation status and frame statistics in minimal format.
    Reindex is infrequent operation so brevity is prioritized.
    """

    def format(self, data: Dict[str, Any], execution_time_ms: float = 0.0) -> str:
        """Format reindex output in compact style."""
        lines = []
        
        # Header with status
        status = data.get("status", "unknown")
        status_icon = "✅" if status == "completed" else "❌"
        
        lines.append(f"# Database Reindex {status_icon}")
        lines.append(f"Status: {status.upper()}")
        lines.append("")
        
        # Database path
        db_path = data.get("database_path", "unknown")
        repo_path = data.get("repository_path", "unknown")
        lines.append(f"**Database**: {db_path}")
        lines.append(f"**Repository**: {repo_path}")
        lines.append("")
        
        # Frame Statistics - compact tabular format
        frame_stats = data.get("frame_stats", {})
        total_frames = data.get("total_frames", 0)
        
        if frame_stats:
            lines.append(f"## Frame Statistics (Total: {total_frames})")
            lines.append("`frame_type (count)`")
            
            # Sort by count descending for quick scanning
            sorted_stats = sorted(frame_stats.items(), key=lambda x: x[1], reverse=True)
            for frame_type, count in sorted_stats:
                lines.append(f"{frame_type} ({count})")
            lines.append("")
        
        # Execution time footer (reindex is slow, show actual time)
        execution_sec = execution_time_ms / 1000.0
        if execution_sec > 60:
            execution_min = execution_sec / 60.0
            lines.append(f"*execution_time {execution_min:.2f}min ({execution_time_ms:.0f}ms)*")
        else:
            lines.append(f"*execution_time {execution_sec:.2f}s ({execution_time_ms:.0f}ms)*")
        
        return "\n".join(lines)

