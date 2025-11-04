"""
Core Skeleton Generation

Provides clean interface for generating frame skeletons using language formatters.
Separates formatting logic from database/recursion concerns.

Usage:
    # Simple skeleton generation (no database)
    formatter = SkeletonFormatter()
    skeleton = formatter.build_show_structure(frame_data, options)

    # Advanced with database and recursion
    builder = SkeletonBuilder(db_manager)
    skeleton_result = await builder.build_recursive_skeleton(frame_data, options)
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _get_formatter_registry():
    """Lazy import to avoid circular dependency."""
    from nabu.language_handlers.formatters import formatter_registry
    return formatter_registry


@dataclass
class SkeletonOptions:
    """Configuration for skeleton generation."""
    detail_level: str = "minimal"  # "minimal", "guards", "structure"
    include_docstrings: bool = False
    structure_detail_depth: int = 1  # Only applies when detail_level="structure"


class SkeletonFormatter:
    """
    Simple skeleton generation using language formatters.

    No database access, no recursion - just clean skeleton formatting.
    Perfect for embedding generation and simple use cases.
    """

    def build_show_structure(
        self,
        frame_data: Dict[str, Any],
        options: Optional[SkeletonOptions] = None,
        control_flows: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """
        Generate skeleton for a single frame.

        Args:
            frame_data: Frame metadata (type, name, parameters, content, etc.)
            options: Skeleton generation options
            control_flows: Optional control flow data for detail_level != "minimal"

        Returns:
            Formatted skeleton string or None if generation fails
        """
        if options is None:
            options = SkeletonOptions()

        frame_type = frame_data.get('type')
        language = frame_data.get('language', 'python')

        # Get formatter for language
        formatter_registry = _get_formatter_registry()
        formatter = formatter_registry.get_formatter(language)
        if not formatter:
            logger.warning(f"No formatter for language: {language}")
            return None

        # Only generate skeletons for structural frames
        if frame_type not in ['CLASS', 'CALLABLE', 'PACKAGE']:
            return None

        # Prepare control flows dict (formatter expects dict, not list)
        control_flows_dict = {}
        if control_flows and frame_type in ['CALLABLE', 'PACKAGE']:
            frame_id = frame_data.get('id', '')
            if frame_id:
                control_flows_dict[frame_id] = control_flows

        try:
            skeleton = formatter.format_show_structure(
                frame_data=frame_data,
                children=[],
                children_skeletons=[],
                control_flows=control_flows_dict,
                detail_level=options.detail_level,
                include_docstrings=options.include_docstrings,
                recursive=False
            )
            return skeleton
        except Exception as e:
            logger.error(f"Skeleton generation failed for {frame_data.get('qualified_name')}: {e}")
            return None


def _extract_control_flows_from_ast(
    frame: 'AstFrameBase',
    max_depth: int = 1
) -> List[Dict[str, Any]]:
    """
    Extract control flows from AST frame tree (no DB queries).
    
    Returns same format as get_control_flow() for formatter compatibility.
    
    Args:
        frame: AstFrame with children loaded
        max_depth: Maximum depth for control flow traversal (1-3)
    
    Returns:
        List of control flow dicts with keys: type, content, start_line
    """
    from nabu.core.frame_types import FrameNodeType
    
    # Get control flow types using existing class method
    cf_types = FrameNodeType.control_flow_types()
    
    control_flows = []
    
    def collect_recursive(current_frame: 'AstFrameBase', current_depth: int):
        """Recursively collect control flow frames."""
        if current_depth > max_depth:
            return
        
        for child in current_frame.children:
            if child.type in cf_types:
                control_flows.append({
                    'type': child.type.value,
                    'content': child.content or '',
                    'start_line': child.start_line
                })
                
                # Recurse into nested control flow
                if current_depth < max_depth:
                    collect_recursive(child, current_depth + 1)
    
    collect_recursive(frame, 1)
    
    # Sort by line number (same as DB mode)
    control_flows.sort(key=lambda x: x['start_line'])
    return control_flows


class SkeletonBuilder:
    """
    Advanced skeleton building with database access and recursion.

    Supports:
    - Frame lookup by name path
    - Recursive skeleton generation
    - Control flow extraction
    - Children traversal

    Used by ShowStructureTool for complex skeleton generation.
    """

    def __init__(self, db_manager):
        """
        Initialize with database manager.

        Args:
            db_manager: KuzuConnectionManager instance
        """
        self.db_manager = db_manager
        self.formatter_helper = SkeletonFormatter()

    async def find_frame(self, name_path: str) -> Optional[Dict[str, Any]]:
        """
        Find frame by hierarchical name path with intelligent matching.

        Supports:
        - Simple name: "MyClass" -> matches any frame with that name
        - Partial qualified: "utils/MyClass" -> matches hierarchy
        - Full qualified: "nabu.mcp.utils.MyClass" -> exact match

        Args:
            name_path: Hierarchical path

        Returns:
            Frame data dict or None if not found
        """
        # Parse name_path - convert / to . for qualified name matching
        normalized_path = name_path.replace('/', '.')

        find_query = """
        MATCH (f:Frame)
        WHERE f.name = $name_path
           OR f.qualified_name = $normalized_path
           OR f.qualified_name CONTAINS $normalized_path
           OR f.name CONTAINS $name_path
        RETURN f.id as id, f.type as type, f.name as name, f.qualified_name as qualified_name,
               f.file_path as file_path, f.start_line as start_line, f.end_line as end_line,
               f.language as language, f.instance_fields as instance_fields,
               f.static_fields as static_fields, f.content as content,
               f.parameters as parameters, f.return_type as return_type
        ORDER BY
            CASE
                WHEN f.qualified_name = $normalized_path THEN 0
                WHEN f.name = $name_path THEN 1
                WHEN f.qualified_name CONTAINS $normalized_path THEN 2
                ELSE 3
            END
        LIMIT 1
        """
        result = self.db_manager.execute(find_query, {
            "name_path": name_path,
            "normalized_path": normalized_path
        })
        df = result.get_as_df()

        if df.empty:
            return None

        row = df.iloc[0]
        return {
            "id": row['id'],
            "type": row['type'],
            "name": row['name'],
            "qualified_name": row['qualified_name'],
            "file_path": row['file_path'],
            "location": f"{Path(row['file_path']).name}:{int(row['start_line'])}-{int(row['end_line'])}",
            "language": row.get('language', ''),
            "instance_fields": row.get('instance_fields', []) or [],
            "static_fields": row.get('static_fields', []) or [],
            "content": row.get('content', ''),
            "parameters": row.get('parameters', []) or [],
            "return_type": row.get('return_type', '')
        }

    async def get_frame_children(
        self,
        frame_id: str,
        frame_type: str,
        include_private: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get children frames for recursive skeleton generation.

        For PACKAGE: returns CLASS and CALLABLE children
        For CLASS: returns CALLABLE children (methods)
        For CALLABLE: returns control flow only (handled separately)

        Args:
            frame_id: Frame ID
            frame_type: "PACKAGE", "CLASS", or "CALLABLE"
            include_private: Whether to include private members

        Returns:
            List of child frame dicts
        """
        if frame_type == "PACKAGE":
            # Get classes and top-level callables
            children_query = """
            MATCH (p:Frame {id: $frame_id})-[:Edge {type: 'CONTAINS'}]->(child:Frame)
            WHERE child.type IN ['CLASS', 'CALLABLE']
            RETURN child.id as id, child.type as type, child.name as name,
                   child.qualified_name as qualified_name, child.file_path as file_path,
                   child.start_line as start_line, child.end_line as end_line,
                   child.language as language, child.content as content,
                   child.parameters as parameters, child.return_type as return_type,
                   child.instance_fields as instance_fields, child.static_fields as static_fields
            ORDER BY child.start_line
            """
        elif frame_type == "CLASS":
            # Get methods
            children_query = """
            MATCH (c:Frame {id: $frame_id})-[:Edge {type: 'CONTAINS'}]->(child:Frame)
            WHERE child.type = 'CALLABLE'
            RETURN child.id as id, child.type as type, child.name as name,
                   child.qualified_name as qualified_name, child.file_path as file_path,
                   child.start_line as start_line, child.end_line as end_line,
                   child.language as language, child.content as content,
                   child.parameters as parameters, child.return_type as return_type
            ORDER BY child.start_line
            """
        else:
            # CALLABLE or other types don't have structural children we care about
            return []

        result = self.db_manager.execute(children_query, {"frame_id": frame_id})
        df = result.get_as_df()

        children = []
        for _, row in df.iterrows():
            name = row['name']

            # Skip private items if requested
            if not include_private and name.startswith('_') and not name.startswith('__'):
                continue

            children.append({
                "id": row['id'],
                "type": row['type'],
                "name": name,
                "qualified_name": row['qualified_name'],
                "file_path": row.get('file_path', ''),
                "location": f"{Path(row.get('file_path', '')).name}:{int(row.get('start_line', 0))}-{int(row.get('end_line', 0))}",
                "language": row.get('language', ''),
                "content": row.get('content', ''),
                "parameters": row.get('parameters', []) or [],
                "return_type": row.get('return_type', ''),
                "instance_fields": row.get('instance_fields', []) or [],
                "static_fields": row.get('static_fields', []) or []
            })

        return children

    async def get_control_flow(
        self,
        frame_id: str,
        max_depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get control flow frames for a frame (CALLABLE or PACKAGE).

        Args:
            frame_id: Frame ID
            max_depth: Maximum depth for control flow traversal (1-3)

        Returns:
            List of control flow frame dicts
        """
        # Control flow types we want to capture
        cf_types = [
            'IF_BLOCK', 'ELIF_BLOCK', 'ELSE_BLOCK',
            'TRY_BLOCK', 'EXCEPT_BLOCK', 'FINALLY_BLOCK',
            'FOR_LOOP', 'WHILE_LOOP',
            'WITH_BLOCK', 'SWITCH_BLOCK', 'CASE_BLOCK'
        ]

        # Build query with depth tracking using UNION
        # Each branch adds a nesting_depth constant to track hierarchy
        if max_depth == 1:
            cf_query = """
            MATCH (m:Frame {id: $frame_id})-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
            WHERE cf.type IN $cf_types
            RETURN
                cf.id as id,
                cf.type as type,
                cf.heading as heading,
                cf.start_line as start_line,
                cf.end_line as end_line,
                1 as nesting_depth
            ORDER BY cf.start_line
            """
        elif max_depth == 2:
            cf_query = """
            MATCH (m:Frame {id: $frame_id})-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
            WHERE cf.type IN $cf_types
            RETURN
                cf.id as id,
                cf.type as type,
                cf.heading as heading,
                cf.start_line as start_line,
                cf.end_line as end_line,
                1 as nesting_depth
            UNION
            MATCH (m:Frame {id: $frame_id})-[:Edge {type: 'CONTAINS'}]->()-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
            WHERE cf.type IN $cf_types
            RETURN
                cf.id as id,
                cf.type as type,
                cf.heading as heading,
                cf.start_line as start_line,
                cf.end_line as end_line,
                2 as nesting_depth
            ORDER BY start_line
            """
        else:
            # max_depth >= 3
            cf_query = """
            MATCH (m:Frame {id: $frame_id})-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
            WHERE cf.type IN $cf_types
            RETURN
                cf.id as id,
                cf.type as type,
                cf.heading as heading,
                cf.start_line as start_line,
                cf.end_line as end_line,
                1 as nesting_depth
            UNION
            MATCH (m:Frame {id: $frame_id})-[:Edge {type: 'CONTAINS'}]->()-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
            WHERE cf.type IN $cf_types
            RETURN
                cf.id as id,
                cf.type as type,
                cf.heading as heading,
                cf.start_line as start_line,
                cf.end_line as end_line,
                2 as nesting_depth
            UNION
            MATCH (m:Frame {id: $frame_id})-[:Edge {type: 'CONTAINS'}]->()-[:Edge {type: 'CONTAINS'}]->()-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
            WHERE cf.type IN $cf_types
            RETURN
                cf.id as id,
                cf.type as type,
                cf.heading as heading,
                cf.start_line as start_line,
                cf.end_line as end_line,
                3 as nesting_depth
            ORDER BY start_line
            """

        result = self.db_manager.execute(cf_query, {
            "frame_id": frame_id,
            "cf_types": cf_types
        })
        df = result.get_as_df()

        # Import pandas for NaN checking (local import to avoid top-level dependency)
        import pandas as pd

        control_flows = []
        for _, row in df.iterrows():
            # Handle heading which might be NaN/None from database
            # Pandas converts NULL to NaN (a float), which causes .strip() to fail in formatters
            heading_val = row['heading']
            if pd.isna(heading_val):
                heading_str = ""
            else:
                heading_str = str(heading_val)

            control_flows.append({
                "type": row['type'],
                "heading": heading_str,
                "start_line": int(row['start_line']),
                "nesting_depth": int(row['nesting_depth'])
            })

        return control_flows

    async def build_recursive_skeleton(
        self,
        frame_data: Dict[str, Any],
        options: SkeletonOptions,
        current_depth: int = 0,
        max_recursion_depth: int = 1,
        include_private: bool = True
    ) -> Dict[str, Any]:
        """
        Recursively build skeleton for frame and its children.

        Args:
            frame_data: Frame metadata
            options: Skeleton generation options
            current_depth: Current recursion depth (internal)
            max_recursion_depth: Maximum depth to recurse
            include_private: Whether to include private members

        Returns:
            Dict with:
                - "frame_type": Frame type
                - "skeleton": Formatted skeleton string
                - "children": List of child skeleton dicts
                - "metadata": Frame metadata
        """
        frame_id = frame_data["id"]
        frame_type = frame_data["type"]
        language = frame_data["language"]

        # Get formatter for this language
        formatter_registry = _get_formatter_registry()
        formatter = formatter_registry.get_formatter(language)
        if not formatter:
            raise ValueError(f"No formatter for language: {language}")

        # Base case: depth limit reached or not a structural frame
        if current_depth >= max_recursion_depth or frame_type not in ["CLASS", "CALLABLE", "PACKAGE"]:
            # Get control flows if needed
            control_flows = {}
            if options.detail_level in ["guards", "structure"] and frame_type in ["CALLABLE", "PACKAGE"]:
                depth = 1 if options.detail_level == "guards" else options.structure_detail_depth
                control_flows[frame_id] = await self.get_control_flow(frame_id, depth)

            # Generate skeleton without recursion
            skeleton = formatter.format_show_structure(
                frame_data=frame_data,
                children=[],
                children_skeletons=[],
                control_flows=control_flows,
                detail_level=options.detail_level,
                include_docstrings=options.include_docstrings,
                recursive=False
            )

            return {
                "frame_type": frame_type,
                "skeleton": skeleton,
                "children": [],
                "metadata": {
                    "name": frame_data["name"],
                    "qualified_name": frame_data["qualified_name"]
                }
            }

        # Recursive case: get children and build their skeletons
        children_frames = await self.get_frame_children(frame_id, frame_type, include_private)

        children_skeletons = []
        for child_frame in children_frames:
            # Recursively build child skeleton
            if child_frame["type"] in ['CLASS', 'CALLABLE', 'PACKAGE']:
                child_skeleton = await self.build_recursive_skeleton(
                    frame_data=child_frame,
                    options=options,
                    current_depth=current_depth + 1,
                    max_recursion_depth=max_recursion_depth,
                    include_private=include_private
                )
                children_skeletons.append(child_skeleton)

        # Get control flows if needed
        control_flows = {}
        if options.detail_level in ["guards", "structure"]:
            depth = 1 if options.detail_level == "guards" else options.structure_detail_depth

            # For CLASS: get control flow for each method
            if frame_type == "CLASS":
                for child in children_frames:
                    if child["type"] == "CALLABLE":
                        control_flows[child["id"]] = await self.get_control_flow(child["id"], depth)
            # For CALLABLE or PACKAGE: get direct control flow
            elif frame_type in ["CALLABLE", "PACKAGE"]:
                control_flows[frame_id] = await self.get_control_flow(frame_id, depth)

        # Generate skeleton using formatter
        skeleton = formatter.format_show_structure(
            frame_data=frame_data,
            children=children_frames,
            children_skeletons=children_skeletons,
            control_flows=control_flows,
            detail_level=options.detail_level,
            include_docstrings=options.include_docstrings,
            recursive=True
        )

        return {
            "frame_type": frame_type,
            "skeleton": skeleton,
            "children": children_skeletons,
            "metadata": {
                "name": frame_data["name"],
                "qualified_name": frame_data["qualified_name"],
                "children_count": len(children_skeletons)
            }
        }

    def build_skeleton_from_ast(
        self,
        frame: 'AstFrameBase',
        options: SkeletonOptions,
        max_recursion_depth: int = 0
    ) -> str:
        """
        Build skeleton from AST frame (no DB queries, for embedding generation).
        
        Uses in-memory AST traversal to extract control flows, then delegates to
        formatters for consistent output with build_recursive_skeleton().
        
        Args:
            frame: AstFrame with children loaded
            options: Skeleton generation options (detail_level, include_docstrings, etc.)
            max_recursion_depth: How deep to recurse (0 = just this frame + control flow)
        
        Returns:
            Formatted skeleton string (same format as build_recursive_skeleton)
        """
        from nabu.core.frames import AstClassFrame, AstCallableFrame
        
        # Convert AstFrame to frame_data dict (formatter expects dict)
        frame_data = {
            'id': frame.id,
            'type': frame.type.value,
            'name': frame.name or '',
            'qualified_name': frame.qualified_name or '',
            'language': frame.language or 'python',
            'file_path': frame.file_path or '',
            'start_line': frame.start_line,
            'end_line': frame.end_line,
            'content': frame.content or '',
            'confidence': frame.confidence,
            'confidence_tier': frame.confidence_tier.value,
        }
        
        # Add specialized fields for CLASS/CALLABLE
        if isinstance(frame, AstClassFrame):
            frame_data['instance_fields'] = [f.to_dict() for f in frame.instance_fields] if frame.instance_fields else []
            frame_data['static_fields'] = [f.to_dict() for f in frame.static_fields] if frame.static_fields else []
        elif isinstance(frame, AstCallableFrame):
            frame_data['parameters'] = [p.to_dict() for p in frame.parameters] if frame.parameters else []
            frame_data['return_type'] = frame.return_type or ''
        
        # Get formatter
        formatter_registry = _get_formatter_registry()
        formatter = formatter_registry.get_formatter(frame.language or 'python')
        if not formatter:
            logger.warning(f"No formatter for language: {frame.language}")
            return f"# No formatter for {frame.language}"
        
        # Extract control flows from AST (if CALLABLE and detail_level requires it)
        control_flows = {}
        if frame.type.value == 'CALLABLE' and options.detail_level in ['guards', 'structure']:
            depth = 1 if options.detail_level == 'guards' else options.structure_detail_depth
            cf_list = _extract_control_flows_from_ast(frame, depth)
            if cf_list:
                control_flows[frame.id] = cf_list
        
        # Generate skeleton (no recursion - just this frame + control flow)
        # For embeddings: max_recursion_depth=0 means no children
        try:
            skeleton = formatter.format_show_structure(
                frame_data=frame_data,
                children=[],  # No children recursion for embeddings
                children_skeletons=[],
                control_flows=control_flows,
                detail_level=options.detail_level,
                include_docstrings=options.include_docstrings,
                recursive=False
            )
            return skeleton
        except Exception as e:
            logger.error(f"AST skeleton generation failed for {frame.qualified_name}: {e}")
            return f"# Error generating skeleton: {e}"
