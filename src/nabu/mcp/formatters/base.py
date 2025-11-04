"""
Base output formatter infrastructure.

Provides abstract base class and format enumeration for output formatters.
"""

from abc import ABC, abstractmethod
from typing import Any
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats."""
    JSON = "json"
    MARKDOWN = "markdown"


class BaseOutputFormatter(ABC):
    """
    Abstract base class for output formatters.

    Formatters transform tool response data from internal representation
    to the desired output format.
    """

    @abstractmethod
    def format(self, data: Any, tool_name: str = "") -> Any:
        """
        Format tool response data.

        Args:
            data: Tool response data (dict, list, etc.)
            tool_name: Name of the tool generating the response (for context)

        Returns:
            Formatted data suitable for the output format
        """
        pass
