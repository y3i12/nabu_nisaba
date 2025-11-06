"""Nisaba Read tool - creates tool result window."""

from typing import Dict, Any, Optional
from nisaba.tools.base import NisabaTool


class NisabaReadTool(NisabaTool):
    """Read file and create tool result window."""

    async def execute(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Read file content into tool result window.

        Instead of returning content directly, creates a persistent window
        in ---TOOL_RESULT_WINDOWS section. Check that section for actual content.

        :meta pitch: File reading with persistent window visibility
        :meta when: Reading files for understanding code structure

        Args:
            path: Path to file
            start_line: Optional start line (1-indexed)
            end_line: Optional end line (1-indexed, inclusive)

        Returns:
            Dict with window_id and status summary
        """
        try:
            if not hasattr(self.factory, 'tool_result_manager') or not self.factory.tool_result_manager:
                return {
                    "success": False,
                    "error": "Tool result manager not initialized",
                    "nisaba": True,
                    "error_type": "ConfigurationError"
                }

            window_id = self.factory.tool_result_manager.create_read_window(
                path, start_line, end_line
            )

            # Write rendered windows to file
            from pathlib import Path
            rendered = self.factory.tool_result_manager.render()
            output_file = Path.cwd() / ".nisaba" / "tool_result_windows.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(rendered, encoding='utf-8')

            summary = self.factory.tool_result_manager.get_state_summary()

            return {
                "success": True,
                "message": f"Created read window: {path} - {window_id}",
                "nisaba": True
                #"window_id": window_id,
                #**summary
            }
        except Exception as e:
            self.logger.error(f"Failed to create read window: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
