"""
Impact analysis markdown formatter.

Compact markdown formatter for impact_analysis_workflow tool output.
"""

from typing import Any, Dict
from pathlib import Path
from ..tool_base import BaseToolMarkdownFormatter

class ImpactAnalysisWorkflowMarkdownFormatter(BaseToolMarkdownFormatter):
    """
    Compact markdown formatter for impact_analysis_workflow tool output.
    Emphasizes risk assessment and actionable recommendations.
    """

    def format(self, data: Dict[str, Any], execution_time_ms: float = 0.0) -> str:
        """Format impact_analysis_workflow output in compact style."""
        lines = []
        
        # === HEADER ===
        target = data.get("target", {})
        target_qname = target.get("qualified_name", "unknown")
        target_name = target.get("name", "unknown")
        target_type = target.get("type", "unknown")
        
        lines.append(f"# Impact Analysis: {target_name}")
        lines.append(f"Target: {target_qname} ({target_type})")
        lines.append("")
        
        # === IMPACT SUMMARY (single-line metrics) ===
        impact_summary = data.get("impact_summary", {})
        lines.append("## Impact Summary")
        lines.append(
            f"**Affected**: {impact_summary.get('total_affected_files', 0)} files, "
            f"{impact_summary.get('total_affected_callables', 0)} callables | "
            f"**Depth**: {impact_summary.get('max_depth_reached', 0)} | "
            f"**Blast Radius**: {impact_summary.get('estimated_blast_radius', 'UNKNOWN')}"
        )
        
        risk_level = impact_summary.get("risk_level", "UNKNOWN")
        lines.append(f"**Risk Level**: {risk_level}")
        lines.append("")
        
        # === RISK ASSESSMENT (compact) ===
        risk_assessment = data.get("risk_assessment", {})
        if risk_assessment:
            lines.append("## Risk Factors `factor (score) - explanation`")
            for factor in risk_assessment.get("risk_factors", []):
                factor_name = factor.get("factor", "unknown")
                score = factor.get("score", 0.0)
                explanation = factor.get("explanation", "")
                lines.append(f"{factor_name} ({score:.2f}) - {explanation}")
            lines.append("")
            
            recommendation = risk_assessment.get("recommendation", "")
            if recommendation:
                lines.append(f"**Risk Recommendation**: {recommendation}")
                lines.append("")
        
        # === TEST COVERAGE (compact) ===
        test_coverage = data.get("test_coverage", {})
        if test_coverage:
            has_tests = test_coverage.get("has_direct_tests", False)
            test_count = test_coverage.get("test_count", 0)
            coverage_assessment = test_coverage.get("coverage_assessment", "UNKNOWN")
            
            lines.append(f"## Test Coverage: {coverage_assessment}")
            if has_tests:
                lines.append(f"Direct tests: {test_count} file(s)")
                test_files = test_coverage.get("test_files", [])
                for test_file in test_files:
                    lines.append(f"- {Path(test_file).name}")
            else:
                lines.append("⚠ No direct test files found")
            lines.append("")
        
        # === AFFECTED FILES (compact list) ===
        affected_files = data.get("affected_files", [])
        if affected_files:
            lines.append(f"## Affected Files ({len(affected_files)})")
            lines.append("`file (affected_methods_count)`")
            for file_info in affected_files:
                file_path = file_info.get("file_path", "")
                filename = Path(file_path).name if file_path else "unknown"
                affected_count = len(file_info.get("affected_methods", []))
                lines.append(f"{filename} ({affected_count})")
            lines.append("")
        
        # === DEPENDENCY TREE SUMMARY (compact) ===
        dependency_tree = data.get("dependency_tree", {})
        if dependency_tree:
            lines.append("## Dependency Tree `depth (callers_count)`")
            for key in sorted(dependency_tree.keys()):
                if key.startswith("depth_"):
                    depth_num = key.replace("depth_", "")
                    callers = dependency_tree[key]
                    lines.append(f"Depth {depth_num}: {len(callers)} caller(s)")
            lines.append("")
        
        # === CHANGE RECOMMENDATIONS (actionable) ===
        change_recommendations = data.get("change_recommendations", [])
        if change_recommendations:
            lines.append("## Change Recommendations")
            for rec in change_recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        # === VISUALIZATION (if present) ===
        visualization = data.get("visualization", {})
        if visualization and visualization.get("format") == "mermaid":
            lines.append("## Dependency Visualization")
            lines.append("```mermaid")
            lines.append(visualization.get("diagram", ""))
            lines.append("```")
            lines.append("")

        # Execution time footer
        lines.append(f"*execution_time {execution_time_ms:.2f}ms*")
        
        return "\n".join(lines)

