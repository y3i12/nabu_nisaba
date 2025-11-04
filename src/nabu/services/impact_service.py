"""
Impact analysis service.

Handles dependency impact analysis, risk assessment, and change recommendations
independent of MCP layer.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

from nabu.services.base import BaseService

logger = logging.getLogger(__name__)


@dataclass
class ImpactRequest:
    """Request parameters for impact analysis."""
    target_frame_id: str
    target_frame_data: Dict[str, Any]
    max_depth: int = 2
    risk_assessment: bool = True
    include_test_coverage: bool = True


@dataclass
class ImpactResult:
    """Domain result from impact analysis."""
    target: Dict[str, Any]
    dependency_tree: Dict[str, Any]
    affected_files: List[Dict[str, Any]]
    impact_summary: Dict[str, Any]
    risk_assessment: Optional[Dict[str, Any]] = None
    test_coverage: Optional[Dict[str, Any]] = None
    change_recommendations: Optional[List[str]] = None


class ImpactAnalysisService(BaseService):
    """
    Service for dependency impact analysis.

    Handles dependency traversal, risk scoring, and test coverage analysis.
    """

    async def analyze_impact(self, request: ImpactRequest) -> ImpactResult:
        """
        Analyze impact of changing a code element.

        Traverses dependency graph to find affected code.

        Args:
            request: ImpactRequest with target and parameters

        Returns:
            ImpactResult with dependency tree and risk assessment
        """
        # Traverse dependency tree
        dependency_tree = await self._traverse_callers(
            request.target_frame_id,
            request.max_depth,
            request.target_frame_data.get("type")
        )

        # Aggregate affected files
        affected_files = self._aggregate_affected_files(dependency_tree)

        # Build impact summary
        impact_summary = {
            "total_affected_files": len(affected_files),
            "total_affected_callables": sum(
                len(f["affected_methods"]) for f in affected_files
            ),
            "max_depth_reached": request.max_depth,
            "estimated_blast_radius": self._estimate_blast_radius(len(affected_files))
        }

        # Assess risk if requested
        risk_assessment = None
        if request.risk_assessment:
            risk_assessment = self._assess_risk(
                request.target_frame_data,
                dependency_tree,
                affected_files
            )
            impact_summary["risk_level"] = risk_assessment.get("overall_risk", "UNKNOWN")

        # Generate recommendations if requested
        change_recommendations = None
        if request.risk_assessment and request.include_test_coverage:
            change_recommendations = self._generate_recommendations(
                risk_assessment,
                {}  # test_coverage placeholder
            )

        return ImpactResult(
            target=request.target_frame_data,
            dependency_tree=dependency_tree,
            affected_files=affected_files,
            impact_summary=impact_summary,
            risk_assessment=risk_assessment,
            test_coverage=None,  # Placeholder for future implementation
            change_recommendations=change_recommendations
        )

    async def _traverse_callers(
        self,
        target_id: str,
        max_depth: int,
        target_type: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Traverse callers using BFS up to max_depth.

        Args:
            target_id: Frame ID to analyze
            max_depth: Maximum traversal depth
            target_type: Type of target frame (CLASS, CALLABLE, etc.)

        Returns:
            Dict mapping depth_N_callers to list of caller dicts
        """
        if not self.db_manager:
            return {}

        dependency_tree = {}

        # Choose query strategy based on target type
        for depth in range(1, max_depth + 1):
            try:
                if target_type == 'CALLABLE':
                    query = self._build_callable_query(depth)
                elif target_type == 'CLASS':
                    query = self._build_class_query(depth)
                else:
                    logger.warning(f"Unsupported target type: {target_type}")
                    dependency_tree[f"depth_{depth}_callers"] = []
                    continue

                result = self.db_manager.execute(query, {"target_id": target_id})
                df = result.get_as_df()

                callers = []
                for _, row in df.iterrows():
                    callers.append({
                        "name": row['name'],
                        "qualified_name": row['qualified_name'],
                        "file_path": row['file_path'],
                        "location": f"{Path(row['file_path']).name}:{row['start_line']}",
                        "type": row['type'],
                        "depth": int(row['path_length'])
                    })

                dependency_tree[f"depth_{depth}_callers"] = callers

            except Exception as e:
                logger.warning(f"Failed to get depth {depth} callers: {e}")
                dependency_tree[f"depth_{depth}_callers"] = []

        return dependency_tree

    def _build_callable_query(self, depth: int) -> str:
        """Build cypher query for CALLABLE target at given depth."""
        if depth == 1:
            return """
            MATCH (target:Frame {id: $target_id})<-[e:Edge {type: 'CALLS'}]-(caller:Frame)
            RETURN DISTINCT
                caller.name as name,
                caller.qualified_name as qualified_name,
                caller.file_path as file_path,
                caller.start_line as start_line,
                caller.type as type,
                1 as path_length
            LIMIT 50
            """
        elif depth == 2:
            return """
            MATCH (target:Frame {id: $target_id})<-[:Edge {type: 'CALLS'}]-(caller1:Frame)<-[:Edge {type: 'CALLS'}]-(caller:Frame)
            WHERE caller.id <> $target_id
            RETURN DISTINCT
                caller.name as name,
                caller.qualified_name as qualified_name,
                caller.file_path as file_path,
                caller.start_line as start_line,
                caller.type as type,
                2 as path_length
            LIMIT 50
            """
        else:  # depth == 3
            return """
            MATCH (target:Frame {id: $target_id})<-[:Edge {type: 'CALLS'}]-(caller1:Frame)<-[:Edge {type: 'CALLS'}]-(caller2:Frame)<-[:Edge {type: 'CALLS'}]-(caller:Frame)
            WHERE caller.id <> $target_id AND caller.id <> caller1.id
            RETURN DISTINCT
                caller.name as name,
                caller.qualified_name as qualified_name,
                caller.file_path as file_path,
                caller.start_line as start_line,
                caller.type as type,
                3 as path_length
            LIMIT 50
            """

    def _build_class_query(self, depth: int) -> str:
        """Build cypher query for CLASS target at given depth."""
        if depth == 1:
            return """
            MATCH (target:Frame {id: $target_id})-[:Edge {type: 'CONTAINS'}]->(method:Frame {type: 'CALLABLE'})<-[e:Edge {type: 'CALLS'}]-(caller:Frame)
            RETURN DISTINCT
                caller.name as name,
                caller.qualified_name as qualified_name,
                caller.file_path as file_path,
                caller.start_line as start_line,
                caller.type as type,
                1 as path_length
            LIMIT 50
            """
        elif depth == 2:
            return """
            MATCH (target:Frame {id: $target_id})-[:Edge {type: 'CONTAINS'}]->(method:Frame {type: 'CALLABLE'})<-[:Edge {type: 'CALLS'}]-(caller1:Frame)<-[:Edge {type: 'CALLS'}]-(caller:Frame)
            RETURN DISTINCT
                caller.name as name,
                caller.qualified_name as qualified_name,
                caller.file_path as file_path,
                caller.start_line as start_line,
                caller.type as type,
                2 as path_length
            LIMIT 50
            """
        else:  # depth == 3
            return """
            MATCH (target:Frame {id: $target_id})-[:Edge {type: 'CONTAINS'}]->(method:Frame {type: 'CALLABLE'})<-[:Edge {type: 'CALLS'}]-(caller1:Frame)<-[:Edge {type: 'CALLS'}]-(caller2:Frame)<-[:Edge {type: 'CALLS'}]-(caller:Frame)
            RETURN DISTINCT
                caller.name as name,
                caller.qualified_name as qualified_name,
                caller.file_path as file_path,
                caller.start_line as start_line,
                caller.type as type,
                3 as path_length
            LIMIT 50
            """

    def _aggregate_affected_files(
        self,
        dependency_tree: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate affected files from dependency tree.

        Args:
            dependency_tree: Dependency tree with depth_N_callers

        Returns:
            List of affected file dicts with methods
        """
        file_map = {}

        for key, callers in dependency_tree.items():
            if not key.startswith("depth_"):
                continue

            for caller in callers:
                file_path = caller["file_path"]
                if file_path not in file_map:
                    file_map[file_path] = {
                        "file_path": file_path,
                        "file_name": Path(file_path).name,
                        "affected_methods": []
                    }

                file_map[file_path]["affected_methods"].append({
                    "name": caller["name"],
                    "qualified_name": caller["qualified_name"],
                    "location": caller["location"],
                    "depth": caller["depth"]
                })

        return list(file_map.values())

    def _assess_risk(
        self,
        target: Dict[str, Any],
        dependency_tree: Dict[str, Any],
        affected_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Assess risk of changing the target element.

        Args:
            target: Target frame data
            dependency_tree: Dependency tree
            affected_files: List of affected files

        Returns:
            Risk assessment dict with scores and tier
        """
        # Count total callers
        total_callers = sum(
            len(callers)
            for key, callers in dependency_tree.items()
            if key.startswith("depth_")
        )

        # Calculate centrality score
        centrality_score = self._calculate_centrality_score(total_callers)

        # Calculate core score
        file_path = target.get("file_path", "")
        core_score = self._calculate_core_score(file_path)

        # Calculate external score
        external_score = min(1.0, len(affected_files) / 10)

        # Coverage score placeholder
        coverage_score = 0.5

        # Calculate composite risk
        composite_score, risk_tier = self._calculate_risk_score(
            centrality_score,
            core_score,
            coverage_score,
            external_score
        )

        return {
            "overall_risk": risk_tier,
            "composite_risk_score": composite_score,
            "risk_factors": [
                {
                    "factor": "Centrality",
                    "score": centrality_score,
                    "explanation": f"Called by {total_callers} different locations"
                },
                {
                    "factor": "Core vs Peripheral",
                    "score": core_score,
                    "explanation": "Based on file path analysis"
                },
                {
                    "factor": "Affected Files",
                    "score": external_score,
                    "explanation": f"{len(affected_files)} files affected"
                }
            ],
            "recommendation": self._get_risk_recommendation(risk_tier)
        }

    def _calculate_centrality_score(self, caller_count: int, max_callers: int = 20) -> float:
        """Calculate centrality score from caller count."""
        return min(1.0, caller_count / max_callers)

    def _calculate_core_score(self, file_path: str) -> float:
        """Calculate core vs peripheral score based on file path."""
        file_path_lower = file_path.lower()

        # Core paths (higher risk)
        core_patterns = ['core', 'base', 'main', 'engine', 'kernel']
        if any(pattern in file_path_lower for pattern in core_patterns):
            return 0.9

        # Infrastructure (medium-high risk)
        infra_patterns = ['db', 'database', 'service', 'manager']
        if any(pattern in file_path_lower for pattern in infra_patterns):
            return 0.7

        # Utils/helpers (medium risk)
        util_patterns = ['util', 'helper', 'tool']
        if any(pattern in file_path_lower for pattern in util_patterns):
            return 0.5

        # Test/example (low risk)
        test_patterns = ['test', 'example', 'demo']
        if any(pattern in file_path_lower for pattern in test_patterns):
            return 0.2

        # Default medium
        return 0.5

    def _calculate_risk_score(
        self,
        centrality_score: float,
        core_score: float,
        coverage_score: float,
        external_score: float,
        weights: Optional[Dict[str, float]] = None
    ) -> Tuple[float, str]:
        """Calculate composite risk score and tier."""
        if weights is None:
            weights = {
                "centrality": 0.35,
                "core": 0.35,
                "coverage": 0.20,
                "external": 0.10
            }

        composite = (
            weights["centrality"] * centrality_score +
            weights["core"] * core_score +
            weights["coverage"] * coverage_score +
            weights["external"] * external_score
        )

        if composite > 0.75:
            tier = "HIGH"
        elif composite > 0.5:
            tier = "MEDIUM-HIGH"
        elif composite > 0.3:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        return round(composite, 2), tier

    def _get_risk_recommendation(self, risk_tier: str) -> str:
        """Get recommendation based on risk tier."""
        recommendations = {
            "HIGH": "HIGH RISK: Proceed with extreme caution. Require thorough testing and code review.",
            "MEDIUM-HIGH": "MEDIUM-HIGH RISK: Significant impact. Ensure comprehensive testing.",
            "MEDIUM": "MEDIUM RISK: Moderate impact. Review affected code and update tests.",
            "LOW": "LOW RISK: Minimal impact. Standard testing should suffice."
        }
        return recommendations.get(risk_tier, "UNKNOWN RISK: Assess carefully.")

    def _estimate_blast_radius(self, file_count: int) -> str:
        """Estimate blast radius from file count."""
        if file_count > 10:
            return "Large - affects many files"
        elif file_count > 5:
            return "Medium - affects several files"
        elif file_count > 1:
            return "Small - affects few files"
        else:
            return "Minimal - single file impact"

    def _generate_recommendations(
        self,
        risk_assessment: Dict[str, Any],
        test_coverage: Dict[str, Any]
    ) -> List[str]:
        """Generate change recommendations based on risk and coverage."""
        recommendations = []

        risk_level = risk_assessment.get("overall_risk", "UNKNOWN")

        # Risk-based recommendations
        if risk_level == "HIGH":
            recommendations.extend([
                "Create comprehensive test suite before changes",
                "Implement feature flags for gradual rollout",
                "Schedule code review with multiple reviewers",
                "Plan rollback strategy before deployment"
            ])
        elif risk_level == "MEDIUM-HIGH":
            recommendations.extend([
                "Ensure affected code paths are tested",
                "Review impact on dependent modules",
                "Consider incremental refactoring approach"
            ])
        elif risk_level == "MEDIUM":
            recommendations.extend([
                "Update existing tests",
                "Review changes with team lead"
            ])
        else:
            recommendations.append("Standard testing and review process")

        return recommendations
