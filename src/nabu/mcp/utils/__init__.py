"""Nabu MCP utilities package."""

from .snippet_extractor import extract_snippets

# Backward compatibility: Re-export from new formatters module
from nabu.mcp.formatters import (
    OutputFormat,
    BaseOutputFormatter,
    JsonOutputFormatter,
    OutputFormatterRegistry,
    get_formatter_registry
)

__all__ = [
    "extract_snippets",
    "OutputFormat",
    "BaseOutputFormatter",
    "JsonOutputFormatter",
    "OutputFormatterRegistry",
    "get_formatter_registry",
]
