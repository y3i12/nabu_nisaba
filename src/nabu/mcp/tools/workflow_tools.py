"""
Phase 2 workflow automation tools for nabu MCP.

Automates complex multi-step workflows that agents perform repeatedly:
- understand_class_workflow: Comprehensive class understanding in one call
- impact_analysis_workflow: "What will break?" analysis with risk assessment
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import time
import logging

from nabu.mcp.tools.base import NabuTool
from nisaba.tools.base_tool import BaseToolResponse


logger = logging.getLogger(__name__)


class CheckImpactTool(NabuTool):
    """
    Automated impact analysis for code changes.
    
    Traverses dependency graph to find all code affected by changes to a specific
    element. Provides risk assessment and test coverage analysis.
    """
    
    async def execute(
        self,
        target: str,
        max_depth: int = 2,
        risk_assessment: bool = True,
        include_test_coverage: bool = True,
        is_regex: bool = False
    ) -> BaseToolResponse:
        """
        Analyze the impact of changing a specific code element, finding the blast 
        radius of code changes. 

        This workflow traverses the dependency graph to find all code that would
        be affected by changes to the specified element. Essential for safe
        refactoring and understanding blast radius.
        
        Depth Selection:
        - max_depth=1 - Direct dependents only. Fast, use for small changes or initial assessment.
        - max_depth=2 (default) - Extended impact including indirect dependents. Recommended for most refactoring.
        - max_depth=3 - Full traversal. Use for critical components or widespread API changes. Can be slow on large codebases.
        - risk_assessment=True (default) - Enable to get risk scores. Disable only if you just need the dependency list.
        
        :param target: Frame identifier (name, qualified name, or hierarchical path)
        :param max_depth: How many levels deep to traverse (1=direct, 2=extended, 3=full)
        :param risk_assessment: Whether to calculate risk scores
        :param is_regex: Treat target as regex pattern (default False). Set to True for regex matching.
        :return: Comprehensive impact analysis with dependency tree and risk assessment
        """
        start_time = time.time()
        
        try:
            # ========== VALIDATION ==========
            indexing_check = self._check_indexing_status()
            if indexing_check:
                return indexing_check

            if max_depth < 1 or max_depth > 3:
                return self.response_error("max_depth must be between 1 and 3")
            
            logger.info(f"🎯 Starting impact_analysis_workflow: {target} (depth={max_depth})")

            # ========== FRAME RESOLUTION ==========
            target_frames = await self._resolve_frame(target, is_regex=is_regex)

            resolution_metadata = None
            if target_frames and len(target_frames) > 1 and target_frames[0].get('_resolution_strategy') == 'fts_fuzzy':
                alternatives = target_frames[1:3]
                other_matches = [
                    f"{c['file_path']}:{c['qualified_name']}"
                    for c in target_frames[3:]
                ]

                resolution_metadata = {
                    "strategy": "fts_fuzzy",
                    "alternatives": alternatives,
                    "other_matches": other_matches,
                    "total_candidates": len(target_frames)
                }

                target_frames = [target_frames[0]]
                logger.info(f"FTS fuzzy resolution: using '{target_frames[0]['qualified_name']}' with {len(alternatives)} alternatives")

            if not target_frames:
                return self.response_error(f"Target not found: {target}")

            # ========== SINGLE TARGET PATH ==========
            if len(target_frames) == 1:
                target_frame = target_frames[0]

                # Call service
                from nabu.services.impact_service import ImpactRequest
                
                request = ImpactRequest(
                    target_frame_id=target_frame["id"],
                    target_frame_data=target_frame,
                    max_depth=max_depth,
                    risk_assessment=risk_assessment,
                    include_test_coverage=include_test_coverage
                )

                result = await self.impact_service.analyze_impact(request)

                # Format MCP response
                results = {
                    "target": result.target,
                    "dependency_tree": result.dependency_tree,
                    "affected_files": result.affected_files,
                    "impact_summary": result.impact_summary
                }

                if resolution_metadata:
                    results["resolution_metadata"] = resolution_metadata

                if result.risk_assessment:
                    results["risk_assessment"] = result.risk_assessment

                if result.change_recommendations:
                    results["change_recommendations"] = result.change_recommendations

            # ========== MULTIPLE TARGETS PATH ==========
            else:
                logger.info(f"📋 Analyzing {len(target_frames)} targets matching pattern '{target}'")
                
                # Analyze each target
                all_results = []
                for frame in target_frames:
                    from nabu.services.impact_service import ImpactRequest
                    
                    request = ImpactRequest(
                        target_frame_id=frame["id"],
                        target_frame_data=frame,
                        max_depth=max_depth,
                        risk_assessment=risk_assessment,
                        include_test_coverage=include_test_coverage
                    )
                    
                    result = await self.impact_service.analyze_impact(request)
                    all_results.append(result)

                # Aggregate results
                all_affected_files_set = set()
                total_callables = 0
                
                for result in all_results:
                    for file in result.affected_files:
                        all_affected_files_set.add(file["file_path"])
                    total_callables += result.impact_summary["total_affected_callables"]

                results = {
                    "is_regex_match": True,
                    "pattern": target,
                    "match_count": len(target_frames),
                    "targets": target_frames,
                    "target": {
                        "name": f"Multiple targets ({len(target_frames)} matches)",
                        "qualified_name": f"Pattern: {target}",
                        "type": "MULTI_MATCH",
                        "location": f"{len(target_frames)} matches",
                        "file_path": "Multiple files"
                    },
                    "aggregate_summary": {
                        "total_targets_analyzed": len(target_frames),
                        "total_affected_files": len(all_affected_files_set),
                        "total_affected_callables": total_callables,
                        "max_depth": max_depth
                    },
                    "individual_analyses": [
                        {
                            "target_name": r.target["name"],
                            "target_qualified_name": r.target["qualified_name"],
                            "affected_files_count": len(r.affected_files),
                            "risk_level": r.risk_assessment.get("overall_risk") if r.risk_assessment else None
                        }
                        for r in all_results
                    ]
                }

            return self.response_success(results)
            
        except Exception as e:
            logger.error(f"impact_analysis_workflow failed for '{target}': {e}", exc_info=True)
            return self.response_exception(e, "Check impact tool failed")

    def __init__(self, factory):
        super().__init__(factory)
        self._impact_service = None

    @property
    def impact_service(self):
        """Lazy-initialize impact analysis service."""
        if self._impact_service is None:
            from nabu.services.impact_service import ImpactAnalysisService
            self._impact_service = ImpactAnalysisService(self.db_manager)
        return self._impact_service
