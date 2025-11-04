"""
C++ Parsing Utilities

Shared utilities for parsing C++ constructs, extracted to prevent
duplication between SymbolResolver and RelationshipRepairer.
"""

import re
from typing import Optional


def extract_cpp_class_from_signature(method_content: str) -> Optional[str]:
    """
    Extract class name from C++ method signature.

    Patterns:
        void Logger::log(...) → "Logger"
        Logger::Logger(...) → "Logger"  (constructor)
        Logger::~Logger() → "Logger"  (destructor)
        std::string Helper::formatOutput(...) → "Helper"

    Args:
        method_content: C++ method definition text

    Returns:
        Class name or None if not a class method
    """
    # Take first line (signature line)
    first_line = method_content.strip().split('\n')[0]

    # Pattern: ClassName::methodName
    # Match scope resolution operator with class name before it
    pattern = r'\b([A-Z][a-zA-Z0-9_]*)::'

    match = re.search(pattern, first_line)
    if match:
        class_name = match.group(1)
        # Validate it looks like a class name (starts with uppercase)
        if class_name[0].isupper():
            return class_name

    return None
