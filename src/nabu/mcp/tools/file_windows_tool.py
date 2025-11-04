"""MCP tool for managing file windows."""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from nabu.mcp.tools.base import NabuTool

logger = logging.getLogger(__name__)


class FileWindowsTool(NabuTool):
    """
    Manage persistent file windows for code visibility.

    Operations:
    - open_frame(frame_path): Open frame's full body
    - open_range(file_path, start, end): Open specific line range
    - open_search(query, max_windows, context_lines): Open search results
    - update(window_id, start, end): Update window range
    - close(window_id): Close window
    - clear_all(): Close all windows
    - status(): Show current windows
    """

    def __init__(self, factory):
        super().__init__(factory)
        self.view_file = Path.cwd() / ".nisaba" / "file_windows.md"
        self._manager = None

    @property
    def manager(self):
        """Lazy-initialize manager instance (persists across operations)."""
        if self._manager is None:
            from nabu.tui.file_windows_manager import FileWindowsManager
            self._manager = FileWindowsManager(self.db_manager, self.factory)
        return self._manager

    async def execute(
        self,
        operation: str,
        frame_path: Optional[str] = None,
        file_path: Optional[str] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        query: Optional[str] = None,
        max_windows: Optional[int] = 5,
        context_lines: Optional[int] = 3,
        window_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute file window operation.

        :meta pitch: Persistent file windows for simultaneous code visibility
        :meta when: Comparing implementations, understanding dependencies, investigating bugs
        :meta emoji: 🪟
        :param operation: Operation type
        :param frame_path: Frame qualified name (for open_frame)
        :param file_path: File path (for open_range)
        :param start: Start line (for open_range, update)
        :param end: End line (for open_range, update)
        :param query: Search query (for open_search)
        :param max_windows: Max windows to open (for open_search)
        :param context_lines: Context lines around match (for open_search)
        :param window_id: Window ID (for update, close)
        :return: Operation result with state summary
        """
        import time
        start_time = time.time()

        try:
            # Validate operation
            valid_ops = ['open_frame', 'open_range', 'open_search', 'update', 'close', 'clear_all', 'status']
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

            # Execute operation
            message = ""
            result_data = {}

            if operation == 'open_frame':
                if not frame_path:
                    return self._error_response(
                        ValueError("open_frame requires 'frame_path' parameter"),
                        start_time
                    )
                window_id = self.manager.open_frame_window(frame_path)
                message = f"Opened frame window: {frame_path}"
                result_data['window_id'] = window_id

            elif operation == 'open_range':
                if not file_path or start is None or end is None:
                    return self._error_response(
                        ValueError("open_range requires 'file_path', 'start', 'end' parameters"),
                        start_time
                    )
                window_id = self.manager.open_range_window(file_path, start, end)
                message = f"Opened range window: {file_path}:{start}-{end}"
                result_data['window_id'] = window_id

            elif operation == 'open_search':
                if not query:
                    return self._error_response(
                        ValueError("open_search requires 'query' parameter"),
                        start_time
                    )
                window_ids = await self.manager.open_search_windows(
                    query, max_windows, context_lines
                )
                message = f"Opened {len(window_ids)} search result windows"
                result_data['window_ids'] = window_ids

            elif operation == 'update':
                if not window_id or start is None or end is None:
                    return self._error_response(
                        ValueError("update requires 'window_id', 'start', 'end' parameters"),
                        start_time
                    )
                self.manager.update_window(window_id, start, end)
                message = f"Updated window {window_id}"

            elif operation == 'close':
                if not window_id:
                    return self._error_response(
                        ValueError("close requires 'window_id' parameter"),
                        start_time
                    )
                self.manager.close_window(window_id)
                message = f"Closed window {window_id}"

            elif operation == 'clear_all':
                self.manager.clear_all()
                message = "Closed all windows"

            elif operation == 'status':
                message = "File windows status"

            # Render and write
            rendered = self.manager.render()
            self._write_state(rendered)

            # Get state summary
            state = self.manager.get_state_summary()

            return self._success_response({
                'operation': operation,
                'message': message,
                #**result_data,
                #**state
            }, start_time)

        except Exception as e:
            logger.error(f"File windows operation failed: {e}", exc_info=True)
            return self._error_response(
                e,
                start_time,
                recovery_hint="Check file paths and frame names",
                context={'operation': operation}
            )

    def _write_state(self, content: str):
        """Write windows state to file."""
        self.view_file.write_text(content)
        logger.info(f"File windows updated: {self.view_file}")
