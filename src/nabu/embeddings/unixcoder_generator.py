"""
UniXcoder Embedding Generator

Generates vector embeddings for code frames using Microsoft's UniXcoder model.
Optimized for operational differentiation and code→code similarity.
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


class UniXcoderGenerator(BaseTransformerEmbeddingGenerator):
    """
    UniXcoder embedding generator.
    
    Optimized for operational differentiation and code→code similarity.
    Stores embeddings in: embedding_unixcoder column
    
    Strengths:
    - Excellent operational differentiation
    - Low false positive rate for code similarity
    - Code→code pattern matching
    
    Best for: clone detection, code→code search
    """
    
    def __init__(self):
        """Initialize UniXcoder model and tokenizer."""
        super().__init__(
            model_name="microsoft/unixcoder-base",
            embedding_dim=768,
            max_tokens=1024  # UniXcoder supports longer sequences than CodeBERT
        )
    
    @property
    def model_type(self) -> EmbeddingModel:
        return EmbeddingModel.UNIXCODER

    def generate_embedding_from_ast_frame(self, frame: 'AstFrameBase') -> Optional[List[float]]:
        """
        Generate embedding from AstFrame with adaptive strategy.
        
        Adaptive Approach:
        - Small functions (≤400 tokens): Embed FULL implementation for maximum fidelity
        - Large functions (>400 tokens): Use skeleton with control flow fingerprints
        
        This solves the "..." placeholder problem: UniXcoder was trained on real code,
        not abstracted skeletons. Small functions benefit from seeing actual implementation.
        
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
                char_limit = self.max_tokens * 4  # 1024 * 4 = 4096 chars
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
                    full_tokens = self.max_tokens  # Assume large on error  # Assume large on error
                
                if full_tokens <= int(self.max_tokens * 0.9):
                    # SMALL FUNCTION: Use full implementation
                    # UniXcoder can see actual operations (dict lookup, math, logic, etc.)
                    # This solves the 99.69% false positive problem for simple functions
                    parts.append(full_content)
                    logger.debug(f"Embedding FULL code for {frame.qualified_name} ({full_tokens} tokens)")
                else:
                    # LARGE FUNCTION: Use skeleton with control flow fingerprints
                    # This keeps token budget manageable while providing structural differentiation
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
            
            # 3. Join and apply safety truncation
            text = "\n\n".join(parts)
            text = self._truncate_to_token_limit(text, max_tokens=500)
            
            if not text:
                return None
            
            # 4. Generate embedding
            return self.generate_embedding_from_text(text)
        
        except Exception as e:
            logger.error(f"Failed to generate embedding from AST frame {frame.qualified_name}: {e}")
            return None

    async def generate_embeddings_batch(
        self,
        frames: List['AstFrameBase'],
        batch_size: int = 32
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple frames using GPU-optimized batched inference.
        
        Processes frames in batches to maximize GPU utilization (~10-15x speedup vs sequential).
        
        Args:
            frames: List of frames to embed (CALLABLE frames only)
            batch_size: Frames per batch (default: 32, optimal for 8GB VRAM)
        
        Returns:
            List of embeddings in same order as input frames
        """
        from nabu.core.frame_types import FrameNodeType
        from nabu.core.skeleton_builder import SkeletonBuilder, SkeletonOptions
        import asyncio
        
        logger.info(f"[UniXcoder] Generating embeddings for {len(frames)} frames (batch_size={batch_size})")
        
        # Prepare texts for all frames (adaptive strategy per frame)
        texts = []
        for frame in frames:
            if frame.type != FrameNodeType.CALLABLE:
                texts.append(None)
                continue
            
            # Use same adaptive logic as single-frame generation
            try:
                parts = []
                if frame.qualified_name:
                    parts.append(frame.qualified_name)
                
                full_content = frame.content or ''
                if full_content:
                    # Quick token estimate
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
                        # Use skeleton for large functions
                        builder = SkeletonBuilder(db_manager=None)
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
                text = self._truncate_to_token_limit(text, max_tokens=500)
                texts.append(text if text else None)
            except Exception as e:
                logger.error(f"Failed to prepare text for {frame.qualified_name}: {e}")
                texts.append(None)
        
        # Generate embeddings with stream-based pipeline parallelism
        results = [None] * len(frames)
        total_batches = (len(texts) + batch_size - 1) // batch_size

        # Determine pipeline depth (how many batches to process concurrently)
        pipeline_depth = len(self.cuda_streams) if self.cuda_streams else 1

        logger.info(f"[UniXcoder] Processing {total_batches} batches with pipeline_depth={pipeline_depth}")

        # Process batches in groups (pipeline windows)
        for window_start in range(0, total_batches, pipeline_depth):
            # Prepare batch tasks for this pipeline window
            batch_tasks = []
            batch_metadata = []  # Track (batch_idx, batch_num, valid_indices)

            for i in range(pipeline_depth):
                batch_num = window_start + i
                if batch_num >= total_batches:
                    break

                batch_idx = batch_num * batch_size
                batch_texts = texts[batch_idx:batch_idx + batch_size]

                # Filter out None texts
                valid_indices = [j for j, text in enumerate(batch_texts) if text is not None]
                valid_texts = [batch_texts[j] for j in valid_indices]

                if not valid_texts:
                    logger.debug(f"[UniXcoder] Batch {batch_num + 1}/{total_batches}: Skipped (no valid frames)")
                    continue

                # Tokenize batch (CPU operation)
                tokens = self.tokenizer(
                    valid_texts,
                    return_tensors="pt",
                    truncation=True,
                    max_length=self.max_tokens,
                    padding=True
                )

                # Select stream for this batch
                stream = self.cuda_streams[i] if self.cuda_streams else None

                # Create async task for this batch
                loop = asyncio.get_event_loop()
                task = loop.run_in_executor(
                    None,
                    self._generate_batch_embeddings_with_stream,
                    tokens,
                    stream
                )
                batch_tasks.append(task)
                batch_metadata.append((batch_idx, batch_num + 1, valid_indices))

            # Execute all batches in this window concurrently
            if batch_tasks:
                try:
                    batch_results = await asyncio.gather(*batch_tasks)

                    # Map embeddings back to results
                    for (batch_idx, batch_num, valid_indices), embeddings in zip(batch_metadata, batch_results):
                        for j, embedding in zip(valid_indices, embeddings):
                            results[batch_idx + j] = embedding

                        progress_pct = (batch_num * 100) // total_batches
                        logger.info(f"[UniXcoder] Batch {batch_num}/{total_batches} complete ({progress_pct}%)")

                except Exception as e:
                    logger.error(f"[UniXcoder] Pipeline window failed: {e}")
                    raise RuntimeError(f"Embedding generation failed: {e}")

        successful = sum(1 for r in results if r is not None)
        logger.info(f"[UniXcoder] Completed: {successful}/{len(frames)} embeddings generated")
        return results

    def _generate_batch_embeddings_with_stream(
        self,
        tokens: dict,
        stream: Optional['torch.cuda.Stream'] = None
    ) -> List[List[float]]:
        """
        Synchronous batch embedding generation with optional CUDA stream.

        Args:
            tokens: Tokenized batch (dict with 'input_ids', 'attention_mask', etc.)
            stream: Optional CUDA stream for pipeline parallelism

        Returns:
            List of embeddings (one per sample in batch)
        """
        # Move tokens to device on specified stream
        if stream is not None and self.device.type == 'cuda':
            with torch.cuda.stream(stream):
                tokens = {k: v.to(self.device, non_blocking=True) for k, v in tokens.items()}

                with torch.no_grad():
                    outputs = self.model(**tokens)
                    embeddings = outputs.last_hidden_state[:, 0, :].cpu()

                # Synchronize stream before returning to ensure data is ready
                stream.synchronize()
        else:
            # Fallback: default stream (backward compatible)
            tokens = {k: v.to(self.device) for k, v in tokens.items()}

            with torch.no_grad():
                outputs = self.model(**tokens)
                embeddings = outputs.last_hidden_state[:, 0, :].cpu()

        return embeddings.numpy().tolist()
