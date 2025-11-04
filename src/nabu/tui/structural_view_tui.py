"""
Stateful TUI service for structural view.

Uses in-memory ViewableFrame hierarchy with lazy loading.
Operations mutate frame metadata, rendering traverses frames.
"""

import logging
from typing import Optional, List, Set, Dict, Any
from pathlib import Path
from nabu.tui.frame_cache import FrameCache
from nabu.tui.viewable_frame import ViewableFrame
from nabu.core.frames import FrameNodeType
from nabu.db.kuzu_manager import KuzuConnectionManager

logger = logging.getLogger(__name__)


class StructuralViewTUI:
    """
    Stateful TUI service for structural view.

    Architecture:
    - In-memory frame hierarchy (ViewableFrame instances)
    - Operations mutate frame metadata (_view_expanded, _view_is_search_hit)
    - Rendering traverses frames (not kuzu queries)
    - Lazy loading on expand operations
    """

    def __init__(self, db_manager: KuzuConnectionManager, factory):
        """
        Initialize TUI with frame cache and search tool.

        Args:
            db_manager: KuzuDB connection manager
            factory: NabuMCPFactory for SearchTool instantiation
        """
        self.cache = FrameCache(db_manager)
        self.cache.initialize_root()
        self.search_query: Optional[str] = None
        self.search_hits: Set[str] = set()  # qualified_names

        # Instantiate SearchTool for semantic search backend
        from nabu.mcp.tools.search_tools import SearchTool
        self.search_tool = SearchTool(factory=factory)
        
        # Restore state
        self.load_state()

    @property
    def state_file(self) -> Path:
        """Path to state persistence file."""
        return Path.cwd() / ".nisaba" / "structural_view_state.json"

    def save_state(self) -> None:
        """Save structural view state to JSON."""
        import json
        
        # Collect expanded paths from cache
        expanded_paths = [
            qn for qn, frame in self.cache.frames.items()
            if frame._view_expanded
        ]
        
        # Collect search hits with scores
        search_hits = {
            qn: frame._search_score
            for qn, frame in self.cache.frames.items()
            if frame._view_is_search_hit and frame._search_score is not None
        }
        
        state = {
            "expanded_paths": expanded_paths,
            "search_query": self.search_query,
            "search_hits": search_hits
        }
        
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2), encoding='utf-8')
        logger.debug(f"Saved structural view state: {len(expanded_paths)} expanded, {len(search_hits)} hits")

    def load_state(self) -> None:
        """Restore structural view state from JSON (graceful degradation)."""
        import json
        
        if not self.state_file.exists():
            logger.debug("No structural view state file found, starting fresh")
            return
        
        try:
            state = json.loads(self.state_file.read_text(encoding='utf-8'))
            
            # Restore expanded paths
            for qn in state.get("expanded_paths", []):
                try:
                    frame = self.cache.get_or_load(qn)
                    if frame:
                        frame._view_expanded = True
                        frame.ensure_children_loaded(self.cache.db_manager, self.cache)
                except Exception as e:
                    logger.warning(f"Skipping expansion of {qn}: {e}")
                    continue
            
            # Restore search state
            self.search_query = state.get("search_query")
            search_hits = state.get("search_hits", {})
            
            for qn, score in search_hits.items():
                try:
                    frame = self.cache.get_or_load(qn)
                    if frame:
                        frame._view_is_search_hit = True
                        frame._search_score = score
                        self.search_hits.add(qn)
                        self._load_ancestry_path(frame)
                except Exception as e:
                    logger.warning(f"Skipping search hit {qn}: {e}")
                    continue
            
            logger.info(f"Restored structural view state: {len(state.get('expanded_paths', []))} expanded, {len(search_hits)} search hits")
        except Exception as e:
            logger.warning(f"Failed to load structural view state: {e}")

    # === Operations (mutate frame metadata) ===

    def expand(self, qualified_name: str) -> bool:
        """
        Expand node, lazy-load children.

        Args:
            qualified_name: Frame to expand

        Returns:
            True if successful, False if frame not found
        """
        frame = self.cache.get_or_load(qualified_name)
        if not frame:
            return False

        frame._view_expanded = True
        frame.ensure_children_loaded(self.cache.db_manager, self.cache)

        # Ensure ancestry path is visible (expand all parents)
        self._load_ancestry_path(frame)

        self.save_state()
        return True

    def collapse(self, qualified_name: str) -> bool:
        """
        Collapse node.

        Args:
            qualified_name: Frame to collapse

        Returns:
            True if successful, False if frame not found
        """
        frame = self.cache.get_or_load(qualified_name)
        if not frame:
            return False

        frame._view_expanded = False
        self.save_state()
        return True

    async def search(self, query: str, k: int = 50) -> List[str]:
        """
        Search frames using nabu's unified search (semantic + FTS + regex).

        Marks matching frames with scores, expands ancestry paths.

        Args:
            query: Search query (natural language, keywords, code patterns)
            k: Maximum results to mark in tree (default 50)

        Returns:
            List of matching qualified_names
        """
        # Clear previous search
        self._unmark_all_search_hits()

        # Call SearchTool backend (unified semantic + FTS search)
        search_result = await self.search_tool.execute(
            query=query,
            k=k,
            frame_type_filter="CALLABLE|CLASS|PACKAGE",  # Tree-relevant frames
            compact_metadata=True,  # Don't need snippets for tree view
            context_lines=0,  # Don't need content
            max_snippets=0
        )

        if not search_result.get('success'):
            return []

        results = search_result.get('data', {}).get('results', [])

        # Mark hits with scores + load ancestry
        matches = []
        for result in results:
            qname = result['qualified_name']
            score = result.get('rrf_score', 0.0)

            frame = self.cache.get_or_load(qname)
            if frame:
                frame._view_is_search_hit = True
                frame._search_score = score
                self._load_ancestry_path(frame)
                matches.append(qname)

        self.search_query = query
        self.search_hits = set(matches)
        self.save_state()
        return matches

    def clear_search(self) -> None:
        """Clear search markers."""
        self._unmark_all_search_hits()
        self.search_query = None
        self.search_hits.clear()
        self.save_state()

    def reset(self, depth: int = 2) -> None:
        """
        Reset to initial state and auto-expand to depth.

        Args:
            depth: Levels to auto-expand in active codebase
                   0 = codebase collapsed
                   1 = codebase expanded (show languages)
                   2 = languages expanded (show packages)
                   3+ = deeper expansion
        """
        self.cache = FrameCache(self.cache.db_manager)
        self.cache.initialize_root()
        self.clear_search()

        # Auto-expand to depth
        if depth > 0 and self.cache.root:
            self._expand_to_depth(self.cache.root, depth, current_depth=0)
        
        self.save_state()

    # === Rendering (traverse frames) ===

    def render(self) -> str:
        """
        Render markdown tree from in-memory frames.

        Returns:
            Formatted markdown with symbology
        """
        lines = []

        # Header with search context
        if self.search_query:
            lines.append(f'**search query**: "{self.search_query}"')
        else:
            lines.append('**search query**: (none)')
        lines.append('')

        # Render from codebase root (not language roots)
        if not self.cache.root:
            return '\n'.join(lines)

        tree_lines = self._render_frame_recursive(
            self.cache.root,
            depth=0,
            is_last=True,
            prefix=''
        )
        lines.extend(tree_lines)

        return '\n'.join(lines)

    def _render_frame_recursive(
        self,
        frame: ViewableFrame,
        depth: int,
        is_last: bool,
        prefix: str
    ) -> List[str]:
        """
        Recursively render frame subtree.

        Args:
            frame: Frame to render
            depth: Current depth (for indentation)
            is_last: Whether this is last child of parent
            prefix: Line prefix for tree drawing

        Returns:
            List of formatted tree lines
        """
        lines = []

        # Check states
        is_expanded = frame._view_expanded
        is_search_hit = frame._view_is_search_hit

        # Get child count
        child_count = frame.get_child_count(self.cache.db_manager)

        # Format node with symbology
        line = self._format_node(
            frame,
            is_expanded,
            is_search_hit,
            child_count,
            prefix,
            is_last
        )
        lines.append(line)

        # Recurse into children if expanded
        if is_expanded and child_count > 0:
            frame.ensure_children_loaded(self.cache.db_manager, self.cache)

            # Prepare prefix for children
            # Always add connector prefix for nested items
            child_prefix = prefix + ('    ' if is_last else '│   ')

            for i, child in enumerate(frame.children):
                is_last_child = (i == len(frame.children) - 1)
                child_lines = self._render_frame_recursive(
                    child,
                    depth + 1,
                    is_last_child,
                    child_prefix
                )
                lines.extend(child_lines)

        return lines

    def _format_node(
        self,
        frame: ViewableFrame,
        is_expanded: bool,
        is_search_hit: bool,
        child_count: int,
        prefix: str,
        is_last: bool
    ) -> str:
        """
        Format node with symbology.

        Symbology:
        · leaf (no children)
        - expanded
        + collapsed
        ● search hit
        [N+] child count badge

        Args:
            frame: Frame to format
            is_expanded: Whether node is expanded
            is_search_hit: Whether node matches search
            child_count: Number of children
            prefix: Line prefix
            is_last: Is last child of parent

        Returns:
            Formatted tree line
        """
        # Tree connector
        if prefix == '':  # Root level
            connector = ''
        else:
            connector = '└─' if is_last else '├─'

        # Expansion symbol
        if child_count == 0:
            expansion = '·'  # Leaf
        elif is_expanded:
            expansion = '-'  # Expanded
        else:
            expansion = '+'  # Collapsed

        # Name
        name = frame.name or '(unnamed)'

        # Child count badge
        if not is_expanded and child_count > 0:
            count_suffix = f' [{child_count}+]'
        else:
            count_suffix = ''

        # Search hit marker with score
        if is_search_hit and frame._search_score is not None:
            search_marker = f' ● {frame._search_score:.2f}'
        elif is_search_hit:
            search_marker = ' ●'
        else:
            search_marker = ''

        # Compose line with HTML comment metadata
        line = f'{prefix}{connector}{expansion} {name}{count_suffix}{search_marker}'
        line += f' <!-- {frame.qualified_name} -->'

        return line

    # === Helper methods ===

    def _load_ancestry_path(self, frame: ViewableFrame) -> None:
        """
        Load and expand ancestry path from frame to codebase root.

        Ensures search results are visible in tree by expanding
        all parent nodes along the path.

        Args:
            frame: Frame to load ancestry for
        """
        current_qn = frame.qualified_name

        while current_qn:
            # Get current frame (load if needed)
            current = self.cache.get_or_load(current_qn)
            if not current:
                break

            # Query kuzu for parent via CONTAINS edge
            query = """
            MATCH (parent:Frame)-[:Edge {type: 'CONTAINS'}]->(child:Frame {qualified_name: $child_qn})
            WHERE parent.type IN ['PACKAGE', 'CLASS', 'CALLABLE', 'LANGUAGE', 'CODEBASE']
            RETURN parent.qualified_name AS qualified_name
            LIMIT 1
            """

            result = self.cache.db_manager.execute(query, {'child_qn': current_qn})

            if result and hasattr(result, 'get_as_df'):
                df = result.get_as_df()
                if not df.empty:
                    parent_qn = df.iloc[0]['qualified_name']

                    # Load parent into cache and expand
                    parent = self.cache.get_or_load(parent_qn)
                    if parent:
                        parent._view_expanded = True
                        parent.ensure_children_loaded(self.cache.db_manager, self.cache)
                        current_qn = parent_qn
                    else:
                        break
                else:
                    break
            else:
                break

    def _unmark_all_search_hits(self) -> None:
        """Clear search hit markers and scores from all cached frames."""
        for frame in self.cache.frames.values():
            frame._view_is_search_hit = False
            frame._search_score = None

    def _expand_to_depth(
        self,
        frame: ViewableFrame,
        target_depth: int,
        current_depth: int
    ) -> None:
        """
        Recursively expand frame hierarchy to target depth.

        Args:
            frame: Frame to expand
            target_depth: Depth to reach
            current_depth: Current depth in recursion
        """
        if current_depth >= target_depth:
            return

        # Expand this frame
        frame._view_expanded = True
        frame.ensure_children_loaded(self.cache.db_manager, self.cache)

        # Recurse into children
        for child in frame.children:
            self._expand_to_depth(child, target_depth, current_depth + 1)

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get current state for tool responses.

        Returns:
            Dict with cached_frames, expanded_count, search_hits, search_query
        """
        expanded_count = sum(
            1 for f in self.cache.frames.values()
            if f._view_expanded
        )

        return {
            'cached_frames': len(self.cache.frames),
            'expanded_count': expanded_count,
            'search_hits': len(self.search_hits),
            'search_query': self.search_query
        }
