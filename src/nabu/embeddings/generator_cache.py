"""
Module-level singleton cache for embedding generators.

Ensures models are loaded once per MCP server process lifetime,
dramatically reducing overhead for semantic operations.
"""

import logging
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from nabu.embeddings.base import EmbeddingGenerator

logger = logging.getLogger(__name__)

# Module-level cache: survives for process lifetime
_generator_cache: Dict[str, 'EmbeddingGenerator'] = {}


def get_unixcoder_generator() -> 'EmbeddingGenerator':
    """
    Get cached UniXcoder generator (lazy-loaded on first call).

    Returns:
        Singleton UniXcoderGenerator instance
    """
    if 'unixcoder' not in _generator_cache:
        from nabu.embeddings.unixcoder_generator import UniXcoderGenerator
        logger.info("Initializing UniXcoder generator (first use)")
        _generator_cache['unixcoder'] = UniXcoderGenerator()
    return _generator_cache['unixcoder']


def get_codebert_generator() -> 'EmbeddingGenerator':
    """
    Get cached CodeBERT generator (lazy-loaded on first call).

    Returns:
        Singleton CodeBERTGenerator instance
    """
    if 'codebert' not in _generator_cache:
        from nabu.embeddings.codebert_generator import CodeBERTGenerator
        logger.info("Initializing CodeBERT generator (first use)")
        _generator_cache['codebert'] = CodeBERTGenerator()
    return _generator_cache['codebert']


def clear_generator_cache():
    """Clear all cached generators (useful for testing or memory cleanup)."""
    global _generator_cache
    _generator_cache.clear()
    logger.info("Cleared embedding generator cache")
