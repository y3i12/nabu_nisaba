"""
Output formatter registry.

Provides centralized management of available formatters and format resolution.
"""

from typing import Dict
from .base import BaseOutputFormatter, OutputFormat
from .json import JsonOutputFormatter
from .markdown import MarkdownOutputFormatter


class OutputFormatterRegistry:
    """
    Registry for output formatters.

    Provides centralized management of available formatters and
    format resolution.
    """

    def __init__(self):
        """Initialize registry with default formatters."""
        self._formatters: Dict[str, BaseOutputFormatter] = {
            OutputFormat.JSON.value: JsonOutputFormatter(),
            OutputFormat.MARKDOWN.value: MarkdownOutputFormatter(),
        }
        self._default_format = OutputFormat.MARKDOWN.value

    def register(self, format_name: str, formatter: BaseOutputFormatter):
        """
        Register a new formatter.

        Args:
            format_name: Format identifier (e.g., "json", "markdown")
            formatter: Formatter instance
        """
        self._formatters[format_name] = formatter

    def get_formatter(self, format_name: str) -> BaseOutputFormatter:
        """
        Get formatter for specified format.

        Args:
            format_name: Format identifier

        Returns:
            Formatter instance

        Raises:
            ValueError: If format not supported
        """
        if format_name not in self._formatters:
            raise ValueError(
                f"Unsupported output format: {format_name}. "
                f"Supported formats: {', '.join(self._formatters.keys())}"
            )
        return self._formatters[format_name]

    def get_default_formatter(self) -> BaseOutputFormatter:
        """Get default formatter (JSON)."""
        return self._formatters[self._default_format]

    def list_formats(self) -> list[str]:
        """List available format names."""
        return list(self._formatters.keys())


# Global registry instance
_formatter_registry = OutputFormatterRegistry()


def get_formatter_registry() -> OutputFormatterRegistry:
    """Get global formatter registry."""
    return _formatter_registry
