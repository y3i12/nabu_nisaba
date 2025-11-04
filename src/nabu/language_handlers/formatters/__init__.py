"""
Skeleton Formatter Infrastructure

This module provides language-specific skeleton formatters that convert
database frames and metadata into formatted skeleton code.

Each formatter handles:
- Class skeleton assembly (declaration, fields, methods)
- Method signature reconstruction
- Control flow hint formatting
- Docstring extraction
- Language-specific syntax rules

Usage:
    from nabu.language_handlers.formatters import formatter_registry

    formatter = formatter_registry.get_formatter('python')
    if formatter:
        skeleton = formatter.format_class_skeleton(class_data, methods, ...)
"""

from .base import BaseSkeletonFormatter
from .registry import FormatterRegistry, formatter_registry
from .python import PythonSkeletonFormatter
from .java import JavaSkeletonFormatter
from .cpp import CppSkeletonFormatter
from .perl import PerlSkeletonFormatter


def setup_formatters():
    """Initialize and register all skeleton formatters."""
    from nabu.language_handlers import language_registry

    # Register formatters with their corresponding language handlers
    python_handler = language_registry.get_handler('python')
    if python_handler:
        formatter_registry.register('python', PythonSkeletonFormatter(python_handler))

    java_handler = language_registry.get_handler('java')
    if java_handler:
        formatter_registry.register('java', JavaSkeletonFormatter(java_handler))

    cpp_handler = language_registry.get_handler('cpp')
    if cpp_handler:
        formatter_registry.register('cpp', CppSkeletonFormatter(cpp_handler))

    perl_handler = language_registry.get_handler('perl')
    if perl_handler:
        formatter_registry.register('perl', PerlSkeletonFormatter(perl_handler))


# Auto-setup on import
setup_formatters()


__all__ = [
    'BaseSkeletonFormatter',
    'FormatterRegistry',
    'formatter_registry',
    'PythonSkeletonFormatter',
    'JavaSkeletonFormatter',
    'CppSkeletonFormatter',
    'PerlSkeletonFormatter',
    'setup_formatters',
]
