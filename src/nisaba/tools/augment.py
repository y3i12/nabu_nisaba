from typing import Dict, Any, TYPE_CHECKING
from nisaba.tools.base_operation_tool import BaseOperationTool, Operation
from nisaba.tools.base_tool import BaseToolResponse
from nisaba.augments import get_augment_manager

if TYPE_CHECKING:
    from nisaba.factory import MCPFactory

class AugmentTool(BaseOperationTool):
    """
    Operations load, unload, (un)pin, and learn augments. 
    
    Augments live in the system prompt and they mutate how the entire context is interpreted. Think of
    augments as 'dynamic context libraries', which can contain theoretical knowledge, practical knowledge,
    memories, documentation, procedures, references, mindsets... information.
    """    
    def __init__(self, factory:"MCPFactory"):
        super().__init__(
            factory=factory
        )

    @classmethod
    def nisaba(cls) -> bool:
        return True
    
    @classmethod
    def response_augment_manager_not_present(cls) -> BaseToolResponse:
        return cls.response(success=False, message="ConfigurationError: Augments system not initialized")
    
    @classmethod
    def augment_manager_result_response(cls, result:dict[str,Any]) -> BaseToolResponse:
        message_list:list[str] = []
        for key in ('affected', 'dependencies', 'skipped'):
            message_list = cls._augment_result_append_key(result, key, message_list)

        message = ', '.join(message_list)
        return cls.response(success=True, message=message)
    
    @classmethod
    def _augment_result_append_key(cls, result:dict[str,Any], key:str, message_list:list[str]) -> list[str]:
        if key in result:
            message_list.append(f"{key} [{', '.join(result[key])}]")
        return message_list

    @classmethod
    def get_operation_config(cls) -> Dict[str,Operation]:
        return cls.make_operations([
                cls.make_operation(
                    command=get_augment_manager().activate_augments,
                    name='load',
                    description='Load augments matching patterns',
                    result_formatter=cls.augment_manager_result_response,
                    parameters=[
                        cls.make_parameter(name='patterns', required=True, description='List of patterns to match')
                    ]
                ),
                cls.make_operation(
                    command=get_augment_manager().deactivate_augments,
                    name='unload',
                    description='Unload augments matching patterns',
                    result_formatter=cls.augment_manager_result_response,
                    parameters=[
                        cls.make_parameter(name='patterns', required=True, description='List of patterns to match')
                    ]
                ),
                cls.make_operation(
                    command=get_augment_manager().pin_augment,
                    name='pin',
                    description='Pin augments matching patterns',
                    result_formatter=cls.augment_manager_result_response,
                    parameters=[
                        cls.make_parameter(name='patterns', required=True, description='List of patterns to match')
                    ],
                    skip_render=True
                ),
                cls.make_operation(
                    command=get_augment_manager().unpin_augment,
                    name='unpin',
                    description='Unpin augments matching patterns',
                    result_formatter=cls.augment_manager_result_response,
                    parameters=[
                        cls.make_parameter(name='patterns', required=True, description='List of patterns to match')
                    ],
                    skip_render=True
                ),
                cls.make_operation(
                    command=get_augment_manager().learn_augment,
                    name='store',
                    description='Store augment in group/name',
                    result_formatter=cls.augment_manager_result_response,
                    parameters=[
                        cls.make_parameter(name='group',   required=True, description= 'Augment group/category (e.g., "code_analysis")'),
                        cls.make_parameter(name='name',    required=True, description= 'Augment name (e.g., "find_circular_deps")'),
                        cls.make_parameter(name='content', required=True, description= 'Augment content in markdown format'),
                    ],
                    skip_render=True
                )
            ])

    def _render(self):
        pass