"""Vector search tools for semantic code discovery using CodeBERT embeddings."""

from pathlib import Path
import time

from nabu.mcp.tools.base import NabuTool
from nisaba.tools.base_tool import BaseToolResponse
from nabu.mcp.tools.search_tools import SearchTool


def _compute_clone_clusters(clone_pairs: list) -> list:
    """
    Compute connected components from clone pairs.
    
    Args:
        clone_pairs: List of clone pair dicts with function_1, function_2, similarity
        
    Returns:
        List of cluster dicts with metadata
    """
    if not clone_pairs:
        return []
    
    # Build adjacency list from clone pairs
    graph = {}  # qualified_name -> set of connected qualified_names
    pair_lookup = {}  # (qname1, qname2) -> pair dict
    
    for pair in clone_pairs:
        qn1 = pair["function_1"]["qualified_name"]
        qn2 = pair["function_2"]["qualified_name"]
        
        if qn1 not in graph:
            graph[qn1] = set()
        if qn2 not in graph:
            graph[qn2] = set()
            
        graph[qn1].add(qn2)
        graph[qn2].add(qn1)
        
        # Store pair for later retrieval (bidirectional)
        pair_key = tuple(sorted([qn1, qn2]))
        pair_lookup[pair_key] = pair
    
    # Find connected components via DFS
    visited = set()
    clusters = []
    
    def dfs(node, component):
        if node in visited:
            return
        visited.add(node)
        component.add(node)
        for neighbor in graph.get(node, []):
            dfs(neighbor, component)
    
    for node in graph:
        if node not in visited:
            component = set()
            dfs(node, component)
            if len(component) >= 2:  # Only include actual clusters
                clusters.append(component)
    
    # Build cluster metadata
    cluster_data = []
    for cluster_id, component in enumerate(clusters):
        # Get all pairs within this cluster
        component_list = list(component)
        cluster_pairs = []
        similarities = []
        total_loc = 0
        function_names = set()
        
        for i, qn1 in enumerate(component_list):
            for qn2 in component_list[i+1:]:
                pair_key = tuple(sorted([qn1, qn2]))
                if pair_key in pair_lookup:
                    pair = pair_lookup[pair_key]
                    cluster_pairs.append(pair)
                    similarities.append(pair["similarity"])
                    total_loc += pair["function_1"]["line_count"]
                    function_names.add(pair["function_1"]["name"])
                    function_names.add(pair["function_2"]["name"])
        
        cluster_data.append({
            "cluster_id": cluster_id,
            "node_count": len(component),
            "pair_count": len(cluster_pairs),
            "function_names": sorted(list(function_names)),
            "qualified_names": sorted(component_list),
            "pairs": cluster_pairs,
            "avg_similarity": round(sum(similarities) / len(similarities), 4) if similarities else 0.0,
            "min_similarity": round(min(similarities), 4) if similarities else 0.0,
            "max_similarity": round(max(similarities), 4) if similarities else 0.0,
            "total_loc": total_loc,
            "cluster_type": "multi-way" if len(component) >= 3 else "pairwise"
        })
    
    # Sort by node count (larger clusters first), then by avg similarity
    cluster_data.sort(key=lambda c: (c["node_count"], c["avg_similarity"]), reverse=True)
    
    return cluster_data


