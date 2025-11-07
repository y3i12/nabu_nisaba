"""
Base class for tool-specific markdown formatters.

Provides abstract interface for tool formatters.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseToolMarkdownFormatter(ABC):
    """
    Abstract base class for tool-specific markdown formatters.

    Similar to BaseSkeletonFormatter pattern but for tool output formatting.
    Each tool can implement its own compact, LLM-optimized markdown format.
    """

    @abstractmethod
    def format(self, data: Dict[str, Any]) -> str:
        """
        Format tool response data as compact markdown.

        Args:
            data: Tool response data dictionary

        Returns:
            Compact markdown-formatted string
        """
        pass
