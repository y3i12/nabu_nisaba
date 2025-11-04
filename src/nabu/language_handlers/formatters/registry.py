"""Registry for skeleton formatters"""

from typing import Dict, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from nabu.language_handlers.formatters.base import BaseSkeletonFormatter


class FormatterRegistry:
    """
    Central registry for skeleton formatters.

    Maps language names to their skeleton formatter instances.
    """

    def __init__(self):
        self._formatters: Dict[str, 'BaseSkeletonFormatter'] = {}

    def register(self, language: str, formatter: 'BaseSkeletonFormatter'):
        """
        Register a skeleton formatter for a language.

        Args:
            language: Language name (e.g., 'python', 'java', 'cpp')
            formatter: Formatter instance for this language
        """
        self._formatters[language] = formatter

    def get_formatter(self, language: str) -> Optional['BaseSkeletonFormatter']:
        """
        Get formatter for a language.

        Args:
            language: Language name (e.g., 'python', 'java', 'cpp')

        Returns:
            BaseSkeletonFormatter instance or None if not registered
        """
        return self._formatters.get(language)

    def get_supported_languages(self) -> List[str]:
        """
        Get list of languages with registered formatters.

        Returns:
            List of language names
        """
        return list(self._formatters.keys())


# Global formatter registry instance
formatter_registry = FormatterRegistry()
