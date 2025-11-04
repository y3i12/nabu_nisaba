"""
FrameCache: Manages in-memory ViewableFrame instances.

Singleton per database, provides lazy loading and instance deduplication.
"""
from typing import Dict, Optional
from nabu.tui.viewable_frame import ViewableFrame, hydrate_frame_from_kuzu
from nabu.db.kuzu_manager import KuzuConnectionManager


class FrameCache:
    """
    Cache of ViewableFrame instances loaded from kuzu.

    Responsibilities:
    - Load frames on demand from kuzu
    - Deduplicate by qualified_name
    - Manage codebase root initialization
    """

    def __init__(self, db_manager: KuzuConnectionManager):
        """
        Initialize cache.

        Args:
            db_manager: KuzuDB connection manager
        """
        self.db_manager = db_manager
        self.frames: Dict[str, ViewableFrame] = {}
        self.root: Optional[ViewableFrame] = None

    def get_or_load(self, qualified_name: str) -> Optional[ViewableFrame]:
        """
        Get cached frame or load from kuzu.

        Args:
            qualified_name: Frame qualified name

        Returns:
            ViewableFrame instance or None if not found
        """
        # Return cached if available
        if qualified_name in self.frames:
            return self.frames[qualified_name]

        # Load from kuzu
        frame = self._load_frame(qualified_name)

        if frame:
            self.frames[qualified_name] = frame

        return frame

    def _load_frame(self, qualified_name: str) -> Optional[ViewableFrame]:
        """
        Load single frame from kuzu.

        Args:
            qualified_name: Frame qualified name

        Returns:
            ViewableFrame or None if not found
        """
        query = """
        MATCH (f:Frame {qualified_name: $qname})
        RETURN f.id AS id,
               f.name AS name,
               f.qualified_name AS qualified_name,
               f.type AS type,
               f.file_path AS file_path,
               f.start_line AS start_line,
               f.end_line AS end_line,
               f.language AS language
        LIMIT 1
        """

        result = self.db_manager.execute(query, {'qname': qualified_name})

        if not result or not hasattr(result, 'get_as_df'):
            return None

        df = result.get_as_df()

        if df.empty:
            return None

        # Hydrate from first row
        row = df.iloc[0].to_dict()
        return hydrate_frame_from_kuzu(row)

    def initialize_root(self) -> ViewableFrame:
        """
        Load codebase root and language roots.

        Returns:
            Codebase root frame with language children loaded
        """
        # Load codebase root
        query_root = """
        MATCH (f:Frame {type: 'CODEBASE'})
        RETURN f.id AS id,
               f.name AS name,
               f.qualified_name AS qualified_name,
               f.type AS type,
               f.file_path AS file_path
        LIMIT 1
        """

        result = self.db_manager.execute(query_root)

        if not result or not hasattr(result, 'get_as_df'):
            raise RuntimeError("No codebase root found in database")

        df = result.get_as_df()

        if df.empty:
            raise RuntimeError("No codebase root found in database")

        # Hydrate root
        root_row = df.iloc[0].to_dict()
        self.root = hydrate_frame_from_kuzu(root_row)
        self.frames[self.root.qualified_name] = self.root

        # Load language roots as direct children
        self.root.ensure_children_loaded(self.db_manager, self)

        # Cache language roots
        for lang_root in self.root.children:
            self.frames[lang_root.qualified_name] = lang_root

        return self.root
