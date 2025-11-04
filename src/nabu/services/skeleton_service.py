"""
Skeleton generation service.

Handles orchestration of skeleton building, relationship gathering,
and metrics calculation independent of MCP layer.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import logging

from nabu.services.base import BaseService
from nabu.core.skeleton_builder import SkeletonBuilder, SkeletonOptions
from nabu.language_handlers.formatters import formatter_registry

logger = logging.getLogger(__name__)


@dataclass
class SkeletonRequest:
    """Request parameters for skeleton generation."""
    target_frame_data: Dict[str, Any]
    detail_level: str = "minimal"
    structure_detail_depth: int = 1
    include_docstrings: bool = False
    include_private: bool = True
    max_recursion_depth: int = 1
    include_relationships: bool = False
    include_metrics: bool = False
    max_callers: int = 10


@dataclass
class SkeletonResult:
    """Domain result from skeleton generation."""
    skeleton: str
    metadata: Dict[str, Any]
    relationships: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


class SkeletonService(BaseService):
    """
    Service for generating frame skeletons.

    Handles orchestration of skeleton building, relationship gathering,
    and metrics calculation independent of MCP layer.
    """

    def __init__(self, db_manager):
        super().__init__(db_manager)
        self._builder = None

    @property
    def builder(self):
        """Lazy-initialize skeleton builder."""
        if self._builder is None:
            from nabu.core.skeleton_builder import SkeletonBuilder
            self._builder = SkeletonBuilder(self.db_manager)
        return self._builder

    async def generate_skeleton(self, request: SkeletonRequest) -> SkeletonResult:
        """
        Generate skeleton for a frame with optional relationships and metrics.

        Args:
            request: SkeletonRequest with all parameters

        Returns:
            SkeletonResult with skeleton string and metadata

        Raises:
            ValueError: If frame data invalid or formatter not found
        """
        frame_data = request.target_frame_data
        frame_type = frame_data.get("type")
        language = frame_data.get("language")

        # Validate language support
        if not language:
            raise ValueError(f"Frame has no language information")

        formatter = formatter_registry.get_formatter(language)
        if formatter is None:
            supported = formatter_registry.get_supported_languages()
            raise ValueError(
                f"Language '{language}' not supported for skeleton generation. "
                f"Supported: {', '.join(supported)}"
            )

        # Build skeleton options
        options = SkeletonOptions(
            detail_level=request.detail_level,
            include_docstrings=request.include_docstrings,
            structure_detail_depth=request.structure_detail_depth
        )

        # Generate skeleton
        skeleton_result = await self.builder.build_recursive_skeleton(
            frame_data=frame_data,
            options=options,
            current_depth=0,
            max_recursion_depth=request.max_recursion_depth,
            include_private=request.include_private
        )

        # Build metadata
        skeleton = skeleton_result["skeleton"]
        estimated_tokens = len(skeleton) // 4  # Rough estimate
        children_count = len(skeleton_result.get("children", []))

        metadata = {
            "frame_type": frame_type,
            "name": frame_data["name"],
            "qualified_name": frame_data["qualified_name"],
            "file_path": frame_data["file_path"],
            "location": frame_data["location"],
            "language": language,
            "detail_level": request.detail_level,
            "recursion_depth": request.max_recursion_depth,
            "children_count": children_count,
            "estimated_tokens": estimated_tokens
        }

        # Gather relationships if requested (CLASS frames only)
        relationships = None
        if request.include_relationships and frame_type == "CLASS":
            relationships = await self._gather_relationships(
                frame_data,
                request.max_callers
            )

        # Calculate metrics if requested (CLASS frames only)
        metrics = None
        if request.include_metrics and frame_type == "CLASS":
            metrics = await self._calculate_metrics(
                frame_data,
                relationships
            )

        return SkeletonResult(
            skeleton=skeleton,
            metadata=metadata,
            relationships=relationships,
            metrics=metrics
        )

    async def generate_multi_skeleton(
        self,
        frame_data_list: List[Dict[str, Any]],
        detail_level: str = "minimal",
        structure_detail_depth: int = 1,
        include_docstrings: bool = False,
        include_private: bool = True,
        max_recursion_depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Generate skeletons for multiple frames.

        Args:
            frame_data_list: List of frame data dicts
            detail_level: Skeleton detail level
            structure_detail_depth: Control flow nesting depth
            include_docstrings: Whether to include docstrings
            include_private: Whether to include private members
            max_recursion_depth: Maximum recursion depth

        Returns:
            List of skeleton dicts with metadata
        """
        all_skeletons = []

        for frame_data in frame_data_list:
            frame_type = frame_data.get("type")
            language = frame_data.get("language")

            if not language:
                logger.warning(
                    f"Skipping frame {frame_data.get('qualified_name')} "
                    f"- no language information"
                )
                continue

            formatter = formatter_registry.get_formatter(language)
            if not formatter:
                logger.warning(
                    f"Skipping frame {frame_data.get('qualified_name')} "
                    f"- language '{language}' not supported"
                )
                continue

            # Build skeleton for this frame
            options = SkeletonOptions(
                detail_level=detail_level,
                include_docstrings=include_docstrings,
                structure_detail_depth=structure_detail_depth
            )

            skeleton_result = await self.builder.build_recursive_skeleton(
                frame_data=frame_data,
                options=options,
                current_depth=0,
                max_recursion_depth=max_recursion_depth,
                include_private=include_private
            )

            all_skeletons.append({
                "name": frame_data["name"],
                "qualified_name": frame_data["qualified_name"],
                "type": frame_type,
                "location": frame_data["location"],
                "language": language,
                "skeleton": skeleton_result["skeleton"]
            })

        return all_skeletons

    async def _gather_relationships(
        self,
        frame_data: Dict[str, Any],
        max_callers: int
    ) -> Dict[str, Any]:
        """
        Gather inheritance, callers, dependencies for a CLASS frame.

        Args:
            frame_data: Frame data dict with 'id' field
            max_callers: Maximum number of callers to return

        Returns:
            Dict with inheritance, called_by, dependencies
        """
        class_id = frame_data['id']
        relationships = {}

        # Get inheritance relationships
        inheritance_query = """
        MATCH (c:Frame {id: $class_id})
        OPTIONAL MATCH (c)-[:Edge {type: 'INHERITS'}]->(parent:Frame)
        OPTIONAL MATCH (child:Frame)-[:Edge {type: 'INHERITS'}]->(c)
        RETURN
            collect(DISTINCT {
                name: parent.name,
                qualified_name: parent.qualified_name,
                file_path: parent.file_path
            }) as parents,
            collect(DISTINCT {
                name: child.name,
                qualified_name: child.qualified_name,
                file_path: child.file_path,
                start_line: child.start_line,
                end_line: child.end_line
            }) as children
        """
        inheritance_result = self.db_manager.execute(
            inheritance_query,
            {"class_id": class_id}
        )
        inheritance_df = inheritance_result.get_as_df()

        inheritance_data = {"parents": [], "children": []}
        if not inheritance_df.empty:
            parents = inheritance_df.iloc[0]['parents']
            children = inheritance_df.iloc[0]['children']

            for p in parents:
                if p['name']:  # Filter out nulls
                    inheritance_data["parents"].append({
                        "name": p['name'],
                        "qualified_name": p['qualified_name'],
                        "file_path": p['file_path']
                    })

            for c in children:
                if c['name']:  # Filter out nulls
                    inheritance_data["children"].append({
                        "name": c['name'],
                        "qualified_name": c['qualified_name'],
                        "location": f"{Path(c['file_path']).name}:{c['start_line']}-{c['end_line']}"
                    })

        relationships["inheritance"] = inheritance_data

        # Get callers
        callers_query = """
        MATCH (c:Frame {id: $class_id})-[:Edge {type: 'CONTAINS'}]->(m:Frame {type: 'CALLABLE'})<-[e:Edge {type: 'CALLS'}]-(caller:Frame)
        RETURN
            caller.name,
            caller.qualified_name,
            caller.file_path,
            caller.start_line,
            e.confidence,
            m.name as called_method
        ORDER BY e.confidence DESC
        LIMIT $max_callers
        """
        callers_result = self.db_manager.execute(callers_query, {
            "class_id": class_id,
            "max_callers": max_callers
        })
        callers_df = callers_result.get_as_df()

        callers = []
        for _, row in callers_df.iterrows():
            callers.append({
                "caller_name": row['caller.name'],
                "caller_qualified_name": row['caller.qualified_name'],
                "location": f"{Path(row['caller.file_path']).name}:{row['caller.start_line']}",
                "confidence": float(row['e.confidence']),
                "called_method": row['called_method']
            })

        relationships["called_by"] = callers

        # Get dependencies
        deps_query = """
        MATCH (c:Frame {id: $class_id})-[e:Edge]->(dep:Frame)
        WHERE e.type IN ['CALLS', 'USES', 'IMPORTS']
        RETURN
            dep.name,
            dep.qualified_name,
            dep.type,
            dep.file_path,
            e.type as edge_type
        LIMIT 20
        """
        deps_result = self.db_manager.execute(deps_query, {"class_id": class_id})
        deps_df = deps_result.get_as_df()

        dependencies = []
        for _, row in deps_df.iterrows():
            dependencies.append({
                "name": row['dep.name'],
                "qualified_name": row['dep.qualified_name'],
                "type": row['dep.type'],
                "relationship": row['edge_type'],
                "file_path": row['dep.file_path']
            })

        relationships["dependencies"] = dependencies

        return relationships

    async def _calculate_metrics(
        self,
        frame_data: Dict[str, Any],
        relationships: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate complexity metrics for a CLASS frame.

        Args:
            frame_data: Frame data dict with 'id' and field info
            relationships: Optional relationships data (if already gathered)

        Returns:
            Dict with method counts, field counts, complexity rating
        """
        class_id = frame_data['id']
        language = frame_data.get('language', 'python')

        # Get full frame details from database
        frame_query = """
        MATCH (f:Frame {id: $frame_id})
        RETURN f.name, f.qualified_name, f.file_path, f.start_line, f.end_line,
               f.instance_fields, f.static_fields
        """
        frame_result = self.db_manager.execute(frame_query, {"frame_id": class_id})
        frame_df = frame_result.get_as_df()

        if frame_df.empty:
            # Fallback to basic info from frame_data
            instance_fields = []
            static_fields = []
        else:
            row = frame_df.iloc[0]
            instance_fields = row.get('f.instance_fields', []) or []
            static_fields = row.get('f.static_fields', []) or []

        # Get method count
        methods_query = """
        MATCH (c:Frame {id: $class_id})-[:Edge {type: 'CONTAINS'}]->(m:Frame {type: 'CALLABLE'})
        RETURN count(m) as method_count
        """
        methods_result = self.db_manager.execute(methods_query, {"class_id": class_id})
        methods_df = methods_result.get_as_df()
        method_count = int(methods_df.iloc[0]['method_count']) if not methods_df.empty else 0

        # Get caller and dependency counts (from relationships if available)
        if relationships:
            caller_count = len(relationships.get("called_by", []))
            dep_count = len(relationships.get("dependencies", []))
            parent_count = len(relationships.get("inheritance", {}).get("parents", []))
            child_count = len(relationships.get("inheritance", {}).get("children", []))
        else:
            caller_count = 0
            dep_count = 0
            parent_count = 0
            child_count = 0

        # Calculate complexity rating
        complexity_rating = self._calculate_complexity_rating(
            method_count,
            caller_count,
            dep_count
        )

        return {
            "method_count": method_count,
            "instance_field_count": len(instance_fields),
            "static_field_count": len(static_fields),
            "parent_count": parent_count,
            "child_count": child_count,
            "caller_count": caller_count,
            "dependency_count": dep_count,
            "complexity_rating": complexity_rating
        }

    def _calculate_complexity_rating(
        self,
        method_count: int,
        caller_count: int,
        dep_count: int
    ) -> str:
        """
        Calculate complexity rating based on metrics.

        Args:
            method_count: Number of methods in class
            caller_count: Number of callers
            dep_count: Number of dependencies

        Returns:
            Complexity rating string (LOW, MEDIUM, HIGH, VERY HIGH)
        """
        # Weighted complexity score
        complexity_score = (
            method_count * 0.4 +      # Methods contribute most
            caller_count * 0.3 +       # Callers indicate coupling
            dep_count * 0.3            # Dependencies indicate complexity
        )

        if complexity_score > 50:
            return "VERY HIGH"
        elif complexity_score > 25:
            return "HIGH"
        elif complexity_score > 10:
            return "MEDIUM"
        else:
            return "LOW"
