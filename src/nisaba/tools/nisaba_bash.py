"""Nisaba Bash tool - creates tool result window."""

from typing import Dict, Any, Optional
from nisaba.tools.base import NisabaTool


class NisabaBashTool(NisabaTool):
    """Execute bash command and create tool result window."""

    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute bash command into tool result window.

        Instead of returning output directly, creates a persistent window
        in ---TOOL_RESULT_WINDOWS section. Check that section for actual output.

        :meta pitch: Command execution with persistent output visibility
        :meta when: Running builds, tests, git commands, etc.

        Args:
            command: Shell command to execute
            cwd: Working directory (default: current)

        Returns:
            Dict with window_id, exit_code, and status summary
        """
        try:
            if not hasattr(self.factory, 'tool_result_manager') or not self.factory.tool_result_manager:
                return {
                    "success": False,
                    "error": "Tool result manager not initialized",
                    "error_type": "ConfigurationError",
                    "nisaba": True,
                }

            window_id = self.factory.tool_result_manager.create_bash_window(command, cwd)

            # Write rendered windows to file
            from pathlib import Path
            rendered = self.factory.tool_result_manager.render()
            output_file = Path.cwd() / ".nisaba" / "tool_result_windows.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(rendered, encoding='utf-8')

            # Get exit code from created window
            window = self.factory.tool_result_manager.windows[window_id]
            summary = self.factory.tool_result_manager.get_state_summary()

            return {
                "success": True,
                "message": f"Executed command: {command[:30]}... (return {window.exit_code}) - {window_id}",
                "nisaba": True
                #"window_id": window_id,
                #"exit_code": window.exit_code,
                #**summary
            }
        except Exception as e:
            self.logger.error(f"Failed to create bash window: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
