"""Nisaba Glob tool - creates tool result window."""

from typing import Dict, Any
from nisaba.tools.base import NisabaTool


class NisabaGlobTool(NisabaTool):
    """Find files by pattern and create tool result window."""

    async def execute(
        self,
        pattern: str,
        path: str = "."
    ) -> Dict[str, Any]:
        """
        Find files by glob pattern into tool result window.

        Instead of returning matches directly, creates a persistent window
        in ---TOOL_RESULT_WINDOWS section. Check that section for actual results.

        :meta pitch: File finding with persistent results visibility
        :meta when: Discovering files by name patterns

        Args:
            pattern: Glob pattern (e.g., "**/*.py")
            path: Base path to search (default: current dir)

        Returns:
            Dict with window_id and status summary
        """
        try:
            if not hasattr(self.factory, 'tool_result_manager') or not self.factory.tool_result_manager:
                return {
                    "success": False,
                    "error": "Tool result manager not initialized",
                    "error_type": "ConfigurationError"
                }

            window_id = self.factory.tool_result_manager.create_glob_window(pattern, path)

            # Write rendered windows to file
            from pathlib import Path
            rendered = self.factory.tool_result_manager.render()
            output_file = Path.cwd() / ".nisaba" / "tool_result_windows.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(rendered, encoding='utf-8')

            summary = self.factory.tool_result_manager.get_state_summary()

            return {
                "success": True,
                "message": f"Found files matching: {pattern} - {window_id}",
                #"window_id": window_id,
                #**summary
            }
        except Exception as e:
            self.logger.error(f"Failed to create glob window: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
