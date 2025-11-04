"""
Embedding generation for vector search.

Provides multi-model embedding support:
- UniXcoder: Code→code similarity (contrastive learning)
- CodeBERT: Structural understanding (data flow graphs)

Fusion:
- Pythagorean³ consensus (P3): Proven UX×CB fusion approach
"""

from nabu.embeddings.base import (
    EmbeddingGenerator,
    EmbeddingModel,
    compute_non_linear_consensus
)

# Optional dependencies for embeddings (torch, transformers)
# Only import if dependencies are available
try:
    from nabu.embeddings.unixcoder_generator import UniXcoderGenerator
    from nabu.embeddings.codebert_generator import CodeBERTGenerator
    from nabu.embeddings.fusion_strategies import NonLinearConsensusFusion
    from nabu.embeddings.generator_cache import (
        get_unixcoder_generator,
        get_codebert_generator,
        clear_generator_cache
    )
    _EMBEDDINGS_AVAILABLE = True
except ImportError:
    # Embeddings require torch/transformers, which are optional
    # Provide stub implementations that raise helpful errors
    UniXcoderGenerator = None  # type: ignore
    CodeBERTGenerator = None  # type: ignore
    NonLinearConsensusFusion = None  # type: ignore
    get_unixcoder_generator = None  # type: ignore
    get_codebert_generator = None  # type: ignore
    clear_generator_cache = lambda: None  # type: ignore
    _EMBEDDINGS_AVAILABLE = False

__all__ = [
    # Core generators
    'EmbeddingGenerator',
    'EmbeddingModel',
    'UniXcoderGenerator',
    'CodeBERTGenerator',
    # Fusion
    'compute_non_linear_consensus',
    'NonLinearConsensusFusion',
    # Cached getters (recommended for MCP tools)
    'get_unixcoder_generator',
    'get_codebert_generator',
    'clear_generator_cache',
]
