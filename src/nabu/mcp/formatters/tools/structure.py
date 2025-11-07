"""
Show structure markdown formatter.

Compact markdown formatter for show_structure tool output.
"""

from typing import Any, Dict
from pathlib import Path
from ..tool_base import BaseToolMarkdownFormatter

class ShowStructureMarkdownFormatter(BaseToolMarkdownFormatter):
    """
    Compact markdown formatter for show_structure tool output.
    Optimized for code skeleton display with minimal wrapper overhead.
    """

    def format(self, data: Dict[str, Any],) -> str:
        """Format show_structure output in compact style (skeleton + optional relationships)."""
        lines = []
        
        # Header with frame identification
        frame_type = data.get("frame_type", "UNKNOWN")
        name = data.get("name", "unknown")
        qualified_name = data.get("qualified_name", "unknown")
        
        lines.append(f"# {name} ({frame_type})")
        lines.append(f"FQN: {qualified_name}")
        
        # Location info (compact single line)
        file_path = data.get("file_path", "")
        location = data.get("location", "")
        if file_path:
            # For skeleton mode: show full path with line range
            line_range = location.split(':')[-1] if ':' in location else ''
            if line_range:
                lines.append(f"Location: {file_path}:{line_range}")
            else:
                lines.append(f"Location: {file_path}")
        else:
            lines.append(f"Location: {location}")
        
        # Metadata line
        language = data.get("language", "unknown")
        detail_level = data.get("detail_level", "minimal")
        recursion_depth = data.get("recursion_depth", 0)
        children_count = data.get("children_count", 0)
        
        lines.append(f"Language: {language}, Detail: {detail_level}, Depth: {recursion_depth}, Children: {children_count}")
        lines.append("")
        
        # Check if we have relationship data (CLASS frames with include_relationships=True)
        inheritance = data.get("inheritance", {})
        called_by = data.get("called_by", [])
        dependencies = data.get("dependencies", [])
        metrics = data.get("metrics", {})
        
        has_inheritance = bool(inheritance and (inheritance.get("parents") or inheritance.get("children")))
        has_callers = bool(called_by)
        has_deps = bool(dependencies)
        has_metrics = bool(metrics)
        has_relationships = has_inheritance or has_callers or has_deps or has_metrics
        
        # Skeleton code block (the main content)
        skeleton = data.get("skeleton", "")
        if skeleton:
            lines.append("## Skeleton")
            lines.append("```" + language)
            lines.append(skeleton.rstrip())
            lines.append("```")
            lines.append("")
        
        # If we have relationship data, format it
        if has_relationships:
            # Parents - compact format
            lines.append("## Parents (parent_name(file:line_range))")
            parents = inheritance.get("parents", [])
            if parents:
                for parent in parents:
                    parent_name = parent.get("name", "unknown")
                    parent_file = parent.get("file_path", "")
                    filename = Path(parent_file).name if parent_file else "unknown"
                    lines.append(f"{parent_name} ({filename})")
            else:
                lines.append("")
            lines.append("")

            # Children - compact format
            lines.append("## Children (child_name(file:line_range))")
            children = inheritance.get("children", [])
            if children:
                for child in children:
                    child_name = child.get("name", "unknown")
                    child_location = child.get("location", "")
                    lines.append(f"{child_name} ({child_location})")
            else:
                lines.append("")
            lines.append("")

            # Called By - compact single-line format
            lines.append("## Called by `caller_fqn(file:line, confidence) -> callee`")
            if called_by:
                for caller in called_by:
                    caller_fqn = caller.get("caller_qualified_name", "unknown")
                    caller_location = caller.get("location", "")
                    conf = caller.get("confidence", 0.0)
                    method = caller.get("called_method", "unknown")
                    lines.append(f"{caller_fqn}({caller_location}, {conf:.2f}) -> {method}")
            else:
                lines.append("")
            lines.append("")

            # Dependencies (optional - only if present and non-empty)
            if dependencies:
                lines.append("## Dependencies `name (relationship)`")
                for dep in dependencies[:10]:  # Limit to 10 for token efficiency
                    dep_name = dep.get("name", "unknown")
                    rel = dep.get("relationship", "unknown")
                    lines.append(f"{dep_name} ({rel})")
                lines.append("")

            # Metrics - single-line compact format
            if has_metrics:
                lines.append("## Metrics")
                lines.append(f"Methods: {metrics.get('method_count', 0)}")
                lines.append(f"Instance fields: {metrics.get('instance_field_count', 0)}")
                lines.append(f"Static fields: {metrics.get('static_field_count', 0)}")
                lines.append(f"Parents: {metrics.get('parent_count', 0)}")
                lines.append(f"Children: {metrics.get('child_count', 0)}")
                lines.append(f"Callers: {metrics.get('caller_count', 0)}")
                lines.append(f"Dependencies: {metrics.get('dependency_count', 0)}")
                lines.append(f"Complexity Rating: {metrics.get('complexity_rating', 'UNKNOWN')}")
                lines.append("")
            
        # Token estimation
        estimated_tokens = data.get("estimated_tokens", 0)
        lines.append(f"**Estimated tokens**: ~{estimated_tokens}")
        lines.append("")
        
        return "\n".join(lines)

