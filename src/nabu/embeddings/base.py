"""Abstract base class for embedding generators."""

from abc import ABC, abstractmethod
from typing import List, Optional
from enum import Enum


class EmbeddingModel(Enum):
    """Available embedding models mapped to database columns."""
    UNIXCODER = "unixcoder"
    CODEBERT = "codebert"
    NON_LINEAR_CONSENSUS = "non_linear_consensus"
    EARLY_FUSION = "early_fusion"


class SimilarityMetric(Enum):
    """Metrics for dimension similarity/synonym detection during early fusion."""
    PYTHAGOREAN3 = "p3"          # Element-wise P³ consensus (default)
    COSINE = "cosine"             # Cosine similarity
    PEARSON = "pearson"           # Pearson correlation (legacy)


# Metric-specific default thresholds (empirically calibrated)
DEFAULT_SIMILARITY_THRESHOLDS = {
    SimilarityMetric.PYTHAGOREAN3: 1,
    SimilarityMetric.COSINE: 1.0,
    SimilarityMetric.PEARSON: 0.75
}




def compute_non_linear_consensus(
    embedding_a: List[float],
    embedding_b: List[float]
) -> List[float]:
    """
    Compute Pythagorean³ fusion: cbrt(a³ + b³).

    Implementation follows embedding_fusion_theory.md Section 4 (Non-Linear Consensus).

    Strategy:
    1. Normalize both vectors to [-1, 1] per-dimension using 99th percentile scaling
    2. Cube both vectors (preserves sign), sum element-wise
    3. Cube root to get consensus
    4. L2 normalize for efficient cosine similarity search

    Properties:
    - Sign-preserving (unlike Pythagorean²)
    - Cancels when models disagree in direction
    - Emphasizes strong consensus (superlinear amplification)
    - De-emphasizes weak or conflicting signals (sublinear suppression)

    Args:
        embedding_a: First embedding vector (768D)
        embedding_b: Second embedding vector (768D)

    Returns:
        Fused embedding (768D, L2-normalized) representing non-linear consensus

    Note:
        Uses per-dimension normalization to [-1, 1] range before P3 computation,
        then L2 normalizes output for storage/search efficiency.
    """
    import numpy as np

    a = np.array(embedding_a)
    b = np.array(embedding_b)

    # Per-dimension normalization to [-1, 1] using 99th percentile method
    # This matches the theory in embedding_fusion_theory.md Section 1.3
    # and the validated implementation in scripts/generate_correlation_gifs.py
    combined = np.stack([a, b], axis=0)  # Shape: (2, 768)
    scales = np.percentile(np.abs(combined), 99, axis=0) * 1.2  # Shape: (768,)
    scales = np.maximum(scales, 1e-8)  # Prevent division by zero

    a_norm = np.clip(a / scales, -1, 1)
    b_norm = np.clip(b / scales, -1, 1)

    # Pythagorean³: cbrt(a³ + b³)
    # Use np.cbrt instead of np.power for better handling of negative values
    cubed_sum = a_norm**3 + b_norm**3
    result = np.cbrt(cubed_sum)

    # L2 normalize output for storage (improved index efficiency with cosine similarity)
    # This final normalization is appropriate since we use cosine similarity in vector indices
    result_norm = result / (np.linalg.norm(result) + 1e-8)
    return result_norm.tolist()


class EmbeddingGenerator(ABC):
    """
    Abstract base for code embedding generators.
    
    Each implementation generates embeddings for a specific model.
    All embeddings are stored in parallel in the database.
    """
    
    @property
    @abstractmethod
    def model_type(self) -> EmbeddingModel:
        """Which embedding model this generator produces."""
        pass
    
    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Embedding dimensionality (must match database schema)."""
        pass
    
    @property
    @abstractmethod
    def max_tokens(self) -> int:
        """Maximum token length for this model."""
        pass
    
    @abstractmethod
    def generate_embedding_from_ast_frame(
        self, 
        frame: 'AstFrameBase'
    ) -> Optional[List[float]]:
        """
        Generate embedding from AST frame with model-specific strategy.
        
        Args:
            frame: AstFrame with children loaded
        
        Returns:
            N-dimensional embedding or None if generation fails
        """
        pass
    
    @abstractmethod
    def generate_embedding_from_text(
        self, 
        text: str
    ) -> Optional[List[float]]:
        """
        Generate embedding from raw text (for queries).
        
        Args:
            text: Text to embed
        
        Returns:
            N-dimensional embedding or None if generation fails
        """
        pass

    async def generate_embeddings_batch(
        self, 
        frames: List['AstFrameBase'],
        batch_size: int = 32
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple frames using batched inference.
        
        Processes frames in batches to maximize GPU utilization.
        Default implementation (can be overridden for model-specific optimizations).
        
        Args:
            frames: List of frames to embed
            batch_size: Number of frames to process per batch (default: 32)
        
        Returns:
            List of embeddings (same order as input frames), None for failed frames
        """
        import asyncio
        
        results = []
        for frame in frames:
            # Run in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                self.generate_embedding_from_ast_frame, 
                frame
            )
            results.append(embedding)
        return results
    
    def get_db_column_name(self) -> str:
        """Get database column name for this model's embeddings."""
        return f"embedding_{self.model_type.value}"
    
    def get_index_name(self) -> str:
        """Get vector index name for this model."""
        return f"frame_embedding_{self.model_type.value}_idx"
