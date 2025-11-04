"""Nisaba Tool Windows management tool."""

from typing import Dict, Any, Optional
from nisaba.tools.base import NisabaTool


class NisabaToolWindowsTool(NisabaTool):
    """Manage tool result windows."""

    async def execute(
        self,
        operation: str,
        window_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manage tool result windows.

        :meta pitch: Window lifecycle management for tool results
        :meta when: Cleaning up context, viewing window status

        Args:
            operation: Operation type ("close", "clear_all", "status")
            window_id: Window ID (for "close" operation)

        Returns:
            Dict with operation result and status summary
        """
        try:
            if not hasattr(self.factory, 'tool_result_manager') or not self.factory.tool_result_manager:
                return {
                    "success": False,
                    "error": "Tool result manager not initialized",
                    "error_type": "ConfigurationError"
                }

            manager = self.factory.tool_result_manager

            if operation == "close":
                if not window_id:
                    return {
                        "success": False,
                        "error": "close operation requires 'window_id' parameter",
                        "error_type": "ValueError"
                    }
                manager.close_window(window_id)
                message = f"Closed window: {window_id}"

            elif operation == "clear_all":
                manager.clear_all()
                message = "Closed all tool result windows"

            elif operation == "status":
                message = "Tool result windows status"

            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}",
                    "error_type": "ValueError"
                }

            # Write rendered windows to file
            from pathlib import Path
            rendered = manager.render()
            output_file = Path.cwd() / ".nisaba" / "tool_result_windows.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(rendered, encoding='utf-8')

            summary = manager.get_state_summary()

            return {
                "success": True,
                "message": message,
                #**summary
            }
        except Exception as e:
            self.logger.error(f"Failed to manage tool windows: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
