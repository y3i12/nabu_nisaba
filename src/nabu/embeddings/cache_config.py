"""Shared model cache configuration for HuggingFace transformers."""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_model_cache_dir() -> Optional[str]:
    """
    Get model cache directory for HuggingFace transformers.

    Priority:
    1. NABU_MODEL_CACHE env variable
    2. HF_HOME env variable
    3. TRANSFORMERS_CACHE env variable
    4. None (use HuggingFace default: ~/.cache/huggingface)

    Environment Variables:
        NABU_MODEL_CACHE: Nabu-specific cache directory (highest priority)
        HF_HOME: HuggingFace home directory
        TRANSFORMERS_CACHE: Transformers-specific cache directory

    Returns:
        Cache directory path or None for default behavior

    Example:
        >>> os.environ["NABU_MODEL_CACHE"] = "/data/models"
        >>> get_model_cache_dir()
        '/data/models'
    """
    # Check nabu-specific cache first
    if cache_dir := os.getenv("NABU_MODEL_CACHE"):
        cache_path = Path(cache_dir)
        try:
            cache_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using NABU_MODEL_CACHE: {cache_path}")
            return str(cache_path)
        except Exception as e:
            logger.warning(f"Failed to create cache directory {cache_path}: {e}")
            # Fall through to other options

    # Fallback to HuggingFace standard env vars
    if hf_home := os.getenv("HF_HOME"):
        logger.info(f"Using HF_HOME: {hf_home}")
        return hf_home

    if transformers_cache := os.getenv("TRANSFORMERS_CACHE"):
        logger.info(f"Using TRANSFORMERS_CACHE: {transformers_cache}")
        return transformers_cache

    default_path = Path('.nabu/hf_cache').absolute()
    default_path.mkdir(exist_ok=True)
    return str(default_path)
    # Use HuggingFace default (~/.cache/huggingface)
    #logger.debug("Using HuggingFace default cache directory")
    #return None
