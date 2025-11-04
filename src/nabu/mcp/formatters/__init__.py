"""
Nabu MCP Output Formatters

Provides pluggable formatting system for tool responses.
Supports JSON and Markdown output with tool-specific optimizations.

Usage:
    from nabu.mcp.formatters import get_formatter_registry

    registry = get_formatter_registry()
    formatter = registry.get_formatter('markdown')
    output = formatter.format(data, tool_name='search')
"""

from .base import BaseOutputFormatter, OutputFormat
from .json import JsonOutputFormatter
from .markdown import MarkdownOutputFormatter
from .registry import OutputFormatterRegistry, get_formatter_registry
from .tool_base import BaseToolMarkdownFormatter
from .tool_registry import ToolMarkdownFormatterRegistry

# Auto-setup tool formatters on import (like language_handlers)
from .tool_registry import _setup_tool_formatters
_setup_tool_formatters()

__all__ = [
    'BaseOutputFormatter',
    'OutputFormat',
    'JsonOutputFormatter',
    'MarkdownOutputFormatter',
    'OutputFormatterRegistry',
    'get_formatter_registry',
    'BaseToolMarkdownFormatter',
    'ToolMarkdownFormatterRegistry',
]
