"""Service for generating structural tree views of the codebase."""

import logging
from typing import Dict, List, Set, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class StructuralViewService:
    """
    Generate hierarchical tree views of codebase structure.

    Creates markdown trees with symbology:
    - +/- : collapsed/expanded state
    - ·   : leaf nodes
    - [N+]: child count when collapsed
    - ●   : search match markers
    """

    def __init__(self, db_manager):
        """
        Initialize service.

        Args:
            db_manager: KuzuDB manager for graph queries
        """
        self.db = db_manager

    def generate_tree(
        self,
        expanded_paths: Set[str],
        search_results: Optional[List[str]] = None,
        search_query: Optional[str] = None
    ) -> str:
        """
        Generate complete markdown tree.

        Args:
            expanded_paths: Set of qualified names that should be expanded
            search_results: List of qualified names matching search (marked with ●)
            search_query: Current search query string (for display)

        Returns:
            Formatted markdown tree with symbology
        """
        search_hits = set(search_results or [])

        # Build tree starting from language roots
        lines = []

        # Header with search context
        if search_query:
            lines.append(f'**search query**: "{search_query}"')
        else:
            lines.append('**search query**: (none)')
        lines.append('')

        # Get language roots
        roots = self._get_language_roots()

        for root in roots:
            tree_lines = self._build_tree_recursive(
                root['qualified_name'],
                expanded_paths,
                search_hits,
                depth=0,
                is_last=True
            )
            lines.extend(tree_lines)

        return '\n'.join(lines)

    def _get_language_roots(self) -> List[Dict[str, Any]]:
        """
        Get language root nodes (python_root, java_root, etc.).

        Returns:
            List of language frame data
        """
        query = """
        MATCH (lang:Frame {type: 'LANGUAGE'})
        RETURN lang.name AS name,
               lang.qualified_name AS qualified_name,
               size((lang)-[:Edge {type: 'CONTAINS'}]->()) AS child_count
        ORDER BY lang.name
        """

        result = self.db.execute(query)
        if not result or not hasattr(result, 'get_as_df'):
            return []

        df = result.get_as_df()
        return [
            {
                'name': row['name'],
                'qualified_name': row['qualified_name'],
                'child_count': row['child_count']
            }
            for _, row in df.iterrows()
        ]

    def _build_tree_recursive(
        self,
        qualified_name: str,
        expanded_paths: Set[str],
        search_hits: Set[str],
        depth: int,
        is_last: bool = False,
        prefix: str = ''
    ) -> List[str]:
        """
        Recursively build tree lines.

        Args:
            qualified_name: Node to build tree for
            expanded_paths: Expanded node paths
            search_hits: Search result qualified names
            depth: Current depth (for indentation)
            is_last: Whether this is last child of parent
            prefix: Line prefix for tree drawing

        Returns:
            List of formatted tree lines
        """
        lines = []

        # Get node data
        node = self._get_node_data(qualified_name)
        if not node:
            return lines

        # Check states
        is_expanded = qualified_name in expanded_paths
        is_search_hit = qualified_name in search_hits

        # Get children if expanded or to get count
        children = self._get_node_children(qualified_name)
        child_count = len(children)

        # Format this node
        node_line = self._format_node(
            node,
            is_expanded,
            is_search_hit,
            child_count,
            prefix,
            is_last
        )
        lines.append(node_line)

        # Recurse into children if expanded
        if is_expanded and children:
            # Prepare prefix for children
            if depth == 0:
                child_prefix = ''
            else:
                child_prefix = prefix + ('    ' if is_last else '│   ')

            for i, child in enumerate(children):
                is_last_child = (i == len(children) - 1)
                child_lines = self._build_tree_recursive(
                    child['qualified_name'],
                    expanded_paths,
                    search_hits,
                    depth + 1,
                    is_last_child,
                    child_prefix
                )
                lines.extend(child_lines)

        return lines

    def _get_node_data(self, qualified_name: str) -> Optional[Dict[str, Any]]:
        """
        Get node metadata.

        Args:
            qualified_name: Frame qualified name

        Returns:
            Node data dict or None if not found
        """
        query = """
        MATCH (node:Frame {qualified_name: $qname})
        RETURN node.name AS name,
               node.type AS type,
               node.qualified_name AS qualified_name
        """

        result = self.db.execute(query, {'qname': qualified_name})
        if not result or not hasattr(result, 'get_as_df'):
            return None

        df = result.get_as_df()
        if df.empty:
            return None

        row = df.iloc[0]
        return {
            'name': row['name'],
            'type': row['type'],
            'qualified_name': row['qualified_name']
        }

    def _get_node_children(self, qualified_name: str) -> List[Dict[str, Any]]:
        """
        Get children of a node.

        Args:
            qualified_name: Parent qualified name

        Returns:
            List of child node data (sorted)
        """
        query = """
        MATCH (parent:Frame {qualified_name: $qname})-[e:Edge]->(child:Frame)
        WHERE e.type = 'CONTAINS'
          AND child.type IN ['LANGUAGE', 'PACKAGE', 'CLASS', 'CALLABLE']
        RETURN child.name AS name,
               child.type AS type,
               child.qualified_name AS qualified_name,
               size((child)-[:Edge {type: 'CONTAINS'}]->()) AS child_count
        ORDER BY child.type DESC, child.name
        """

        result = self.db.execute(query, {'qname': qualified_name})
        if not result or not hasattr(result, 'get_as_df'):
            return []

        df = result.get_as_df()
        return [
            {
                'name': row['name'],
                'type': row['type'],
                'qualified_name': row['qualified_name'],
                'child_count': row['child_count']
            }
            for _, row in df.iterrows()
        ]

    def _format_node(
        self,
        node: Dict[str, Any],
        is_expanded: bool,
        is_search_hit: bool,
        child_count: int,
        prefix: str,
        is_last: bool
    ) -> str:
        """
        Format single tree node with symbology.

        Args:
            node: Node data
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

        # Name with type-specific suffix
        name = node['name']
        node_type = node['type']

        # Add child count for collapsed nodes
        if not is_expanded and child_count > 0:
            count_suffix = f' [{child_count}+]'
        else:
            count_suffix = ''

        # Add search hit marker
        search_marker = ' ●' if is_search_hit else ''

        # Compose line with hidden metadata for state tracking
        qname = node['qualified_name']
        line = f'{prefix}{connector}{expansion} {name}{count_suffix}{search_marker}'

        # Add hidden qualified name as HTML comment for state parsing
        line += f' <!-- {qname} -->'

        return line

    def search_frames(self, query: str) -> List[str]:
        """
        Search for frames matching query.

        Args:
            query: Search string (matches name, qualified_name)

        Returns:
            List of qualified names matching search
        """
        # Simple case-insensitive substring search
        # In future, could integrate with SearchTool
        search_query = """
        MATCH (f:Frame)
        WHERE f.type IN ['PACKAGE', 'CLASS', 'CALLABLE']
          AND (lower(f.name) CONTAINS $query OR lower(f.qualified_name) CONTAINS $query)
        RETURN f.qualified_name AS qualified_name
        LIMIT 100
        """

        result = self.db.execute(
            search_query,
            {'query': query.lower()}
        )

        if not result or not hasattr(result, 'get_as_df'):
            return []

        df = result.get_as_df()
        return df['qualified_name'].tolist()
