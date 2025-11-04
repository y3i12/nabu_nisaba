"""Base class for transformer-based embedding generators."""

import logging
import torch
from transformers import AutoTokenizer, AutoModel
from typing import Optional, List
from nabu.embeddings.base import EmbeddingGenerator
from nabu.core.skeleton_builder import SkeletonFormatter

logger = logging.getLogger(__name__)


class BaseTransformerEmbeddingGenerator(EmbeddingGenerator):
    """
    Base class for transformer-based code embedding generators.

    Consolidates common initialization, tokenization, and generation logic
    shared across CodeBERT, UniXcoder, and similar models.

    Subclasses only need to specify:
    - model_name (via constructor parameter)
    - model_type property
    - embedding_dim property
    - max_tokens property
    - generate_embedding_from_ast_frame (model-specific strategy)
    - generate_embeddings_batch (model-specific optimizations)
    """

    def __init__(self, model_name: str, embedding_dim: int, max_tokens: int = 512):
        """
        Initialize transformer model and tokenizer.

        Args:
            model_name: HuggingFace model identifier
            embedding_dim: Dimension of generated embeddings
            max_tokens: Maximum token length for model
        """
        from nabu.embeddings.cache_config import get_model_cache_dir

        cache_dir = get_model_cache_dir()

        logger.info(f"Loading model: {model_name}")
        if cache_dir:
            logger.info(f"Using cache directory: {cache_dir}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        self.model = AutoModel.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        self.model.eval()  # Inference mode

        # Use GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        # CUDA streams for pipeline parallelism
        self.cuda_streams = []
        self.num_streams = 4  # Pipeline depth (optimal for 8-16GB VRAM)
        if self.device.type == 'cuda':
            try:
                self.cuda_streams = [torch.cuda.Stream() for _ in range(self.num_streams)]
                logger.info(f"Created {self.num_streams} CUDA streams for pipeline parallelism")
            except Exception as e:
                logger.warning(f"Failed to create CUDA streams: {e}. Falling back to default stream.")
                self.cuda_streams = []

        # Initialize skeleton formatter for consistent skeleton generation
        self.skeleton_formatter = SkeletonFormatter()

        # Store config
        self._embedding_dim = embedding_dim
        self._max_tokens = max_tokens

        logger.info(f"{model_name} loaded on device: {self.device}")

    @property
    def embedding_dim(self) -> int:
        """Return embedding dimensionality."""
        return self._embedding_dim

    @property
    def max_tokens(self) -> int:
        """Return maximum token length."""
        return self._max_tokens

    def _truncate_to_token_limit(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within token limit using tokenizer.

        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens allowed

        Returns:
            Truncated text that fits within token limit
        """
        if not text:
            return ""

        # Simple heuristic: ~4 chars per token for code
        estimated_tokens = len(text) // 4

        # Always use truncation for safety (prevents warnings)
        tokens = self.tokenizer.encode(
            text,
            add_special_tokens=False,
            truncation=True,
            max_length=self.max_tokens  # Use model's actual limit
        )

        if len(tokens) <= max_tokens:
            return text

        # Truncate tokens and decode back
        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens, skip_special_tokens=True)

    def generate_embedding_from_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using transformer model.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None on failure
        """
        try:
            # Tokenize with truncation
            tokens = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_tokens,
                padding=True
            )
            tokens = {k: v.to(self.device) for k, v in tokens.items()}

            # Generate embedding
            with torch.no_grad():
                outputs = self.model(**tokens)
                # Use [CLS] token embedding (standard for CodeBERT/RoBERTa models)
                embedding = outputs.last_hidden_state[:, 0, :].squeeze()

            # Convert to list and return
            return embedding.cpu().numpy().tolist()

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
