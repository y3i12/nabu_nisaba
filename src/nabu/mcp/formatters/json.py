"""
JSON output formatter.

Provides pass-through formatting for JSON output (maintains backward compatibility).
"""

from typing import Any
from .base import BaseOutputFormatter


class JsonOutputFormatter(BaseOutputFormatter):
    """
    JSON output formatter (pass-through).

    Keeps data in its original dict/list structure for JSON serialization.
    This is the default formatter and maintains backward compatibility.
    """

    def format(self, data: Any, tool_name: str = "") -> Any:
        """
        Pass-through formatter for JSON output.

        Args:
            data: Tool response data
            tool_name: Tool name (unused for JSON format)

        Returns:
            Unmodified data
        """
        # JSON is the native format - no transformation needed
        return data
