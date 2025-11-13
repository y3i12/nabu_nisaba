"""
Frame skeleton tools for nabu.

Provides tools to generate skeleton/summary views for any frame type (CLASS, CALLABLE, PACKAGE)
with support for hierarchical name matching and recursive skeleton generation.
"""

import logging
import time

from nabu.mcp.tools.base import NabuTool
from nisaba.tools.base_tool import BaseToolResponse

logger = logging.getLogger(__name__)


class ShowStructureTool(NabuTool):
    """
    Tool for generating skeleton/summary view of any frame type.

    Works with CLASS, CALLABLE, and PACKAGE frames using hierarchical name matching.
    Supports recursive skeleton generation to show package contents.
    """

    async def execute(
        self,
        target: str,
        detail_level: str = "minimal",
        structure_detail_depth: int = 1,
        include_docstrings: bool = False,
        include_private: bool = True,
        max_recursion_depth: int = 1,
        include_relationships: bool = False,
        include_metrics: bool = False,
        max_callers: int = 10,
        is_regex: bool = False
    ) -> BaseToolResponse:
        """
        Get skeleton view of frame (CLASS, CALLABLE, or PACKAGE) with configurable detail.

        Supports hierarchical name matching similar to serena's find_symbol:
        - Simple name: "MyClass" matches any frame with that name
        - Hierarchical path: "utils/MyClass" or "MyClass/my_method"
        - Qualified name: "nabu.mcp.utils.extract_snippets"

        For PACKAGE frames, recursively generates skeletons for contained classes and functions.
        For CLASS frames, shows class structure with methods.
        For CALLABLE frames, shows function/method signature with control flow.

        Detail levels:
        - **minimal**: Just signatures (default) - cleanest, most token-efficient
        - **guards**: Include top-level guards & validation - shows behavioral hints
        - **structure**: Include all control flow - comprehensive structure view

        Relationship features (for CLASS frames only):
        - **include_relationships=True**: Add inheritance, callers, and dependencies
        - **include_metrics=True**: Add complexity metrics and analysis
        - **max_callers**: Control number of calling sites returned (default 10)

        :meta pitch: Get frame skeleton + optional relationships. Progressive disclosure: start simple, add relationships as needed.
        :meta when: Understanding packages, classes, or functions. Use include_relationships for comprehensive class analysis.
        :meta emoji: 🔍
        :meta tips: **Usage Tips:**
            - Start with simple skeleton: show_structure(target="MyClass")
            - Add relationships when needed: include_relationships=True
            - Use max_recursion_depth=0 to see only the target frame
            - Use max_recursion_depth=1 to see target + immediate children
            - Query packages to see all contained classes and functions at once
        :meta examples: **Common Usage Patterns:**

            Simple skeleton (fast, token-efficient):
            ```python
            show_structure(target="MyClass")
            ```
            Comprehensive class analysis:
            ```python
            show_structure(target="MyClass", include_relationships=True, include_metrics=True)
            ```
            Query a package to see all its contents:
            ```python
            show_structure(target="nabu.mcp.utils", max_recursion_depth=1)
            ```
        :param target: Hierarchical path to frame (e.g., "MyClass", "utils/MyClass", "MyClass/my_method")
        :param detail_level: Detail level - "minimal", "guards", or "structure"
        :param structure_detail_depth: How deep to include control flow nesting (ONLY applies when detail_level="structure")
        :param include_docstrings: Whether to include docstrings in output
        :param include_private: Whether to include private methods/fields (names starting with _)
        :param max_recursion_depth: Maximum depth for recursive skeleton generation (0-3, default 1)
        :param include_relationships: Whether to include inheritance, callers, dependencies (CLASS frames only)
        :param include_metrics: Whether to include complexity metrics (CLASS frames only)
        :param max_callers: Maximum number of calling sites to return (default 10)
        :param is_regex: Treat target as regex pattern (default False). Set to True for regex matching.
        :return: Dict with skeleton and optional relationship/metric data
        """
        start_time = time.time()

        try:
            # ========== STEP 1: VALIDATION (MCP CONCERN) ==========
            indexing_check = self._check_indexing_status()
            if indexing_check:
                return indexing_check

            valid_levels = ["minimal", "guards", "structure"]
            if detail_level not in valid_levels:
                return self.response_error(f"Invalid detail_level: {detail_level}. Must be one of: {valid_levels}")

            if max_recursion_depth < 0 or max_recursion_depth > 3:
                return self.response_error(f"Invalid max_recursion_depth: {max_recursion_depth}. Must be between 0 and 3.")

            if self.db_manager is None:
                return self.response_error("Database manager not initialized")

            # ========== STEP 2: FRAME RESOLUTION (MCP CONCERN) ==========
            supported_types_filter = "CLASS|CALLABLE|PACKAGE"
            all_matches = await self._resolve_frame(
                target,
                is_regex=is_regex,
                frame_type=supported_types_filter
            )

            # Handle FTS fuzzy resolution metadata
            resolution_metadata = None
            if all_matches and len(all_matches) > 1 and all_matches[0].get('_resolution_strategy') == 'fts_fuzzy':
                alternatives = all_matches[1:3]
                other_matches = [
                    f"{c['file_path']}:{c['qualified_name']}"
                    for c in all_matches[3:]
                ]

                resolution_metadata = {
                    "strategy": "fts_fuzzy",
                    "alternatives": alternatives,
                    "other_matches": other_matches,
                    "total_candidates": len(all_matches)
                }

                all_matches = [all_matches[0]]
                logger.info(f"FTS fuzzy resolution: using '{all_matches[0]['qualified_name']}' with {len(alternatives)} alternatives")

            # Filter to supported frame types
            supported_types = {'CLASS', 'CALLABLE', 'PACKAGE'}
            frame_matches = [f for f in all_matches if f['type'] in supported_types]

            if all_matches and not frame_matches:
                unsupported_types = {f['type'] for f in all_matches}
                logger.warning(f"Pattern '{target}' matched {len(all_matches)} frames but all are unsupported types: {unsupported_types}")

                return self.response_error(f"Frame not found: {target}")

            # ========== SINGLE MATCH PATH ==========
            if len(frame_matches) == 1:
                frame_data = frame_matches[0]

                # Validate language support (could be in service, but keeping MCP concerns here)
                if not frame_data.get("language"):
                    return self.response_error(f"Frame has no language information: {target}")

                # Call service (business logic extracted)
                from nabu.services.skeleton_service import SkeletonRequest

                request = SkeletonRequest(
                    target_frame_data=frame_data,
                    detail_level=detail_level,
                    structure_detail_depth=structure_detail_depth,
                    include_docstrings=include_docstrings,
                    include_private=include_private,
                    max_recursion_depth=max_recursion_depth,
                    include_relationships=include_relationships,
                    include_metrics=include_metrics,
                    max_callers=max_callers
                )

                result = await self.skeleton_service.generate_skeleton(request)

                # Format MCP response
                data = {
                    "skeleton": result.skeleton,
                    **result.metadata
                }

                if resolution_metadata:
                    data["resolution_metadata"] = resolution_metadata

                if result.relationships:
                    data.update(result.relationships)

                if result.metrics:
                    data["metrics"] = result.metrics

            # ========== MULTIPLE MATCHES PATH (REGEX) ==========
            else:
                logger.info(f"📋 Generating skeletons for {len(frame_matches)} frames matching pattern '{target}'")

                # Call service for multi-skeleton generation
                all_skeletons = await self.skeleton_service.generate_multi_skeleton(
                    frame_data_list=frame_matches,
                    detail_level=detail_level,
                    structure_detail_depth=structure_detail_depth,
                    include_docstrings=include_docstrings,
                    include_private=include_private,
                    max_recursion_depth=max_recursion_depth
                )

                # Format multi-match response
                total_tokens = sum(len(s["skeleton"]) // 4 for s in all_skeletons)
                data = {
                    "is_regex_match": True,
                    "pattern": target,
                    "match_count": len(frame_matches),
                    "generated_count": len(all_skeletons),
                    "structures": all_skeletons,
                    "frame_type": "MULTI_MATCH",
                    "name": f"Multiple matches ({len(all_skeletons)} structures)",
                    "qualified_name": f"Pattern: {target}",
                    "file_path": "Multiple files",
                    "location": f"{len(all_skeletons)} matches",
                    "language": "multi-language" if len(set(s['language'] for s in all_skeletons)) > 1 else all_skeletons[0]['language'] if all_skeletons else "unknown",
                    "detail_level": detail_level,
                    "recursion_depth": max_recursion_depth,
                    "children_count": 0,
                    "estimated_tokens": total_tokens
                }

            return self.response_success(data)

        except ValueError as e:
            # Catch service-level validation errors
            return self.response_exception(e, "Error showing structure")

    def __init__(self, factory):
        super().__init__(factory)
        self._skeleton_service = None

    @property
    def skeleton_service(self):
        """Lazy-initialize skeleton service."""
        if self._skeleton_service is None:
            from nabu.services.skeleton_service import SkeletonService
            self._skeleton_service = SkeletonService(self.db_manager)
        return self._skeleton_service









