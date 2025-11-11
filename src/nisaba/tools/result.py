from typing import Any, Dict, TYPE_CHECKING
from nisaba.tools.base_tool import BaseToolResponse
from nisaba.tools.base_operation_tool import BaseOperationTool, Operation
from nisaba.wrapper.proxy import get_request_modifier

if TYPE_CHECKING:
    from nisaba.factory import MCPFactory

class ResultTool(BaseOperationTool):
    """Manage tool result in context.messages, allowing the results to be expanded and collapsed, saving context"""

    def __init__(self, factory:"MCPFactory"):
        super().__init__(
            factory=factory
        )

    @classmethod
    def nisaba(cls) -> bool:
        return True
    
    @classmethod
    def tool_collapse_response(cls, operation:str, result:dict[str,Any]) -> BaseToolResponse:
        message = f"operation: {operation}, modified: {result['modified']}",
        return cls.response(success=True, message=message)
    
    @classmethod
    def get_operation_config(cls) -> Dict[str,Operation]:
        return cls.make_operations([
                cls.make_operation(
                    command=get_request_modifier().expand_tool_results,
                    name='expand',
                    description='Expand tool results',
                    result_formatter=cls.tool_collapse_response,
                    parameters=[
                        cls.make_parameter(name='tool_ids', required=True, description='List of tool_id')
                    ]
                ),
                cls.make_operation(
                    command=get_request_modifier().collapse_tool_results,
                    name='collapse',
                    description='Collapse tool results',
                    result_formatter=cls.tool_collapse_response,
                    parameters=[
                        cls.make_parameter(name='tool_ids', required=True, description='List of tool_id')
                    ]
                ),
                cls.make_operation(
                    command=get_request_modifier().collapse_all_tool_results,
                    name='collapse_all',
                    description='Collapse ALL tool results',
                    result_formatter=cls.tool_collapse_response,
                    parameters=[],
                    skip_render=True
                )
            ])

    def _render(self):
        pass
