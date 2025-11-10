import inspect

from abc import abstractmethod
from dataclasses import dataclass
from nisaba import BaseTool, BaseToolResponse
from typing import Any, Callable, Dict, List, TYPE_CHECKING, get_type_hints

try:
    from docstring_parser import parse as parse_docstring
    DOCSTRING_PARSER_AVAILABLE = True
except ImportError:
    DOCSTRING_PARSER_AVAILABLE = False

if TYPE_CHECKING:
    from nisaba.factory import MCPFactory

@dataclass
class OperationParameter:
    name:str
    required:bool
    required_or:str|None
    default:Any|None
    description:str


@dataclass
class Operation:
    command:Callable
    result_formatter:Callable
    name:str
    parameters:dict[str,OperationParameter]
    description:str
    skip_render:bool=False
  
class BaseOperationTool(BaseTool):
    def __init__(self, factory:MCPFactory, nisaba=False):
        super().__init__(factory, nisaba)
        self.operations_and_parameters:dict[str,Operation] = self.get_operation_config()
    
    @classmethod
    def make_operations(cls, operations:list[Operation]) -> dict[str, Operation]:
        return dict(map(lambda operation: (operation.name, operation), operations))

    @classmethod  
    def make_operation(cls, command:Callable, result_formatter:Callable, name:str, parameters:list[OperationParameter], description:str, skip_render:bool = False) -> Operation:
        return Operation(command=command, result_formatter=result_formatter, name=name, parameters=dict(map(lambda parameter: (parameter.name, parameter), parameters)), description=description, skip_render=skip_render)
    
    @classmethod
    def make_parameter(cls, name:str, description:str, default:Any|None = None, required:bool = False, required_or:str|None = None ) -> OperationParameter:
        return OperationParameter(name=name, required=required or isinstance(required_or, str), required_or=required_or, default=default, description=description)
    
    @classmethod
    def response_invalid_operation(cls, operation:str) -> BaseToolResponse:
        return cls.response_error(message=f"Invalid operation: {operation}")
    
    @classmethod
    def response_parameter_missing(cls, operation:str, parameters:list[str]) -> BaseToolResponse:
        return cls.response_error(f"parameter(s) [{', '.join(parameters)}] required by operation `{operation}`")

    def operation(self, operation:str) -> Operation|None:
        return self.operations_and_parameters.get(operation)
    
    @classmethod
    @abstractmethod
    def get_operation_config(cls) -> Dict[str,Operation]:
        pass

    @classmethod
    @abstractmethod
    def get_tool_schema(cls) -> Dict[str, Any]:
        """
        Generate JSON schema from execute() signature and docstring.

        Returns:
            Dict containing tool name, description, and parameter schema
        """
        tool_name = cls.get_name_from_cls()

        # Get execute method
        execute_method = cls.execute
        sig = inspect.signature(execute_method)
        
        # Parse docstring
        docstring_text = execute_method.__doc__ or ""

        if DOCSTRING_PARSER_AVAILABLE and docstring_text:
            docstring = parse_docstring(docstring_text)

            # Build description
            description_parts = []
            if docstring.short_description:
                description_parts.append(docstring.short_description.strip())
            if docstring.long_description:
                description_parts.append(docstring.long_description.strip())

            description = "\n\n".join(description_parts)
        else:
            description = docstring_text.strip()

        # Build parameter schema
        properties = {}
        operation_config:Dict[str, Operation] = cls.get_operation_config()
        properties['operation'] = {
            'type': 'string',
            'enum': list(operation_config.keys())
        }
        operation_description_list:List[str] = []

        for operation in operation_config.values():
            parameter_list:List[str] = []

            for parameter in operation.parameters.values():
                if parameter not in properties:
                    properties[parameter.name] = {'type':'string', 'description':parameter.description}
          
                parameter_list.append(parameter.name)

            operation_description = ""
            if len(parameter_list):
                operation_description = f"- {operation.name}({', '.join(parameter_list)}): {operation.description}"
            else:
                operation_description = f"- {operation.name}: {operation.description}"
                
            operation_description_list.append(operation_description)
        
        if len(operation_description_list):
            description += "\n\nOperations:\n" + "\n".join(operation_description_list)
            
        return {
            "name": tool_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": ['operation']
            }
        }
    
    @abstractmethod
    async def execute(self, operation:str, **kwargs) -> BaseToolResponse:
        """
        Execute the operation tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Dict with success/error response
        """
        operation_obj = self.operation(operation)

        if operation_obj is None:
            return self.response_invalid_operation(operation)
        
        collected_parameters = {}
        missing_parameters = []
        parameters_to_visit = list(operation_obj.parameters.keys())

        while len(parameters_to_visit):
            parameter = operation_obj.parameters[parameters_to_visit.pop(0)]

            # handles or chain, needs to be sequential
            # TODO: error handling would be nice, but it is luxury
            if parameter.required and parameter.required_or is not None:
                processing_parameter_chain = True
                selected_parameter:OperationParameter|None = None
                or_chain_names = []
                while processing_parameter_chain:
                    or_chain_names.append(parameter.name)

                    if parameter.name in kwargs:
                        if selected_parameter is None:
                            selected_parameter = parameter
                            collected_parameters[parameter.name] = kwargs[parameter.name]
                                                    
                    if parameter.required_or is None:
                        # end of list
                        processing_parameter_chain = False

                        if parameter.required and selected_parameter is None:
                            missing_parameters.append(' OR '.join(or_chain_names))

                    if processing_parameter_chain:
                        parameter = operation_obj.parameters[parameters_to_visit.pop(0)]

            elif parameter.required and parameter.name not in kwargs:
                missing_parameters.append(parameter.name)

            elif parameter.name in kwargs:
                collected_parameters[parameter.name] = kwargs[parameter.name]
        
        if len(missing_parameters):
            return self.response_parameter_missing(operation=operation, parameters=missing_parameters)
        
        try:
            result = operation_obj.command(**collected_parameters)

            if not operation_obj.skip_render:
                self._render()
            
            return self.response_success(message=operation_obj.result_formatter(result))
        
        except Exception as e:
            return self.response_exception(e, f"Operation {operation} failed")

    @abstractmethod
    def _render(self) -> None:
        pass