"""Regex utility functions for search optimization."""

import re
from typing import List


def extract_keywords_from_regex(pattern: str) -> str:
    """
    Extract searchable keywords from regex pattern for FTS pre-filtering.

    This enables intelligent content search by using FTS index to narrow
    candidates before applying expensive regex on content.

    Strategy:
    - Split pattern on regex metacharacters
    - Keep alphanumeric tokens with 3+ characters
    - Join with spaces for FTS query

    Examples:
        "class (SearchTool|QueryTool)" → "class SearchTool QueryTool"
        "import.*from.*tools" → "import from tools"
        "execute\\(\\)" → "execute"
        ".*Tool$" → "Tool"

    Args:
        pattern: Regex pattern string

    Returns:
        Space-separated keywords for FTS, or empty string if none found
    """
    # Split on regex metacharacters: . * + ? | ( ) [ ] { } ^ $ \
    tokens = re.split(r'[.*+?|(){}\[\]^$\\]+', pattern)

    # Keep tokens with 3+ alphanumeric chars (filter noise)
    keywords = [
        token.strip()
        for token in tokens
        if token.strip() and len(token.strip()) >= 3
    ]

    # Further filter: must contain at least one letter (avoid pure numbers)
    keywords = [kw for kw in keywords if any(c.isalpha() for c in kw)]

    return " ".join(keywords) if keywords else ""


def to_snake_case(name: str) -> str:
    """
    Convert PascalCase to snake_case.

    Examples:
        "SearchTool" → "search_tool"
        "MyHTTPServer" → "my_http_server"
        "Tool" → "tool"
    """
    # Insert underscore before uppercase letters (except first)
    result = re.sub(r'(?<!^)(?=[A-Z])', '_', name)
    return result.lower()


def to_pascal_case(name: str) -> str:
    """
    Convert snake_case to PascalCase.

    Examples:
        "search_tool" → "SearchTool"
        "my_http_server" → "MyHttpServer"
        "tool" → "Tool"
    """
    parts = name.replace('-', '_').split('_')
    return ''.join(word.capitalize() for word in parts if word)


def generate_fts_query_variants(target: str) -> str:
    """
    Generate FTS query with naming convention variants.

    FTS already handles:
    - Case insensitivity (porter stemmer)
    - Stemming (plurals, tense)
    - Tokenization (underscores split words)

    We only need to generate:
    - PascalCase ↔ snake_case conversions
    - Path separator normalizations

    Args:
        target: Original target name

    Returns:
        FTS query string with OR variants

    Examples:
        "SearchTool" → "SearchTool OR search_tool"
        "search_tool" → "search_tool OR SearchTool"
        "utils/MyClass" → "utils/MyClass OR utils.MyClass"
    """
    variants = [target]

    # Convention conversions (PascalCase ↔ snake_case)
    if '_' in target:
        # snake_case → PascalCase
        variants.append(to_pascal_case(target))
    elif target and any(c.isupper() for c in target[1:]):
        # Has uppercase (likely PascalCase) → snake_case
        variants.append(to_snake_case(target))

    # Path separator normalization
    if '/' in target:
        variants.append(target.replace('/', '.'))

    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            unique_variants.append(v)

    return ' OR '.join(unique_variants)
