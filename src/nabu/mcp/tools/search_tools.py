"""Unified search tool combining FTS, semantic, and code-vector search with RRF fusion."""

import asyncio
import re
import time
from pathlib import Path
from typing import Dict, Any, List

from nabu.mcp.tools.base import NabuTool
from nisaba.tools.base_tool import BaseToolResponse
from nabu.mcp.utils.snippet_extractor import extract_snippets
from nabu.mcp.utils.regex_helpers import extract_keywords_from_regex as _extract_keywords_from_regex


def _rrf_fusion(
    fts_results: List[Dict[str, Any]],
    semantic_results: List[Dict[str, Any]],
    regex_results: List[Dict[str, Any]] = [],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion for combining heterogeneous search results.

    Implements: score(item) = Σ(1 / (k + rank_in_mechanism_i))

    RRF is score-agnostic - only ranks matter. This elegantly handles:
    - BM25 scores (unbounded)
    - Cosine similarity (bounded [0,1])
    - Different scoring scales

    Args:
        fts_results: FTS/BM25 results (ranked by score)
        semantic_results: Semantic vector search results (ranked by similarity)
        regex_results: Regex pattern search results (ranked by match quality)
        k: RRF constant (default 60, standard value)

    Returns:
        Unified result list sorted by RRF score (highest first)
    """
    # Extract ranked ID lists from each mechanism
    fts_ids = [r['id'] for r in fts_results]
    sem_ids = [r['id'] for r in semantic_results]
    regex_ids = [r['id'] for r in regex_results]

    # Build unified ID → frame mapping (preserve all metadata)
    all_items = {}
    for r in fts_results + semantic_results + regex_results:
        if r['id'] not in all_items:
            all_items[r['id']] = r

    # Compute RRF scores
    scored = []
    for item_id, frame_data in all_items.items():
        rrf_score = 0.0
        mechanisms = []

        # FTS contribution
        if item_id in fts_ids:
            rank = fts_ids.index(item_id) + 1  # 1-indexed
            rrf_score += 1.0 / (k + rank)
            mechanisms.append('fts')

        # Semantic contribution
        if item_id in sem_ids:
            rank = sem_ids.index(item_id) + 1
            rrf_score += 1.0 / (k + rank)
            mechanisms.append('semantic')

        # Regex contribution
        if item_id in regex_ids:
            rank = regex_ids.index(item_id) + 1
            rrf_score += 1.0 / (k + rank)
            mechanisms.append('regex')

        scored.append({
            **frame_data,
            'rrf_score': round(rrf_score, 6),
            'mechanisms': mechanisms
        })

    # Sort by RRF score descending
    scored.sort(key=lambda x: x['rrf_score'], reverse=True)
    return scored


class SearchTool(NabuTool):
    """
    Unified search combining FTS, semantic, and code-vector search with RRF fusion.

    Automatically runs multiple search mechanisms in parallel and fuses results
    using Reciprocal Rank Fusion. Eliminates agent decision paralysis by letting
    the tool determine the best approach.
    """

    async def execute(
        self,
        query: str,
        k: int = 10,
        is_regex_input: bool = False,
        conjunctive: bool = False,
        K: float = 1.2,
        B: float = 0.75,
        frame_type_filter: str | None = "CALLABLE|CLASS",
        context_lines: int = 3,
        max_snippets: int = 5,
        compact_metadata: bool = True
    ) -> BaseToolResponse:
        """
        Execute unified search combining FTS, semantic, and code-vector mechanisms.

        Runs multiple search mechanisms in parallel and fuses results using Reciprocal
        Rank Fusion. Mechanisms automatically weighted based on relevance. Set
        is_regex_input=True when query is a regex pattern for syntactic matching.

        Parameter guidance:
        - k: Number of results to return (default 10, range 1-50)
        - is_regex_input: Enable for regex patterns (default False)
        - conjunctive: Require all keywords present (default False, OR logic)
        - frame_type_filter: Post-fusion filter (default "CALLABLE|CLASS")
        - context_lines: Snippet context size (default 3)
        - compact_metadata: Token efficiency mode (default True)

        :param query: Search query (keywords, natural language, code snippet, or regex pattern)
        :param k: Number of final results to return (default 10)
        :param is_regex_input: Use regex pattern matching (default False)
        :param conjunctive: BM25 AND logic - all keywords must match (default False)
        :param K: BM25 term frequency saturation (default 1.2, range 0.1-5.0)
        :param B: BM25 length normalization (default 0.75, range 0.0-1.0)
        :param frame_type_filter: Regex filter for frame types (default "CALLABLE|CLASS")
        :param context_lines: Lines of context around matches in snippets (default 3)
        :param max_snippets: Maximum snippet windows per result (default 5)
        :param compact_metadata: Strip verbose metadata for token efficiency (default True)
        :return: Fused search results with RRF scores, mechanisms used, and code snippets
        """
        start_time = time.time()

        try:
            # Check indexing status before proceeding
            indexing_check = self._check_indexing_status()
            if indexing_check:
                return indexing_check

            # Validate parameters
            if not query or not query.strip():
                return self.response_error("Query cannot be empty")

            if k < 1 or k > 50:
                return self.response_error(f"k must be between 1 and 50, got {k}")

            # Validate regex pattern if is_regex_input
            if is_regex_input:
                try:
                    re.compile(query.strip())
                except re.error as e:
                    return self.response_error(f"Invalid regex pattern: {e}")

            # Always run FTS + Semantic, optionally add regex search
            # Fetch k*3 candidates from each to compensate for post-fusion filtering
            tasks = [
                self._fts_search(query.strip(), conjunctive, K, B, k * 3, None),
                self._semantic_search(query.strip(), k * 3, "CALLABLE")
            ]
            enabled_mechanisms = ['fts', 'semantic']

            if is_regex_input:
                tasks.append(self._regex_search(query.strip(), k * 3, frame_type_filter))
                enabled_mechanisms.append('regex')

            # Execute all searches concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Extract results, handle exceptions gracefully
            # Always have FTS and Semantic (indices 0 and 1)
            fts_res = [] if isinstance(results[0], Exception) else results[0]
            sem_res = [] if isinstance(results[1], Exception) else results[1]
            regex_res = []

            if isinstance(results[0], Exception):
                self.logger().warning(f"FTS search failed: {results[0]}")
            if isinstance(results[1], Exception):
                self.logger().warning(f"Semantic search failed: {results[1]}")

            # Conditionally extract regex results (index 2 if regex enabled)
            if is_regex_input:
                if isinstance(results[2], Exception):
                    self.logger().warning(f"Regex search failed: {results[2]}")
                else:
                    regex_res = results[2]

            # RRF fusion
            fused = _rrf_fusion(fts_res, sem_res, regex_res)

            # Apply frame_type_filter post-fusion
            if frame_type_filter:
                fused = [
                    r for r in fused
                    if re.search(frame_type_filter, r.get('type', ''), re.IGNORECASE)
                ]

            # Limit to k and extract snippets
            final = fused[:k]

            for item in final:
                content = item.get('content', '')
                if content:
                    # Extract snippets
                    item['snippets'] = extract_snippets(
                        content, query.strip(), context_lines, max_snippets
                    )

                    # For small frames, include full content preview
                    start_line = item.get('start_line', 0)
                    end_line = item.get('end_line', 0)
                    line_count = end_line - start_line + 1

                    if line_count <= 30:
                        item['content_preview'] = content

                    # Remove full content if compact mode
                    if compact_metadata:
                        del item['content']

            # Build response
            return self.response_success({
                "query": query.strip(),
                "results": final,
                "metadata": {
                    "k": k,
                    "mechanisms_used": enabled_mechanisms,
                    "total_candidates_before_filter": len(fts_res) + len(sem_res) + len(regex_res),
                    "candidates_after_fusion": len(fused),
                    "returned": len(final)
                }
            })

        except Exception as e:
            return self.response_exception(e, "Search failed")

    async def _fts_search(
        self,
        query: str,
        conjunctive: bool,
        K: float,
        B: float,
        top: int,
        frame_type_filter: str | None
    ) -> List[Dict[str, Any]]:
        """
        Execute BM25 full-text search across dual indices.

        Queries both frame_fts_index (content/metadata) and
        frame_resolution_fts_index (names/paths) in parallel,
        then merges results by taking MAX score per frame.

        Returns raw results with IDs for RRF ranking.
        """

        # Build base FTS query parameters
        fts_params = f"conjunctive := {conjunctive}, K := {K}, B := {B}"
        if top > 0:
            fts_params += f", TOP := {top}"

        # Query 1: Resolution index (name, qualified_name, file_path)
        resolution_query = (
            f"CALL QUERY_FTS_INDEX('Frame', 'frame_resolution_fts_index', '{query}', "
            f"{fts_params}) "
            "RETURN score, node.id, node.type, node.name, node.qualified_name, "
            "node.file_path, node.start_line, node.end_line, node.content;"
        )

        # Query 2: Content index (type, language, confidence_tier, content)
        content_query = (
            f"CALL QUERY_FTS_INDEX('Frame', 'frame_fts_index', '{query}', "
            f"{fts_params}) "
            "RETURN score, node.id, node.type, node.name, node.qualified_name, "
            "node.file_path, node.start_line, node.end_line, node.content;"
        )

        # Execute both queries SEQUENTIALLY to avoid KuzuDB write transaction conflicts
        # KuzuDB only allows one write transaction at a time, and FTS operations can trigger locks
        resolution_result = None
        content_result = None

        try:
            resolution_result = await asyncio.to_thread(
                self.db_manager.execute, resolution_query, load_extensions=True
            )
        except Exception as e:
            self.logger().warning(f"FTS resolution index query failed: {e}")

        try:
            content_result = await asyncio.to_thread(
                self.db_manager.execute, content_query, load_extensions=True
            )
        except Exception as e:
            self.logger().warning(f"FTS content index query failed: {e}")

        results_tuple = (resolution_result, content_result)

        # Merge results by frame ID, taking MAX score
        frame_dict = {}  # id -> {data, score}

        for idx, result in enumerate(results_tuple):
            if result is None or isinstance(result, Exception):
                continue

            if not result or not hasattr(result, 'get_as_df'):
                continue

            df = result.get_as_df()
            if df.empty:
                continue

            for _, row in df.iterrows():
                frame_id = str(row['node.id'])
                score = float(row['score'])

                # If frame already seen, take MAX score
                if frame_id in frame_dict:
                    if score > frame_dict[frame_id]['score']:
                        frame_dict[frame_id]['score'] = score
                else:
                    # First time seeing this frame
                    frame_dict[frame_id] = {
                        'score': score,
                        'id': frame_id,
                        'type': row['node.type'],
                        'name': row['node.name'],
                        'qualified_name': row['node.qualified_name'],
                        'file_path': row['node.file_path'],
                        'location': f"{Path(row['node.file_path']).name}:{row['node.start_line']}-{row['node.end_line']}",
                        'start_line': row['node.start_line'],
                        'end_line': row['node.end_line'],
                        'content': row.get('node.content', '')
                    }

        # Convert to list and sort by score (descending)
        results = sorted(frame_dict.values(), key=lambda x: x['score'], reverse=True)

        return results

    async def _semantic_search(
        self,
        query: str,
        k: int,
        frame_type: str
    ) -> List[Dict[str, Any]]:
        """
        Execute semantic vector search using P3 consensus (UniXcoder × CodeBERT).

        Returns raw results with IDs for RRF ranking.
        """
        try:
            from nabu.embeddings import (
                get_unixcoder_generator,
                get_codebert_generator,
                compute_non_linear_consensus
            )

            # Generate P3 consensus embedding (proven best approach)
            ux_gen = get_unixcoder_generator()
            cb_gen = get_codebert_generator()

            ux_emb = ux_gen.generate_embedding_from_text(query)
            cb_emb = cb_gen.generate_embedding_from_text(query)

            if not ux_emb or not cb_emb:
                self.logger().warning("Failed to generate embeddings for semantic search")
                return []

            query_embedding = compute_non_linear_consensus(ux_emb, cb_emb)

        except ImportError as e:
            self.logger().error(f"Embedding imports failed: {e}")
            return []

        # Query vector index
        vector_query = """
        CALL QUERY_VECTOR_INDEX(
            'Frame',
            'frame_embedding_non_linear_consensus_idx',
            $embedding,
            $k_plus_buffer
        ) RETURN node, distance
        """

        vector_result = self.db_manager.execute(vector_query, {
            "embedding": query_embedding,
            "k_plus_buffer": k * 2
        })

        if not vector_result or not hasattr(vector_result, 'get_as_df'):
            return []

        results_df = vector_result.get_as_df()
        if results_df.empty:
            return []

        # Convert to list of dicts
        results = []
        for _, row in results_df.iterrows():
            node = row['node']
            distance = float(row['distance'])
            similarity = 1.0 - distance

            if node['type'] != frame_type:
                continue

            results.append({
                'id': str(node['id']),
                'similarity': round(similarity, 4),
                'type': node['type'],
                'name': node['name'],
                'qualified_name': node['qualified_name'],
                'file_path': node['file_path'],
                'location': f"{Path(node['file_path']).name}:{node['start_line']}-{node['end_line']}",
                'start_line': node['start_line'],
                'end_line': node['end_line'],
                'content': node.get('content', '')
            })

        return results

    async def _regex_search(
        self,
        pattern: str,
        top: int,
        frame_type_filter: str | None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid regex pattern search using two-path strategy.

        PATH 1 (Always Fast):
        - Direct Cypher regex on name/qualified_name fields
        - No table scan (small indexed fields)
        - Catches: class names, method names, qualified paths

        PATH 2 (Smart Content Search):
        - Extract keywords from regex → FTS pre-filter (indexed, fast)
        - FTS returns ~top*3 candidates (small set)
        - Apply Python regex filter on candidates only
        - No full table scan!

        Particularly useful for:
        - Finding class/function definitions: r"class (Foo|Bar|Baz)"
        - Finding import statements: r"import.*from.*tools"
        - Finding function calls: r"method_name\\(\\)"

        Returns raw results with IDs for RRF ranking.

        Args:
            pattern: Regex pattern (Python/Perl syntax)
            top: Max results to fetch
            frame_type_filter: Optional regex filter for frame types

        Returns:
            List of matching frames in standard format
        """
        results = []
        result_ids = set()

        try:
            # ========== PATH 1: Direct regex on names (always run) ==========
            # Fast - only searches small string fields (name, qualified_name)
            # Note: Using f-string for pattern and LIMIT as KuzuDB parameter binding
            # has issues with regex patterns and LIMIT clauses
            # Escape single quotes for safe Cypher string interpolation
            escaped_pattern = pattern.replace("'", "\\'")

            cypher_query = f"""
            MATCH (f:Frame)
            WHERE f.name =~ '{escaped_pattern}'
               OR f.qualified_name =~ '{escaped_pattern}'
            RETURN f.id as id, f.type as type, f.name as name,
                   f.qualified_name as qualified_name,
                   f.file_path as file_path, f.start_line as start_line,
                   f.end_line as end_line, f.content as content
            LIMIT {top}
            """

            result = self.db_manager.execute(cypher_query)

            if result and hasattr(result, 'get_as_df'):
                df = result.get_as_df()
                if not df.empty:
                    for _, row in df.iterrows():
                        frame_id = str(row['id'])
                        # Ensure content is a string (handle NaN, None, floats from DB)
                        content = row.get('content', '')
                        if not isinstance(content, str):
                            content = str(content) if content is not None else ''

                        results.append({
                            'id': frame_id,
                            'type': row['type'],
                            'name': row['name'],
                            'qualified_name': row['qualified_name'],
                            'file_path': row['file_path'],
                            'location': f"{Path(row['file_path']).name}:{row['start_line']}-{row['end_line']}",
                            'start_line': row['start_line'],
                            'end_line': row['end_line'],
                            'content': content
                        })
                        result_ids.add(frame_id)

            # ========== PATH 2: FTS + regex filter (if keywords extractable) ==========
            # Smart - uses FTS index to narrow candidates, then regex filter
            if len(results) < top:
                keywords = _extract_keywords_from_regex(pattern)

                if keywords:
                    # Use FTS to get candidates (leverages index, fast!)
                    fts_candidates = await self._fts_search(
                        query=keywords,
                        conjunctive=False,  # OR logic for broader recall
                        K=1.2,
                        B=0.75,
                        top=top * 3,  # Oversample for post-filtering
                        frame_type_filter=None  # Apply frame_type_filter post-fusion
                    )

                    # Compile regex once for efficiency
                    try:
                        regex_obj = re.compile(pattern)
                    except re.error as e:
                        self.logger().warning(f"Regex compilation failed in content filter: {e}")
                        return results[:top]

                    # Filter FTS candidates with regex on content
                    for candidate in fts_candidates:
                        frame_id = candidate['id']

                        # Skip if already have this frame
                        if frame_id in result_ids:
                            continue

                        # Apply regex filter on content (ensure it's a string)
                        content = candidate.get('content', '')
                        if not isinstance(content, str):
                            # Skip non-string content (e.g., NaN, float, None)
                            continue

                        if regex_obj.search(content):
                            results.append(candidate)
                            result_ids.add(frame_id)

                            # Stop if we have enough results
                            if len(results) >= top:
                                break

            return results[:top]

        except Exception as e:
            self.logger().error(f"Regex search failed: {e}")
            return []
