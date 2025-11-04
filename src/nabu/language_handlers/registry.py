"""Language handler registry for managing language-specific handlers"""

from typing import Dict, Optional, List
from pathlib import Path

from .base import LanguageHandler


class LanguageHandlerRegistry:
    """
    Central registry for language handlers.
    
    Manages registration and lookup of language handlers by:
    - Language name (e.g., 'python', 'cpp')
    - File extension (e.g., '.py', '.cpp')
    """

    def __init__(self):
        self._handlers: Dict[str, LanguageHandler] = {}
        self._extension_map: Dict[str, str] = {}  # .py -> python

    def register(self, handler: LanguageHandler):
        """
        Register a language handler.
        
        Args:
            handler: LanguageHandler instance to register
        """
        self._handlers[handler.language] = handler
        
        # Register all file extensions for this handler
        for ext in handler.get_file_extensions():
            self._extension_map[ext] = handler.language

    def get_handler(self, language: str) -> Optional[LanguageHandler]:
        """
        Get handler by language name.
        
        Args:
            language: Language name (e.g., 'python', 'cpp', 'java', 'perl')
            
        Returns:
            LanguageHandler instance or None if not found
        """
        return self._handlers.get(language)

    def get_handler_for_file(self, file_path: str) -> Optional[LanguageHandler]:
        """
        Get handler by file extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            LanguageHandler instance or None if extension not supported
        """
        ext = Path(file_path).suffix.lower()
        language = self._extension_map.get(ext)
        return self._handlers.get(language) if language else None

    def get_all_extensions(self) -> List[str]:
        """
        Get all supported file extensions.
        
        Returns:
            List of file extensions (e.g., ['.py', '.cpp', '.java', ...])
        """
        return list(self._extension_map.keys())

    def get_supported_languages(self) -> List[str]:
        """
        Get all supported languages.
        
        Returns:
            List of language names (e.g., ['python', 'cpp', 'java', ...])
        """
        return list(self._handlers.keys())

    def detect_language(self, file_path: str) -> Optional[str]:
        """
        Detect language from file extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            Language name or None if extension not supported
        """
        ext = Path(file_path).suffix.lower()
        return self._extension_map.get(ext)


# Global registry instance
language_registry = LanguageHandlerRegistry()
