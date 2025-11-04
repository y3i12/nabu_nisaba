"""
Markdown output formatter.

Converts tool response data into human-readable markdown format.
Supports tool-specific compact formatting and generic fallback.
"""

from typing import Any
from .base import BaseOutputFormatter
from .tool_registry import ToolMarkdownFormatterRegistry


class MarkdownOutputFormatter(BaseOutputFormatter):
    """
    Markdown output formatter.

    Converts tool response data into human-readable markdown format.
    Supports both tool-specific compact formatting and generic fallback.
    Tool-specific formatters provide 60-70% token reduction for LLM consumption.
    """

    def __init__(self):
        """Initialize with tool formatter registry."""
        self.tool_formatter_registry = ToolMarkdownFormatterRegistry()

    def format(self, data: Any, tool_name: str = "") -> str:
        """
        Format tool response data as markdown.

        Checks for tool-specific formatter first, falls back to generic formatting.

        Args:
            data: Tool response data (dict, list, primitive, etc.)
            tool_name: Name of the tool generating the response

        Returns:
            Markdown-formatted string
        """
        # Extract execution time if present (for tool-specific formatters)
        execution_time_ms = 0.0
        if isinstance(data, dict):
            execution_time_ms = data.get("execution_time_ms", 0.0)

        # Check for tool-specific formatter
        if tool_name and self.tool_formatter_registry.has_formatter(tool_name):
            formatter = self.tool_formatter_registry.get_formatter(tool_name)
            return formatter.format(data, execution_time_ms)

        # Fall back to generic formatting
        return self._generic_format(data, tool_name)

    def _generic_format(self, data: Any, tool_name: str = "") -> str:
        """
        Generic markdown formatting (original implementation).

        Args:
            data: Tool response data
            tool_name: Tool name (for header)

        Returns:
            Generic markdown-formatted string
        """
        if tool_name:
            output = [f"# {tool_name} Output\n"]
        else:
            output = []

        output.append(self._format_value(data, level=0))
        return "\n".join(output)

    def _format_value(self, value: Any, level: int = 0) -> str:
        """
        Recursively format a value as markdown.

        Args:
            value: Value to format
            level: Current nesting level

        Returns:
            Markdown-formatted string
        """
        indent = "  " * level

        if value is None:
            return f"{indent}*None*"

        elif isinstance(value, bool):
            return f"{indent}**{value}**"

        elif isinstance(value, (int, float)):
            return f"{indent}{value}"

        elif isinstance(value, str):
            # Handle multi-line strings
            if "\n" in value:
                lines = value.split("\n")
                return "\n".join(f"{indent}    {line}" for line in lines)
            return f"{indent}{value}"

        elif isinstance(value, dict):
            if not value:
                return f"{indent}*(empty)*"

            lines = []
            for key, val in value.items():
                # Format key
                lines.append(f"{indent}**{key}**:")
                # Format value (increase indent)
                formatted_val = self._format_value(val, level + 1)
                lines.append(formatted_val)
            return "\n".join(lines)

        elif isinstance(value, (list, tuple)):
            if not value:
                return f"{indent}*(empty list)*"

            lines = []
            for item in value:
                # Use markdown list format
                item_formatted = self._format_value(item, level + 1)
                # If item is multi-line, handle it specially
                item_lines = item_formatted.split("\n")
                if len(item_lines) == 1:
                    lines.append(f"{indent}- {item_lines[0].strip()}")
                else:
                    lines.append(f"{indent}- {item_lines[0].strip()}")
                    lines.extend(item_lines[1:])
            return "\n".join(lines)

        else:
            # Fallback for unknown types
            return f"{indent}{str(value)}"
