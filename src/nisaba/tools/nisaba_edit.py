"""Nisaba Edit tool - minimal result, no window."""

from typing import Dict, Any
from nisaba.tools.base import NisabaTool


class NisabaEditTool(NisabaTool):
    """Edit file using exact string replacement."""

    async def execute(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False
    ) -> Dict[str, Any]:
        """
        Edit file by exact string replacement.

        Returns minimal result (ok/error). Old and new strings are visible
        in your tool invocation in message history.

        :meta pitch: File editing with minimal context footprint
        :meta when: Making precise code changes

        Args:
            path: Path to file
            old_string: String to replace
            new_string: Replacement string
            replace_all: Replace all occurrences (default: False)

        Returns:
            Dict with success status
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            if old_string not in content:
                return {
                    "success": False,
                    "error": f"String not found in {path}",
                    "error_type": "ValueError",
                    "nisaba": True,
                }

            if not replace_all and content.count(old_string) > 1:
                return {
                    "success": False,
                    "error": f"Multiple occurrences found. Use replace_all=True",
                    "error_type": "ValueError",
                    "nisaba": True,
                }

            if replace_all:
                new_content = content.replace(old_string, new_string)
                count = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                count = 1

            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return {
                "success": True,
                "message": f"Replaced {count} occurrence(s) in {path}",
                "nisaba": True
            }
        except Exception as e:
            self.logger.error(f"Failed to edit file: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
