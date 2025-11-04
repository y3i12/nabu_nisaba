"""
ViewableFrame: AstFrameBase with TUI view state.

Extends frame hierarchy with lazy loading and view metadata.
"""
from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING
from nabu.core.frames import AstFrameBase
from nabu.core.frame_types import FrameNodeType

if TYPE_CHECKING:
    from nabu.db.kuzu_manager import KuzuConnectionManager


@dataclass(slots=True)
class ViewableFrame(AstFrameBase):
    """
    Frame with view state and lazy loading capabilities.

    Additional slots for TUI state (beyond AstFrameBase):
    - _view_expanded: Whether node is expanded in tree
    - _view_is_search_hit: Whether node matches active search
    - _search_score: RRF score from unified search (0.0-1.0+)
    - _children_loaded: Whether children have been loaded from kuzu
    - _child_count: Cached child count from kuzu
    """

    # View state (additional slots)
    _view_expanded: bool = False
    _view_is_search_hit: bool = False
    _search_score: Optional[float] = None
    _children_loaded: bool = False
    _child_count: Optional[int] = None

    def ensure_children_loaded(self, db_manager: 'KuzuConnectionManager', cache: 'FrameCache' = None) -> None:
        """
        Lazy load children from kuzu if not already loaded.

        Args:
            db_manager: KuzuDB connection manager
            cache: Optional FrameCache for instance deduplication
        """
        if self._children_loaded:
            return

        # Query children via CONTAINS edges
        query = """
        MATCH (parent:Frame {qualified_name: $qname})-[:Edge {type: 'CONTAINS'}]->(child:Frame)
        WHERE child.type IN ['LANGUAGE', 'PACKAGE', 'CLASS', 'CALLABLE']
        RETURN child.id AS id,
               child.name AS name,
               child.qualified_name AS qualified_name,
               child.type AS type,
               child.file_path AS file_path,
               child.start_line AS start_line,
               child.end_line AS end_line,
               child.language AS language
        ORDER BY child.type DESC, child.name
        """

        result = db_manager.execute(query, {'qname': self.qualified_name})

        if result and hasattr(result, 'get_as_df'):
            df = result.get_as_df()

            for _, row in df.iterrows():
                child_qname = row['qualified_name']

                # Use cache if available to maintain instance identity
                if cache:
                    child_frame = cache.get_or_load(child_qname)
                else:
                    # Fallback: hydrate new instance (Phase 0 compatibility)
                    child_frame = hydrate_frame_from_kuzu(row.to_dict())

                if child_frame:
                    # Establish parent-child relationship
                    # (use add_child to maintain bidirectional links)
                    self.add_child(child_frame)

        self._children_loaded = True

    def get_child_count(self, db_manager: 'KuzuConnectionManager') -> int:
        """
        Get child count (cached or query).

        Args:
            db_manager: KuzuDB connection manager

        Returns:
            Number of children
        """
        if self._child_count is None:
            query = """
            MATCH (parent:Frame {qualified_name: $qname})-[:Edge {type: 'CONTAINS'}]->(child:Frame)
            WHERE child.type IN ['LANGUAGE', 'PACKAGE', 'CLASS', 'CALLABLE']
            RETURN count(*) AS count
            """

            result = db_manager.execute(query, {'qname': self.qualified_name})

            if result and hasattr(result, 'get_as_df'):
                df = result.get_as_df()
                self._child_count = int(df.iloc[0]['count']) if not df.empty else 0
            else:
                self._child_count = 0

        return self._child_count


def hydrate_frame_from_kuzu(row: dict) -> ViewableFrame:
    """
    Create ViewableFrame from kuzu query result row.

    Args:
        row: Dict with keys: id, name, qualified_name, type, file_path, etc.

    Returns:
        ViewableFrame instance with minimal properties hydrated
    """
    frame_type = FrameNodeType(row['type'])

    # For spike: use ViewableFrame for all types
    # Later: could add ViewableClassFrame, ViewableCallableFrame, etc.
    return ViewableFrame(
        id=row['id'],
        type=frame_type,
        name=row.get('name'),
        qualified_name=row.get('qualified_name'),
        file_path=row.get('file_path'),
        start_line=row.get('start_line', 0),
        end_line=row.get('end_line', 0),
        language=row.get('language'),
        # Defaults for other AstFrameBase fields
        confidence=1.0,
        provenance="kuzu",  # Mark as hydrated from database
    )
