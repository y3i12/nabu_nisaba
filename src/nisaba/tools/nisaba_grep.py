"""Nisaba Grep tool - creates tool result window."""

from typing import Dict, Any, Optional
from nisaba.tools.base import NisabaTool


class NisabaGrepTool(NisabaTool):
    """Search with grep/ripgrep and create tool result window."""

    async def execute(
        self,
        pattern: str,
        path: str = ".",
        i: bool = False,
        n: bool = True,
        A: Optional[int] = None,
        B: Optional[int] = None,
        C: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Search for pattern into tool result window.

        Instead of returning matches directly, creates a persistent window
        in ---TOOL_RESULT_WINDOWS section. Check that section for actual results.

        :meta pitch: Pattern search with persistent results visibility
        :meta when: Finding code patterns, errors, usages

        Args:
            pattern: Search pattern (regex)
            path: Path to search (default: current dir)
            i: Case insensitive
            n: Show line numbers (default: True)
            A: Lines of context after match
            B: Lines of context before match
            C: Lines of context before and after match

        Returns:
            Dict with window_id and status summary
        """
        try:
            if not hasattr(self.factory, 'tool_result_manager') or not self.factory.tool_result_manager:
                return {
                    "success": False,
                    "error": "Tool result manager not initialized",
                    "error_type": "ConfigurationError",
                    "nisaba": True,
                }

            kwargs = {'i': i, 'n': n}
            if A is not None:
                kwargs['A'] = A
            if B is not None:
                kwargs['B'] = B
            if C is not None:
                kwargs['C'] = C

            window_id = self.factory.tool_result_manager.create_grep_window(
                pattern, path, **kwargs
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
                "message": f"Searched for pattern: {pattern} - {window_id}",
                "nisaba": True
                #"window_id": window_id,
                #**summary
            }
        except Exception as e:
            self.logger.error(f"Failed to create grep window: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
