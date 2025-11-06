"""
Manage tool result visibility states.
"""
import json
from pathlib import Path
from typing import Any, Dict, List
from nisaba.tools.base import NisabaTool


class NisabaToolResultStateTool(NisabaTool):
    """Manage tool result window states for compact/expanded display."""

    async def execute(self, operation: str, tool_ids: List[str] = None) -> Dict[str, Any]:
        """
        Manage tool result visibility in request timeline.

        Controls whether tool results appear collapsed or expanded in message history.
        Changes take effect on next request (not immediately visible).

        :meta pitch: Collapse old tool results to reduce context noise
        :meta when: After processing tool outputs, to clean up message timeline

        Args:
            operation: 'open' or 'close'
            tool_ids: List of tool IDs to modify (e.g., ['toolu_ABC', 'toolu_XYZ'])

        Returns:
            Dict with success status and modified tool IDs
        """
        try:
            if operation not in ['open', 'close']:
                return {
                    "success": False,
                    "error": f"Invalid operation '{operation}'. Use 'open' or 'close'."
                }
            
            if not tool_ids:
                return {
                    "success": False,
                    "error": "No tool IDs provided"
                }
            
            # Find current session state file
            cache_dir = Path('.nisaba/request_cache')
            if not cache_dir.exists():
                return {
                    "success": False,
                    "error": "No active session cache found"
                }
            
            # Find most recent session directory
            sessions = sorted(cache_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            session_dir = None
            for s in sessions:
                if s.is_dir() and (s / 'state.json').exists():
                    session_dir = s
                    break
            
            if not session_dir:
                return {
                    "success": False,
                    "error": "No session with state.json found"
                }
            
            state_file = session_dir / 'state.json'
            
            # Load current state
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Failed to parse state.json: {e}"
                }
            
            tool_result_state = state_data.get('tool_result_state', {})
            
            # Update window states
            new_state = 'open' if operation == 'open' else 'closed'
            modified = []
            not_found = []
            
            for tool_id in tool_ids:
                if tool_id in tool_result_state:
                    tool_result_state[tool_id]['window_state'] = new_state
                    # Update the content string as well
                    tool_obj = tool_result_state[tool_id]
                    tool_obj['tool_result_content'] = (
                        f"status: {tool_obj.get('tool_result_status', 'success')}, "
                        f"window_state:{new_state}, "
                        f"window_id: {tool_id}"
                    )
                    modified.append(tool_id)
                else:
                    not_found.append(tool_id)
            
            if not modified:
                return {
                    "success": False,
                    "error": f"None of the specified tool IDs found in state",
                    "not_found": not_found
                }
            
            # Write updated state
            state_data['tool_result_state'] = tool_result_state
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            result = {
                "success": True,
                "data": {
                    "operation": operation,
                    "modified": modified
                }
            }
            
            if not_found:
                result["data"]["not_found"] = not_found
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to {operation} tool results: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
