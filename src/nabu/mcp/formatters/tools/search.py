"""
Search markdown formatter.

Compact markdown formatter for unified search results.
"""

from typing import Any, Dict
from ..tool_base import BaseToolMarkdownFormatter

class SearchToolMarkdownFormatter(BaseToolMarkdownFormatter):
    """Compact markdown formatter for unified search results."""

    def format(self, data: Dict[str, Any], execution_time_ms: float = 0.0) -> str:
        """Format search results in compact, scannable markdown."""
        results = data.get("results", [])
        metadata = data.get("metadata", {})
        query = data.get("query", "")

        lines = []

        # Header with query
        lines.append("# Search Results")
        lines.append(f"**Query:** `{query}`")
        lines.append("")

        if not results:
            lines.append("*No results found*")
            lines.append("")
            lines.append(f"*{metadata.get('returned', 0)} items returned of {metadata.get('total_candidates_before_filter', 0)} total matches*")
            lines.append(f"*execution_time {execution_time_ms:.2f}ms*")
            return "\n".join(lines)

        # Render each result
        for result in results:
            file_path = result.get("file_path", "")
            start_line = result.get("start_line", "")
            end_line = result.get("end_line", "")
            
            # File header with location
            lines.append(f"## {file_path}:{start_line}-{end_line}")
            
            # Scores and metadata on one line
            score = result.get("score", "-")
            rrf_score = result.get("rrf_score", "-")
            similarity = result.get("similarity", "-")
            mechanisms = ", ".join(result.get("mechanisms", []))
            
            # Format scores with proper precision
            score_str = f"{score:.2f}" if isinstance(score, (int, float)) else str(score)
            rrf_str = f"{rrf_score:.2f}" if isinstance(rrf_score, (int, float)) else str(rrf_score)
            sim_str = f"{similarity:.2f}" if isinstance(similarity, (int, float)) else str(similarity)
            
            lines.append(f"- score: {score_str} | rrf: {rrf_str} | similarity: {sim_str} | mechanisms: {mechanisms}")
            
            # Type and qualified name
            frame_type = result.get("type", "")
            qualified_name = result.get("qualified_name", "")
            lines.append(f"- type: {frame_type} | qualified_name: {qualified_name}")
            lines.append("")
            
            # Snippets (if available)
            snippets = result.get("snippets", [])
            if snippets:
                for snippet in snippets:
                    line_start = snippet.get("line_start", 0)
                    line_end = snippet.get("line_end", 0)
                    context = snippet.get("context", [])
                    
                    lines.append(f"### snippet (lines {line_start}-{line_end})")
                    
                    # Render context with line numbers
                    for i, line_content in enumerate(context):
                        line_num = line_start + i
                        lines.append(f"{line_num}: {line_content}")
                    lines.append("")
            
            # Content preview (if no snippets)
            elif "content_preview" in result:
                lines.append("### preview")
                preview = result.get("content_preview", "")
                # Truncate long previews
                if len(preview) > 500:
                    preview = preview[:500] + "\n    ..."
                lines.append(preview)
                lines.append("")

        # Footer with metadata
        lines.append("---")
        lines.append(f"*{metadata.get('returned', 0)} items returned of {metadata.get('total_candidates_before_filter', 0)} total matches*")

        return "\n".join(lines)

