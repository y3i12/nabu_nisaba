"""
Fusion strategies for combining multiple embeddings.

Simplified to proven P3 consensus approach.
"""

from typing import List, Optional, Dict
from abc import ABC, abstractmethod


class FusionStrategy(ABC):
    """Abstract fusion strategy for combining embeddings."""

    @abstractmethod
    def fuse(
        self,
        embeddings: Dict[str, Optional[List[float]]]
    ) -> Optional[List[float]]:
        """
        Fuse multiple embeddings into one.

        Args:
            embeddings: Dict mapping model_name -> embedding vector

        Returns:
            Fused embedding or None if fusion fails
        """
        pass

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Strategy identifier for logging/debugging."""
        pass


class NonLinearConsensusFusion(FusionStrategy):
    """
    Pythagorean³ (P3) fusion: cbrt(a³ + b³).

    Experimentally validated: 0% → 100% accuracy on challenging semantic search.
    See: .dev_docs/sessions/20251020_model_embedding_fusion/embedding_fusion_experiments.md

    Properties:
    - Sign-preserving (unlike Pythagorean²)
    - Disagreement cancellation (conflicting signals → 0)
    - Consensus amplification (agreement → superlinear boost)
    - Weak signal suppression (noise filtering)

    Proven approach: UniXcoder × CodeBERT
    """

    def __init__(self, model_a_key: str = "unixcoder", model_b_key: str = "codebert"):
        """
        Initialize P3 fusion strategy.

        Args:
            model_a_key: Key for first model in embeddings dict (default: unixcoder)
            model_b_key: Key for second model in embeddings dict (default: codebert)
        """
        self.model_a_key = model_a_key
        self.model_b_key = model_b_key

    @property
    def strategy_name(self) -> str:
        return "non_linear_consensus"

    def fuse(
        self,
        embeddings: Dict[str, Optional[List[float]]]
    ) -> Optional[List[float]]:
        """
        Compute Pythagorean³ fusion of two embeddings.

        Args:
            embeddings: Must contain keys matching model_a_key and model_b_key

        Returns:
            Fused embedding (768D, L2-normalized) or None if either input is None
        """
        emb_a = embeddings.get(self.model_a_key)
        emb_b = embeddings.get(self.model_b_key)

        if emb_a is None or emb_b is None:
            return None

        # Use core P3 implementation
        from nabu.embeddings.base import compute_non_linear_consensus
        return compute_non_linear_consensus(emb_a, emb_b)
