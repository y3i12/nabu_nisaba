"""MCP tool for managing structural codebase tree view."""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from nabu.mcp.tools.base import NabuTool

logger = logging.getLogger(__name__)


class StructuralViewTool(NabuTool):
    """
    Manage interactive structural tree view.

    Operations:
    - expand(path): Show children of collapsed node
    - collapse(path): Hide children of expanded node
    - search(query): Mark matching nodes with ●
    - clear_search(): Remove search markers
    - reset(): Collapse all to root view

    State persisted in-memory (TUI) and rendered to .nisaba/tui/structural_view.md
    """

    def __init__(self, factory):
        super().__init__(factory)
        self.view_file = Path.cwd() / ".nisaba" / "tui" / "structural_view.md"
        self._tui = None

    @property
    def tui(self):
        """Lazy-initialize TUI instance (persists across operations)."""
        if self._tui is None:
            from nabu.tui.structural_view_tui import StructuralViewTUI
            self._tui = StructuralViewTUI(self.db_manager, self.factory)
        return self._tui

    async def execute(
        self,
        operation: str,
        path: Optional[str] = None,
        query: Optional[str] = None,
        depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute structural view operation.

        :meta pitch: Interactive codebase tree navigation with expand/collapse/search
        :meta when: Building mental model of codebase structure, navigating hierarchy
        :meta emoji: 🗺️
        :param operation: Operation type ("expand", "collapse", "search", "clear_search", "reset")
        :param path: Target path for expand/collapse (e.g., "nisaba/factory")
        :param query: Search query string (for search operation)
        :param depth: Auto-expand depth for reset operation (default 2)
        :return: Operation result with updated state summary
        """
        import time
        start_time = time.time()

        try:
            # Validate operation
            valid_ops = ['expand', 'collapse', 'search', 'clear_search', 'reset']
            if operation not in valid_ops:
                return self._error_response(
                    ValueError(f"Invalid operation: {operation}"),
                    start_time,
                    recovery_hint=f"Valid operations: {', '.join(valid_ops)}"
                )

            # Check indexing
            indexing_check = self._check_indexing_status()
            if indexing_check:
                return indexing_check

            # Ensure directory exists
            self.view_file.parent.mkdir(parents=True, exist_ok=True)

            # Execute operation on TUI
            message = ""

            if operation == 'reset':
                reset_depth = depth if depth is not None else 2
                self.tui.reset(depth=reset_depth)
                message = f"Tree reset to initial state (auto-expanded to depth {reset_depth})"

            elif operation == 'expand':
                if not path:
                    return self._error_response(
                        ValueError("expand requires 'path' parameter"),
                        start_time
                    )

                # Resolve path using shared _resolve_frame (supports CODEBASE, partial paths, CONTAINS matching)
                results = await self._resolve_frame(path)
                if not results:
                    return self._error_response(
                        ValueError(f"Path not found: {path}"),
                        start_time,
                        recovery_hint="Use search() to find correct path"
                    )
                qname = results[0]['qualified_name']

                success = self.tui.expand(qname)
                if not success:
                    return self._error_response(
                        ValueError(f"Failed to expand: {path}"),
                        start_time
                    )

                message = f"Expanded: {path}"

            elif operation == 'collapse':
                if not path:
                    return self._error_response(
                        ValueError("collapse requires 'path' parameter"),
                        start_time
                    )

                # Resolve path using shared _resolve_frame (supports CODEBASE, partial paths, CONTAINS matching)
                results = await self._resolve_frame(path)
                if not results:
                    return self._error_response(
                        ValueError(f"Path not found: {path}"),
                        start_time
                    )
                qname = results[0]['qualified_name']

                success = self.tui.collapse(qname)
                if not success:
                    return self._error_response(
                        ValueError(f"Failed to collapse: {path}"),
                        start_time
                    )

                message = f"Collapsed: {path}"

            elif operation == 'search':
                if not query:
                    return self._error_response(
                        ValueError("search requires 'query' parameter"),
                        start_time
                    )

                matches = await self.tui.search(query)
                message = f"Search: '{query}' ({len(matches)} matches)"

            elif operation == 'clear_search':
                self.tui.clear_search()
                message = "Search cleared"

            # Render tree from in-memory frames
            tree_markdown = self.tui.render()

            # Write to file
            self._write_state(tree_markdown)

            # Get state summary
            state = self.tui.get_state_summary()

            return self._success_response({
                'operation': operation,
                'message': f"{message}, {state['expanded_count']} node(s) expanded, {state['search_hits']} search hit(s)",
                #'cached_frames': state['cached_frames'],
                #'expanded_count': state['expanded_count'],
                'search_hits': state['search_hits'],
                #'file_path': str(self.view_file)
            }, start_time)

        except Exception as e:
            logger.error(f"Structural view operation failed: {e}", exc_info=True)
            return self._error_response(
                e,
                start_time,
                recovery_hint="Check database health with show_status()",
                context={'operation': operation, 'path': path, 'query': query}
            )

    def _write_state(self, tree_markdown: str):
        """
        Write tree state to file.

        Args:
            tree_markdown: Complete tree markdown
        """
        # Wrap with delimiters for proxy injection
        content = f"{tree_markdown}"
        self.view_file.write_text(content)
        logger.info(f"Structural view updated: {self.view_file}")