class FindClonesTool(NabuTool):
    """Detect duplicated or very similar code across the codebase."""

    async def execute(
        self,
        query: str | None = None,
        query_k: int = 20,
        min_similarity: float = 0.75,
        max_results: int = 50,
        exclude_same_file: bool = True,
        min_function_size: int = 10
    ) -> BaseToolResponse:
        """
        Find duplicate or nearly-identical implementations using vector similarity.

        Automatically detects copy-pasted code or similar logic that could be
        consolidated. Supports both whole-codebase scanning and targeted pattern
        detection. Uses high similarity threshold (default 0.75) to find actual
        clones, not just related code.

        :meta pitch: Find duplicated code across entire codebase or target specific patterns for refactoring.
        :meta when: Code quality reviews, refactoring planning, architecture audits, targeted pattern consolidation
        :meta emoji: 👯
        :meta tips: **Similarity Thresholds (P³ Consensus):**
            - **0.833-1.0**: Almost identical (likely copy-paste) - **CRITICAL**
            - **0.666-0.832**: Very similar patterns - **HIGH priority** for refactoring
            - **0.60-0.665**: Somewhat similar - Review case-by-case - **MEDIUM**
        :meta examples: **Standard clone detection:**
            ```python
            # Find all clones across codebase
            find_clones(
                min_similarity=0.75,
                exclude_same_file=True
            )

            # Find clones of specific pattern (targeted detection)
            find_clones(
                query="database connection management",
                query_k=20,
                min_similarity=0.75
            )
            ```
        :param query: Optional semantic query to find clones OF matching frames (default None = find all clones)
        :param query_k: Number of search results to use as clone sources when query is provided (default 20)
        :param min_similarity: Minimum similarity for clone detection (default 0.75, range 0.60-1.0)
        :param max_results: Maximum clone pairs to return (default 50)
        :param exclude_same_file: If True, only find clones in different files (default True)
        :param min_function_size: Minimum function size in lines (default 10, ignore trivial functions)
        :return: List of clone pairs with similarity scores, severity, and refactoring recommendations
        """
        start_time = time.time()

        try:
            # Check indexing status before proceeding
            indexing_check = self._check_indexing_status()
            if indexing_check:
                return indexing_check

            # Validate parameters
            if not 0.0 <= min_similarity <= 1.0:
                return self.response_error(f"min_similarity must be between 0.0 and 1.0, got {min_similarity}")

            warnings = [f"min_similarity={min_similarity} is quite low, may produce false positives"] if min_similarity < 0.60 else None

            # Determine target frames: either from query or all frames
            if query:
                # Use SearchTool to find target candidates
                search_tool = SearchTool(factory=self.factory)
                search_result = await search_tool.execute(
                    query=query,
                    k=query_k,
                    frame_type_filter="CALLABLE",  # Clones only work on CALLABLEs
                    compact_metadata=False  # Need full metadata for clone detection
                )

                # Check if search succeeded
                if not search_result.get('success', False):
                    return self.response_error(f"Search failed: {search_result.get('error', 'Unknown error')}")

                search_results = search_result.get('data', {}).get('results', [])
                if not search_results:
                    return self.response_success(self._empty_clone_response(query, query_k, min_similarity, max_results, exclude_same_file, min_function_size))

                # Extract frame IDs from search results
                target_frame_ids = [item['id'] for item in search_results]

                # Fetch ONLY these frames from DB
                frames_query = """
                MATCH (f:Frame)
                WHERE f.id IN $target_ids
                  AND f.type = 'CALLABLE'
                  AND f.embedding_non_linear_consensus IS NOT NULL
                  AND (f.end_line - f.start_line + 1) >= $min_size
                RETURN f.id as id, f.qualified_name as qname, f.name as name,
                       f.file_path as path, f.start_line as start_line, f.end_line as end_line,
                       f.embedding_non_linear_consensus as embedding
                """
                frames_result = self.db_manager.execute(frames_query, {
                    "target_ids": target_frame_ids,
                    "min_size": min_function_size
                })
            else:
                # Original behavior: get all CALLABLE frames
                frames_query = """
                MATCH (f:Frame {type: 'CALLABLE'})
                WHERE f.embedding_non_linear_consensus IS NOT NULL
                  AND (f.end_line - f.start_line + 1) >= $min_size
                RETURN f.id as id, f.qualified_name as qname, f.name as name,
                       f.file_path as path, f.start_line as start_line, f.end_line as end_line,
                       f.embedding_non_linear_consensus as embedding
                """
                frames_result = self.db_manager.execute(frames_query, {"min_size": min_function_size})

            if not frames_result or not hasattr(frames_result, 'get_as_df'):
                return self.response_success(self._empty_clone_response(query, query_k, min_similarity, max_results, exclude_same_file, min_function_size))

            frames_df = frames_result.get_as_df()
            if frames_df.empty:
                return self.response_success(self._empty_clone_response(query, query_k, min_similarity, max_results, exclude_same_file, min_function_size))

            # Find clones for each frame
            clone_pairs = []
            seen_pairs = set()
            affected_files = set()
            severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}
            total_loc_reduction = 0

            for _, f1_row in frames_df.iterrows():
                # Query similar functions
                vector_query = """
                CALL QUERY_VECTOR_INDEX(
                    'Frame',
                    'frame_embedding_non_linear_consensus_idx',
                    $embedding,
                    10
                ) RETURN node, distance
                """

                vector_result = self.db_manager.execute(vector_query, {"embedding": f1_row['embedding']})

                if not vector_result:
                    continue

                results_df = vector_result.get_as_df()

                for _, result_row in results_df.iterrows():
                    f2 = result_row['node']
                    distance = float(result_row['distance'])
                    similarity = 1.0 - distance

                    # Apply filters
                    if similarity < min_similarity:
                        continue
                    if f2['id'] == f1_row['id']:  # Skip self
                        continue
                    if exclude_same_file and f2['file_path'] == f1_row['path']:
                        continue

                    # Avoid duplicate pairs (A-B and B-A)
                    pair_key = tuple(sorted([f1_row['id'], f2['id']]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    # Categorize severity
                    if similarity >= 0.833:
                        severity = "CRITICAL"
                        recommendation = "Almost identical - strong consolidation candidate"
                    elif similarity >= 0.666:
                        severity = "HIGH"
                        recommendation = "Very similar - review for potential consolidation"
                    else:
                        severity = "MEDIUM"
                        recommendation = "Somewhat similar - manual review recommended"

                    severity_counts[severity] += 1

                    f1_lines = f1_row['end_line'] - f1_row['start_line'] + 1
                    f2_lines = f2['end_line'] - f2['start_line'] + 1
                    total_loc_reduction += min(f1_lines, f2_lines)

                    affected_files.add(f1_row['path'])
                    affected_files.add(f2['file_path'])

                    clone_pairs.append({
                        "function_1": {
                            "qualified_name": f1_row['qname'],
                            "name": f1_row['name'],
                            "file_path": f1_row['path'],
                            "location": f"{Path(f1_row['path']).name}:{f1_row['start_line']}-{f1_row['end_line']}",
                            "line_count": f1_lines
                        },
                        "function_2": {
                            "qualified_name": f2['qualified_name'],
                            "name": f2['name'],
                            "file_path": f2['file_path'],
                            "location": f"{Path(f2['file_path']).name}:{f2['start_line']}-{f2['end_line']}",
                            "line_count": f2_lines
                        },
                        "similarity": round(similarity, 4),
                        "severity": severity,
                        "recommendation": recommendation
                    })

                    if len(clone_pairs) >= max_results:
                        break

                if len(clone_pairs) >= max_results:
                    break

            # Sort by similarity desc
            clone_pairs.sort(key=lambda x: x['similarity'], reverse=True)

            # Compute clone clusters
            clone_clusters = _compute_clone_clusters(clone_pairs)

            # Compute cluster summary statistics
            cluster_summary = {
                "total_clusters": len(clone_clusters),
                "multi_way_clusters": sum(1 for c in clone_clusters if c["cluster_type"] == "multi-way"),
                "pairwise_clusters": sum(1 for c in clone_clusters if c["cluster_type"] == "pairwise"),
                "largest_cluster_size": max((c["node_count"] for c in clone_clusters), default=0)
            }

            return self.response_success({
                "clone_pairs": clone_pairs[:max_results],
                "clone_clusters": clone_clusters,
                "summary": {
                    "total_pairs": len(clone_pairs),
                    "by_severity": severity_counts,
                    "affected_files": len(affected_files),
                    "potential_loc_reduction": total_loc_reduction,
                    "cluster_summary": cluster_summary
                },
                "metadata": {
                    "query": query,
                    "query_k": query_k if query else None,
                    "source_frames": len(frames_df),
                    "min_similarity": min_similarity,
                    "max_results": max_results,
                    "excluded_same_file": exclude_same_file,
                    "min_function_size": min_function_size
                }
            })

        except Exception as e:
            return self.response_exception(e, "Find clones tool failed")

    def _empty_clone_response(self, query, query_k, min_sim, max_res, exclude_same, min_size):
        return {
            "clone_pairs": [],
            "clone_clusters": [],
            "summary": {
                "total_pairs": 0,
                "by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0},
                "affected_files": 0,
                "potential_loc_reduction": 0,
                "cluster_summary": {
                    "total_clusters": 0,
                    "multi_way_clusters": 0,
                    "pairwise_clusters": 0,
                    "largest_cluster_size": 0
                }
            },
            "metadata": {
                "query": query,
                "query_k": query_k if query else None,
                "source_frames": 0,
                "min_similarity": min_sim,
                "max_results": max_res,
                "excluded_same_file": exclude_same,
                "min_function_size": min_size
            }
        }
