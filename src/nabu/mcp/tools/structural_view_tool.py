"""MCP tool for managing structural codebase tree view."""

import logging
from typing import Optional
from pathlib import Path

from nabu.mcp.tools.base import NabuTool
from nisaba.tools.base_tool import BaseToolResponse
from nisaba.workspace_files import WorkspaceFiles

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
    ) -> BaseToolResponse:
        """
        Execute structural view operation.

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
                return self.response_error(f"Invalid operation: {operation}, valid operations: {', '.join(valid_ops)}")

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
                    return self.response_error("expand requires 'path' parameter")

                # Resolve path using shared _resolve_frame (supports CODEBASE, partial paths, CONTAINS matching)
                results = await self._resolve_frame(path)
                if not results:
                    return self.response_error(f"Path not found: {path}")
                qname = results[0]['qualified_name']

                success = self.tui.expand(qname)
                if not success:
                    return self.response_error(f"Failed to expand: {path}")

                message = f"Expanded: {path}"

            elif operation == 'collapse':
                if not path:
                    return self.response_error("collapse requires 'path' parameter")

                # Resolve path using shared _resolve_frame (supports CODEBASE, partial paths, CONTAINS matching)
                results = await self._resolve_frame(path)
                if not results:
                    return self.response_error(f"Path not found: {path}")
                
                qname = results[0]['qualified_name']
                success = self.tui.collapse(qname)

                if not success:
                    return self.response_error(f"Failed to collapse: {path}")

                message = f"Collapsed: {path}"

            elif operation == 'search':
                if not query:
                    return self.response_error("search requires 'query' parameter")

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

            return self.response_success({
                'operation': operation,
                'message': f"{message}, {state['expanded_count']} node(s) expanded, {state['search_hits']} search hit(s)",
                'search_hits': state['search_hits'],
            })

        except Exception as e:
            return self.response_exception(e, "Structural view operation failed")

    def _write_state(self, tree_markdown: str):
        """
        Write tree state to file via WorkspaceFiles singleton.

        Args:
            tree_markdown: Complete tree markdown
        """
        # Write via shared cache
        WorkspaceFiles.instance().structural_view.write(tree_markdown)
        logger.info(f"Structural view updated via WorkspaceFiles singleton")

