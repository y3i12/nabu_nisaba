"""
Language Handler Infrastructure

This module provides a pluggable system for language-specific operations in nabu.
Each language handler encapsulates all language-specific behavior including:
- File extension mapping
- Tree-sitter node type → semantic frame type mapping
- Name extraction (classes, functions, packages)
- Qualified name generation
- Import/inheritance resolution

Additionally, skeleton formatters provide language-specific skeleton generation.

Usage:
    from nabu.language_handlers import language_registry

    handler = language_registry.get_handler('python')
    if handler:
        frame_mappings = handler.get_frame_mappings()
        name = handler.extract_class_name(content, raw_node)

    # For skeleton formatting:
    from nabu.language_handlers.formatters import formatter_registry

    formatter = formatter_registry.get_formatter('python')
    if formatter:
        skeleton = formatter.format_class_skeleton(...)
"""

from .base import LanguageHandler, ImportStatement
from .registry import LanguageHandlerRegistry, language_registry
from .python import PythonHandler
from .cpp import CppHandler
from .java import JavaHandler
from .perl import PerlHandler


def setup_handlers():
    """Initialize and register all language handlers."""
    language_registry.register(PythonHandler())
    language_registry.register(CppHandler())
    language_registry.register(JavaHandler())
    language_registry.register(PerlHandler())


# Auto-setup on import
setup_handlers()


__all__ = [
    'LanguageHandler',
    'ImportStatement',
    'LanguageHandlerRegistry',
    'language_registry',
    'PythonHandler',
    'CppHandler',
    'JavaHandler',
    'PerlHandler',
    'setup_handlers',
]
