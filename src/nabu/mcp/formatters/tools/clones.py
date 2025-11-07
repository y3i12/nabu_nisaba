"""
Find clones markdown formatter.

Compact markdown formatter for find_clones tool output.
"""

from typing import Any, Dict
from ..tool_base import BaseToolMarkdownFormatter

class FindClonesMarkdownFormatter(BaseToolMarkdownFormatter):
    """
    Compact markdown formatter for find_clones tool output.
    
    Emphasizes severity-based prioritization for refactoring decisions.
    Optimized for code quality audits and duplicate detection.
    """
    
    def format(self, data: Dict[str, Any],) -> str:
        """Format find_clones output in compact style."""
        lines = []
        
        # Extract data
        clone_pairs = data.get("clone_pairs", [])
        summary = data.get("summary", {})
        metadata = data.get("metadata", {})
        clone_clusters = data.get("clone_clusters", [])
        
        # Header
        lines.append("# Clone Detection")
        lines.append("")
        
        # Summary - compact format
        lines.append("## Summary")
        total_pairs = summary.get("total_pairs", 0)
        by_severity = summary.get("by_severity", {})
        affected_files = summary.get("affected_files", 0)
        loc_reduction = summary.get("potential_loc_reduction", 0)
        
        critical = by_severity.get("CRITICAL", 0)
        high = by_severity.get("HIGH", 0)
        medium = by_severity.get("MEDIUM", 0)
        
        lines.append(f"Total pairs: {total_pairs} | CRITICAL: {critical}, HIGH: {high}, MEDIUM: {medium}")
        lines.append(f"Affected files: {affected_files} | Potential LOC reduction: {loc_reduction}")
        lines.append("")

        # Clone Clusters - stratified view
        if clone_clusters:
            lines.append("## Clone Clusters")

            multi_way = [c for c in clone_clusters if c["cluster_type"] == "multi-way"]
            pairwise = [c for c in clone_clusters if c["cluster_type"] == "pairwise"]

            if multi_way:
                lines.append("")
                multi_pairs = sum(c["pair_count"] for c in multi_way)
                lines.append(f"**Multi-way clusters ({len(multi_way)} clusters, {multi_pairs} pairs):**")

                for cluster in multi_way[:10]:  # Show top 10 multi-way
                    # Get representative function name (most common)
                    func_names = cluster["function_names"]
                    representative_name = func_names[0] if len(func_names) == 1 else f"{func_names[0]} (+{len(func_names)-1} variants)"

                    nodes = cluster["node_count"]
                    pairs = cluster["pair_count"]
                    avg_sim = cluster["avg_similarity"]
                    loc = cluster["total_loc"]

                    lines.append(f"├─ {representative_name}: {nodes} nodes, {pairs} pairs, avg {avg_sim:.3f} sim - {loc} LOC")

            if pairwise:
                lines.append("")
                lines.append(f"**Pairwise clones ({len(pairwise)} isolated pairs):**")

                for cluster in pairwise[:5]:  # Show top 5 pairwise
                    pair = cluster["pairs"][0]  # Each pairwise cluster has exactly 1 pair
                    func1_name = pair["function_1"]["name"]
                    func2_name = pair["function_2"]["name"]
                    similarity = pair["similarity"]

                    # Show different names or indicate same name
                    if func1_name == func2_name:
                        desc = func1_name
                    else:
                        desc = f"{func1_name} / {func2_name}"

                    lines.append(f"├─ {desc}: {similarity:.4f} similarity")

            lines.append("")

        # Clone pairs - table format with severity indicators
        lines.append("## Clone Pairs")
        if clone_pairs:
            lines.append("| Severity | Function 1 | Function 2 | Similarity | Recommendation |")
            lines.append("|----------|------------|------------|------------|----------------|")
            for pair in clone_pairs:
                func1 = pair.get("function_1", {})
                func2 = pair.get("function_2", {})
                similarity = pair.get("similarity", 0.0)
                severity = pair.get("severity", "UNKNOWN")
                recommendation = pair.get("recommendation", "")
                
                func1_name = func1.get("name", "unknown")
                func1_loc = func1.get("location", "unknown")
                func1_lines = func1.get("line_count", 0)
                
                func2_name = func2.get("name", "unknown")
                func2_loc = func2.get("location", "unknown")
                func2_lines = func2.get("line_count", 0)
                
                func1_desc = f"{func1_name} ({func1_loc}, {func1_lines} LOC)"
                func2_desc = f"{func2_name} ({func2_loc}, {func2_lines} LOC)"
                
                lines.append(f"| {severity} | {func1_desc} | {func2_desc} | {similarity:.4f} | {recommendation} |")
        else:
            lines.append("*(No clones found)*")
        lines.append("")
        
        # Metadata - settings used
        min_similarity = metadata.get("min_similarity", 0.0)
        excluded_same_file = metadata.get("excluded_same_file", False)
        min_function_size = metadata.get("min_function_size", 0)
        
        lines.append(f"Settings: min_similarity={min_similarity}, same_file_excluded={excluded_same_file}, min_function_size={min_function_size}")
           
        return "\n".join(lines)

