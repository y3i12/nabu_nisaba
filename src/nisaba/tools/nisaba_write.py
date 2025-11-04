"""Nisaba Write tool - minimal result, no window."""

from typing import Dict, Any
from pathlib import Path
from nisaba.tools.base import NisabaTool


class NisabaWriteTool(NisabaTool):
    """Write new file."""

    async def execute(
        self,
        path: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Write new file with content.

        Returns minimal result (ok/error). Content is visible in your
        tool invocation in message history.

        :meta pitch: File creation with minimal context footprint
        :meta when: Creating new files

        Args:
            path: Path to new file
            content: File content

        Returns:
            Dict with success status
        """
        try:
            path = Path(path)

            if path.exists():
                return {
                    "success": False,
                    "error": f"File already exists: {path}",
                    "error_type": "FileExistsError"
                }

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')

            return {
                "success": True,
                "message": f"Created file: {path}"
            }
        except Exception as e:
            self.logger.error(f"Failed to write file: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
