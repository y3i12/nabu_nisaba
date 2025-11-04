"""
GraphCodeBERT Embedding Generator

Generates vector embeddings for code frames using Microsoft's GraphCodeBERT model.
GraphCodeBERT adds data flow awareness to CodeBERT for better semantic understanding.
"""

import logging
from typing import Optional, List, TYPE_CHECKING
import torch
import math

if TYPE_CHECKING:
    import torch.cuda

from nabu.embeddings.base import EmbeddingModel
from nabu.embeddings.base_transformer_generator import BaseTransformerEmbeddingGenerator

logger = logging.getLogger(__name__)


class CodeBERTGenerator(BaseTransformerEmbeddingGenerator):
    """
    GraphCodeBERT embedding generator.
    
    GraphCodeBERT extends CodeBERT with data flow awareness for improved
    semantic understanding of code structure and relationships.
    Used for: Non-linear consensus fusion (not persisted independently)

    Strengths:
    - Structure and data flow aware
    - Better semantic understanding than vanilla CodeBERT
    - Designed for code-related tasks (search, clone detection, etc.)
    
    Best for:
    - Semantic code search with natural language queries
    - Understanding code semantics beyond token sequences
    """
    
    def __init__(self):
        """Initialize GraphCodeBERT model and tokenizer."""
        super().__init__(
            model_name="microsoft/graphcodebert-base",
            embedding_dim=768,
            max_tokens=512
        )
    
    @property
    def model_type(self) -> EmbeddingModel:
        """Model type identifier for database columns."""
        return EmbeddingModel.CODEBERT

    def generate_embedding_from_ast_frame(self, frame: 'AstFrameBase') -> Optional[List[float]]:
        """
        Generate embedding from AstFrame with adaptive strategy.
        
        Same strategy as UniXcoder for now.
        Future: Could experiment with different strategies optimized for semantic matching.
        
        Args:
            frame: AstFrame with children loaded (includes control flow children)
        
        Returns:
            768-dimensional embedding as list of floats, or None if generation fails
        """
        from nabu.core.frame_types import FrameNodeType
        from nabu.core.skeleton_builder import SkeletonBuilder, SkeletonOptions
        
        # Only embed CALLABLE frames
        if frame.type != FrameNodeType.CALLABLE:
            return None
        
        try:
            parts = []
            
            # 1. Qualified name (context)
            if frame.qualified_name:
                parts.append(frame.qualified_name)
            
            # 2. Adaptive content strategy based on function size
            full_content = frame.content or ''
            
            if full_content:
                # Safely measure token count with defensive truncation
                # Use simple char estimate: ~4 chars per token
                char_limit = self.max_tokens * 4  # 512 * 4 = 2048 chars
                safe_sample = full_content[:char_limit] if len(full_content) > char_limit else full_content
                
                try:
                    full_tokens = len(self.tokenizer.encode(
                        safe_sample, 
                        add_special_tokens=False, 
                        truncation=True, 
                        max_length=self.max_tokens
                    ))
                    # If we truncated the sample, assume it's large
                    if len(full_content) > char_limit:
                        full_tokens = self.max_tokens  # Conservative estimate
                except Exception as e:
                    logger.warning(f"Failed to measure tokens for {frame.qualified_name}: {e}, assuming large")
                    full_tokens = self.max_tokens  # Assume large on error
                
                if full_tokens <= int(self.max_tokens * 0.9):
                    # SMALL FUNCTION: Use full implementation
                    parts.append(full_content)
                    logger.debug(f"Embedding FULL code for {frame.qualified_name} ({full_tokens} tokens)")
                else:
                    # LARGE FUNCTION: Use skeleton with control flow fingerprints
                    builder = SkeletonBuilder(db_manager=None)
                    options = SkeletonOptions(
                        detail_level="structure",  # Full control flow tree
                        include_docstrings=True,   # Critical for semantic signal
                        structure_detail_depth=2   # Nested control flow
                    )
                    
                    skeleton = builder.build_skeleton_from_ast(frame, options, max_recursion_depth=0)
                    if skeleton:
                        parts.append(skeleton)
                        logger.debug(f"Embedding SKELETON for {frame.qualified_name} (full content: {full_tokens} tokens)")
                    else:
                        # Fallback: truncate full content
                        truncated = self._truncate_to_token_limit(full_content, int(self.max_tokens * 0.9))
                        parts.append(truncated)
                        logger.warning(f"Skeleton generation failed for {frame.qualified_name}, using truncated content")
            
            # 3. Join and apply safety truncation (CodeBERT has 512 token limit vs UniXcoder's 1024)
            text = "\n\n".join(parts)
            text = self._truncate_to_token_limit(text, max_tokens=int(self.max_tokens * 0.9))
            
            if not text:
                return None
            
            # 4. Generate embedding
            return self.generate_embedding_from_text(text)
        
        except Exception as e:
            logger.error(f"Failed to generate embedding from AST frame {frame.qualified_name}: {e}")
            return None

    async def generate_embeddings_batch(self, frames: List['AstFrameBase'], batch_size: int = 32) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple frames in parallel batches.
        
        Uses CUDA streams for pipeline parallelism when available.
        
        Args:
            frames: List of AstFrame objects to embed
            batch_size: Number of frames per batch (default 32)
        
        Returns:
            List of embeddings (same order as input), None for failed frames
        """
        from nabu.core.frame_types import FrameNodeType
        from nabu.core.skeleton_builder import SkeletonBuilder, SkeletonOptions
        
        # Filter to CALLABLE frames
        callable_frames = [f for f in frames if f.type == FrameNodeType.CALLABLE]

        if not callable_frames:
            return [None] * len(frames)

        logger.info(f"[CodeBERT] Generating embeddings for {len(callable_frames)} frames (batch_size={batch_size})")

        # Build adaptive text for each frame
        texts = []
        builder = SkeletonBuilder(db_manager=None)
        
        for frame in callable_frames:
            parts = []
            
            if frame.qualified_name:
                parts.append(frame.qualified_name)
            
            full_content = frame.content or ''
            if full_content:
                char_limit = self.max_tokens * 4
                safe_sample = full_content[:char_limit] if len(full_content) > char_limit else full_content
                
                try:
                    full_tokens = len(self.tokenizer.encode(
                        safe_sample, 
                        add_special_tokens=False, 
                        truncation=True, 
                        max_length=self.max_tokens
                    ))
                    if len(full_content) > char_limit:
                        full_tokens = self.max_tokens
                except Exception:
                    full_tokens = self.max_tokens
                
                if full_tokens <= int(self.max_tokens * 0.9):
                    parts.append(full_content)
                else:
                    options = SkeletonOptions(
                        detail_level="structure",
                        include_docstrings=True,
                        structure_detail_depth=2
                    )
                    skeleton = builder.build_skeleton_from_ast(frame, options, max_recursion_depth=0)
                    if skeleton:
                        parts.append(skeleton)
                    else:
                        truncated = self._truncate_to_token_limit(full_content, int(self.max_tokens * 0.9))
                        parts.append(truncated)
            
            text = "\n\n".join(parts)
            text = self._truncate_to_token_limit(text, max_tokens=int(self.max_tokens * 0.9))
            texts.append(text if text else "")
        
        # Batch generation with CUDA streams
        embeddings = []
        num_batches = math.ceil(len(texts) / batch_size)

        logger.info(f"[CodeBERT] Processing {num_batches} batches")

        for i in range(num_batches):
            batch_texts = texts[i * batch_size:(i + 1) * batch_size]
            
            try:
                # Tokenize batch
                tokens = self.tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    truncation=True,
                    max_length=self.max_tokens,
                    padding=True
                )
                tokens = {k: v.to(self.device) for k, v in tokens.items()}
                
                # Use CUDA stream if available
                stream = self.cuda_streams[i % self.num_streams] if self.cuda_streams else None
                batch_embeddings = self._generate_batch_embeddings_with_stream(tokens, stream)

                embeddings.extend(batch_embeddings)

                # Log progress
                progress_pct = ((i + 1) * 100) // num_batches
                logger.info(f"[CodeBERT] Batch {i + 1}/{num_batches} complete ({progress_pct}%)")

            except Exception as e:
                logger.error(f"[CodeBERT] Batch {i + 1} failed: {e}")
                embeddings.extend([None] * len(batch_texts))
        
        # Map back to original frame order
        result = []
        emb_idx = 0
        for frame in frames:
            if frame.type == FrameNodeType.CALLABLE:
                result.append(embeddings[emb_idx] if emb_idx < len(embeddings) else None)
                emb_idx += 1
            else:
                result.append(None)

        successful = sum(1 for e in result if e is not None)
        logger.info(f"[CodeBERT] Completed: {successful}/{len(frames)} embeddings generated")

        return result

    def _generate_batch_embeddings_with_stream(self, tokens: dict, stream: Optional['torch.cuda.Stream'] = None) -> List[List[float]]:
        """
        Generate embeddings for a tokenized batch, optionally using CUDA stream.
        
        Args:
            tokens: Tokenized batch (dict with input_ids, attention_mask, etc.)
            stream: Optional CUDA stream for async execution
        
        Returns:
            List of embedding vectors
        """
        try:
            if stream and self.device.type == 'cuda':
                with torch.cuda.stream(stream):
                    with torch.no_grad():
                        outputs = self.model(**tokens)
                        embeddings = outputs.last_hidden_state[:, 0, :].cpu()
                torch.cuda.current_stream().wait_stream(stream)
            else:
                with torch.no_grad():
                    outputs = self.model(**tokens)
                    embeddings = outputs.last_hidden_state[:, 0, :].cpu()
            
            return [emb.numpy().tolist() for emb in embeddings]
        
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            return [None] * len(tokens['input_ids'])
