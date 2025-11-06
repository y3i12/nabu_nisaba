"""
Manage tool result visibility states.
"""
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
            
            # Get reference to request_modifier from proxy
            from nisaba.wrapper.proxy import get_request_modifier
            
            request_modifier = get_request_modifier()
            if not request_modifier:
                return {
                    "success": False,
                    "error": "RequestModifier not available"
                }
            
            # Call the appropriate method
            if operation == 'close':
                result = request_modifier.close_tool_results(tool_ids)
            else:  # open
                result = request_modifier.open_tool_results(tool_ids)
            
            if not result['modified']:
                return {
                    "success": False,
                    "error": "None of the specified tool IDs found in state",
                    "not_found": result['not_found']
                }
            
            return_data = {
                "success": True,
                "data": {
                    "operation": operation,
                    "modified": result['modified']
                }
            }
            
            if result['not_found']:
                return_data["data"]["not_found"] = result['not_found']
            
            return return_data
            
        except Exception as e:
            self.logger.error(f"Failed to {operation} tool results: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
