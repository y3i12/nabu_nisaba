---EDITOR_c7f44959-3ec5-4aa2-94b9-78c2b6756bc0
**file**: /home/y3i12/nabu_nisaba/src/nisaba/tools/augment.py
**lines**: 1-101 (101 lines)

1: from typing import Dict, Any, TYPE_CHECKING
2: from nisaba.tools.base_operation_tool import BaseOperationTool, Operation
3: from nisaba.tools.base_tool import BaseToolResponse
4: from nisaba.augments import get_augment_manager
5: 
6: if TYPE_CHECKING:
7:     from nisaba.factory import MCPFactory
8: 
9: class AugmentTool(BaseOperationTool):
10:     """
11:     Operations load, unload, (un)pin, and learn augments. 
12:     
13:     Augments live in the system prompt and they mutate how the entire context is interpreted. Think of
14:     augments as 'dynamic context libraries', which can contain theoretical knowledge, practical knowledge,
15:     memories, documentation, procedures, references, mindsets... information.
16:     """    
17:     def __init__(self, factory:"MCPFactory"):
18:         super().__init__(
19:             factory=factory
20:         )
21: 
22:     @classmethod
23:     def nisaba(cls) -> bool:
24:         return True
25:     
26:     @classmethod
27:     def response_augment_manager_not_present(cls) -> BaseToolResponse:
28:         return cls.response(success=False, message="ConfigurationError: Augments system not initialized")
29:     
30:     @classmethod
31:     def augment_manager_result_response(cls, result:dict[str,Any]) -> str:
32:         message_list:list[str] = []
33:         for key in ('affected', 'dependencies', 'skipped'):
34:             message_list = cls._augment_result_append_key(result, key, message_list)
35: 
36:         message = ', '.join(message_list)
37:         return message
38:     
39:     @classmethod
40:     def _augment_result_append_key(cls, result:dict[str,Any], key:str, message_list:list[str]) -> list[str]:
41:         if key in result:
42:             message_list.append(f"{key} [{', '.join(result[key])}]")
43:         return message_list
44: 
45:     @classmethod
46:     def get_operation_config(cls) -> Dict[str,Operation]:
47:         return cls.make_operations([
48:                 cls.make_operation(
49:                     command=get_augment_manager().activate_augments,
50:                     name='load',
51:                     description='Load augments matching patterns',
52:                     result_formatter=cls.augment_manager_result_response,
53:                     parameters=[
54:                         cls.make_parameter(name='patterns', required=True, description='List of patterns to match')
55:                     ]
56:                 ),
57:                 cls.make_operation(
58:                     command=get_augment_manager().deactivate_augments,
59:                     name='unload',
60:                     description='Unload augments matching patterns',
61:                     result_formatter=cls.augment_manager_result_response,
62:                     parameters=[
63:                         cls.make_parameter(name='patterns', required=True, description='List of patterns to match')
64:                     ]
65:                 ),
66:                 cls.make_operation(
67:                     command=get_augment_manager().pin_augment,
68:                     name='pin',
69:                     description='Pin augments matching patterns',
70:                     result_formatter=cls.augment_manager_result_response,
71:                     parameters=[
72:                         cls.make_parameter(name='patterns', required=True, description='List of patterns to match')
73:                     ],
74:                     skip_render=True
75:                 ),
76:                 cls.make_operation(
77:                     command=get_augment_manager().unpin_augment,
78:                     name='unpin',
79:                     description='Unpin augments matching patterns',
80:                     result_formatter=cls.augment_manager_result_response,
81:                     parameters=[
82:                         cls.make_parameter(name='patterns', required=True, description='List of patterns to match')
83:                     ],
84:                     skip_render=True
85:                 ),
86:                 cls.make_operation(
87:                     command=get_augment_manager().learn_augment,
88:                     name='store',
89:                     description='Store augment in group/name',
90:                     result_formatter=cls.augment_manager_result_response,
91:                     parameters=[
92:                         cls.make_parameter(name='group',   required=True, description= 'Augment group/category (e.g., "code_analysis")'),
93:                         cls.make_parameter(name='name',    required=True, description= 'Augment name (e.g., "find_circular_deps")'),
94:                         cls.make_parameter(name='content', required=True, description= 'Augment content in markdown format'),
95:                     ],
96:                     skip_render=True
97:                 )
98:             ])
99: 
100:     def _render(self):
101:         pass
---EDITOR_04fb0ca0-08ad-4b18-ad2b-710a0aa8d97d
**file**: /home/y3i12/nabu_nisaba/src/nisaba/tools/base_operation_tool.py
**lines**: 1-229 (229 lines)

1: import inspect
2: 
3: from abc import abstractmethod
4: from dataclasses import dataclass
5: from nisaba.tools.base_tool import BaseTool, BaseToolResponse
6: from typing import Any, Callable, Dict, List, TYPE_CHECKING, get_type_hints
7: 
8: try:
9:     from docstring_parser import parse as parse_docstring
10:     DOCSTRING_PARSER_AVAILABLE = True
11: except ImportError:
12:     DOCSTRING_PARSER_AVAILABLE = False
13: 
14: if TYPE_CHECKING:
15:     from nisaba.factory import MCPFactory
16: 
17: @dataclass(unsafe_hash=True)
18: class OperationParameter:
19:     name:str
20:     required:bool
21:     required_or:str|None
22:     default:Any|None
23:     description:str
24: 
25: 
26: @dataclass(unsafe_hash=True)
27: class Operation:
28:     command:Callable
29:     result_formatter:Callable
30:     name:str
31:     parameters:dict[str,OperationParameter]
32:     description:str
33:     skip_render:bool=False
34:   
35: class BaseOperationTool(BaseTool):
36:     def __init__(self, factory:"MCPFactory"):
37:         super().__init__(factory)
38:         self.operations_and_parameters:dict[str,Operation] = self.get_operation_config()
39:     
40:     @classmethod
41:     def make_operations(cls, operations:list[Operation]) -> dict[str, Operation]:
42:         return dict(map(lambda operation: (operation.name, operation), operations))
43: 
44:     @classmethod  
45:     def make_operation(cls, command:Callable, result_formatter:Callable, name:str, parameters:list[OperationParameter], description:str, skip_render:bool = False) -> Operation:
46:         return Operation(command=command, result_formatter=result_formatter, name=name, parameters=dict(map(lambda parameter: (parameter.name, parameter), parameters)), description=description, skip_render=skip_render)
47:     
48:     @classmethod
49:     def make_parameter(cls, name:str, description:str, default:Any|None = None, required:bool = False, required_or:str|None = None ) -> OperationParameter:
50:         return OperationParameter(name=name, required=required or isinstance(required_or, str), required_or=required_or, default=default, description=description)
51:     
52:     @classmethod
53:     def response_invalid_operation(cls, operation:str) -> BaseToolResponse:
54:         return cls.response_error(message=f"Invalid operation: {operation}")
55:     
56:     @classmethod
57:     def response_missing_operation(cls) -> BaseToolResponse:
58:         return cls.response_error(message=f"Missing operation")
59:     
60:     @classmethod
61:     def response_parameter_missing(cls, operation:str, parameters:list[str]) -> BaseToolResponse:
62:         return cls.response_error(f"parameter(s) [{', '.join(parameters)}] required by operation `{operation}`")
63:  
64:     @classmethod
65:     def _format_str(cls, _str:str) -> str:
66:         return f"{_str}"
67:     
68:     @classmethod
69:     def _format_ok(cls, ok:bool) -> str:
70:         if ok:
71:             return "ok"
72:         
73:         return "not ok and shouldn't happen"
74:     
75:     @classmethod
76:     def get_operation_config(cls) -> Dict[str,Operation]:
77:         """
78:         Needs override
79:         """
80:         return {}
81: 
82:     @classmethod
83:     def get_tool_schema(cls) -> Dict[str, Any]:
84:         """
85:         Generate JSON schema from execute() signature and docstring.
86: 
87:         Returns:
88:             Dict containing tool name, description, and parameter schema
89:         """
90:         tool_name = cls.get_name_from_cls()
91: 
92:         # Parse docstring
93:         docstring_text = cls.__doc__ or ""
94: 
95:         if DOCSTRING_PARSER_AVAILABLE and docstring_text:
96:             docstring = parse_docstring(docstring_text)
97: 
98:             # Build description
99:             description_parts = []
100:             if docstring.short_description:
101:                 description_parts.append(docstring.short_description.strip())
102:             if docstring.long_description:
103:                 description_parts.append(docstring.long_description.strip())
104: 
105:             description = "\n\n".join(description_parts)
106:         else:
107:             description = docstring_text.strip()
108: 
109:         # Build parameter schema
110:         properties = {}
111:         operation_config:Dict[str, Operation] = cls.get_operation_config()
112:         properties['operation'] = {
113:             'type': 'string',
114:             'enum': list(operation_config.keys())
115:         }
116:         operation_description_list:List[str] = []
117: 
118:         for operation in operation_config.values():
119:             parameter_list:List[str] = []
120: 
121:             for parameter_name in operation.parameters.keys():
122:                 parameter:OperationParameter = operation.parameters[parameter_name]
123:                 if parameter not in properties:
124:                     properties[parameter.name] = {'type':'string', 'description':parameter.description}
125:           
126:                 parameter_list.append(parameter.name)
127: 
128:             operation_description = ""
129:             if len(parameter_list):
130:                 operation_description = f"- {operation.name}({', '.join(parameter_list)}): {operation.description}"
131:             else:
132:                 operation_description = f"- {operation.name}: {operation.description}"
133:                 
134:             operation_description_list.append(operation_description)
135:         
136:         if len(operation_description_list):
137:             description += "\n\nOperations:\n" + "\n".join(operation_description_list)
138: 
139:         return {
140:             "name": tool_name,
141:             "description": description,
142:             "parameters": {
143:                 "type": "object",
144:                 "properties": properties,
145:                 "required": ['operation']
146:             }
147:         }
148:     
149:     def operation(self, operation:str) -> Operation|None:
150:         return self.operations_and_parameters.get(operation)
151:    
152:     async def execute(self, **kwargs) -> BaseToolResponse:
153:         operation = kwargs.get('operation', None)
154:         if operation is None:
155:             return self.response_missing_operation()
156: 
157:         # Remove 'operation' from kwargs to avoid duplicate argument error
158:         params = {k: v for k, v in kwargs.items() if k != 'operation'}
159:         return self._execute(operation=str(operation), **params)
160:     
161:     def _execute(self, operation:str, **kwargs) -> BaseToolResponse:
162:         """
163:         Execute the operation tool with given parameters.
164: 
165:         Args:
166:             **kwargs: Tool-specific parameters
167: 
168:         Returns:
169:             Dict with success/error response
170:         """
171:         operation_obj = self.operation(operation)
172: 
173:         if operation_obj is None:
174:             return self.response_invalid_operation(operation)
175:         
176:         collected_parameters = {}
177:         missing_parameters = []
178:         parameters_to_visit = list(operation_obj.parameters.keys())
179: 
180:         while len(parameters_to_visit):
181:             parameter = operation_obj.parameters[parameters_to_visit.pop(0)]
182: 
183:             # handles or chain, needs to be sequential
184:             # TODO: error handling would be nice, but it is luxury
185:             if parameter.required and parameter.required_or is not None:
186:                 processing_parameter_chain = True
187:                 selected_parameter:OperationParameter|None = None
188:                 or_chain_names = []
189:                 while processing_parameter_chain:
190:                     or_chain_names.append(parameter.name)
191: 
192:                     if parameter.name in kwargs:
193:                         if selected_parameter is None:
194:                             selected_parameter = parameter
195:                             collected_parameters[parameter.name] = kwargs[parameter.name]
196:                                                     
197:                     if parameter.required_or is None:
198:                         # end of list
199:                         processing_parameter_chain = False
200: 
201:                         if parameter.required and selected_parameter is None:
202:                             missing_parameters.append(' OR '.join(or_chain_names))
203: 
204:                     if processing_parameter_chain:
205:                         parameter = operation_obj.parameters[parameters_to_visit.pop(0)]
206: 
207:             elif parameter.required and parameter.name not in kwargs:
208:                 missing_parameters.append(parameter.name)
209: 
210:             elif parameter.name in kwargs:
211:                 collected_parameters[parameter.name] = kwargs[parameter.name]
212:         
213:         if len(missing_parameters):
214:             return self.response_parameter_missing(operation=operation, parameters=missing_parameters)
215:         
216:         try:
217:             result = operation_obj.command(**collected_parameters)
218: 
219:             if not operation_obj.skip_render:
220:                 self._render()
221:             
222:             return self.response_success(message=operation_obj.result_formatter(result))
223:         
224:         except Exception as e:
225:             return self.response_exception(e, f"Operation {operation} failed")
226: 
227:     @abstractmethod
228:     def _render(self) -> None:
229:         pass
---EDITOR_7fe2e26c-f68a-4426-bca6-3c984e188e52
**file**: /home/y3i12/nabu_nisaba/src/nisaba/tools/base_tool.py
**lines**: 1-458 (458 lines)

1: """Abstract base class for MCP tools."""
2: 
3: import inspect
4: import logging
5: import time
6: 
7: from abc import ABC, abstractmethod
8: from dataclasses import dataclass
9: from typing import Any, Dict, Optional, TYPE_CHECKING, get_type_hints
10: 
11: try:
12:     from docstring_parser import parse as parse_docstring
13:     DOCSTRING_PARSER_AVAILABLE = True
14: except ImportError:
15:     DOCSTRING_PARSER_AVAILABLE = False
16: 
17: 
18: if TYPE_CHECKING:
19:     from nisaba.factory import MCPFactory
20: 
21: @dataclass
22: class BaseToolResponse:
23:     """Metadata for a nisaba certified return"""
24:     success:bool = False
25:     message:Any = None
26:     nisaba:bool = False
27: 
28: class BaseTool(ABC):
29:     """
30:     Abstract base class for all MCP tools.
31: 
32:     Each tool must implement:
33:     - execute(**kwargs) -> Dict[str, Any]: The main tool logic
34:     """
35: 
36:     def __init__(self, factory:"MCPFactory"):
37:         """
38:         Initialize tool with factory reference.
39: 
40:         Args:
41:             factory: The MCPFactory that created this tool
42:         """
43:         self.factory:"MCPFactory" = factory
44:         self.config = None
45:         if factory:
46:             self.config = factory.config
47:     
48:     @classmethod
49:     def logger(cls):
50:         return  logging.getLogger(f"{cls.__module__}.{cls.get_name()}")
51: 
52:     @classmethod
53:     def get_name_from_cls(cls) -> str:
54:         """
55:         Get tool name from class name.
56: 
57:         Converts class name like "QueryTool" to "query".
58: 
59:         Returns:
60:             Tool name in snake_case
61:         """
62:         name = cls.__name__
63:         if name.endswith("Tool"):
64:             name = name[:-4]
65:         # Convert to snake_case
66:         name = "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")
67:         return name
68: 
69:     @classmethod
70:     def get_name(cls) -> str:
71:         """Get instance tool name."""
72:         return cls.get_name_from_cls()
73: 
74:     @classmethod
75:     @abstractmethod
76:     def nisaba(cls) -> bool:
77:         return False
78:     
79:     @classmethod
80:     def get_tool_schema(cls) -> Dict[str, Any]:
81:         """
82:         Generate JSON schema from execute() signature and docstring.
83: 
84:         Returns:
85:             Dict containing tool name, description, and parameter schema
86:         """
87:         tool_name = cls.get_name_from_cls()
88: 
89:         # Get execute method
90:         execute_method = cls.execute
91:         sig = inspect.signature(execute_method)
92:         
93:         # Parse docstring
94:         docstring_text = execute_method.__doc__ or ""
95: 
96:         if DOCSTRING_PARSER_AVAILABLE and docstring_text:
97:             docstring = parse_docstring(docstring_text)
98: 
99:             # Build description
100:             description_parts = []
101:             if docstring.short_description:
102:                 description_parts.append(docstring.short_description.strip())
103:             if docstring.long_description:
104:                 description_parts.append(docstring.long_description.strip())
105: 
106:             description = "\n\n".join(description_parts)
107: 
108:             # Build param description map
109:             param_descriptions = {
110:                 param.arg_name: param.description
111:                 for param in docstring.params
112:                 if param.description
113:             }
114:         else:
115:             description = docstring_text.strip()
116:             param_descriptions = {}
117: 
118:         # Build parameter schema
119:         properties = {}
120:         required = []
121:         type_hints = get_type_hints(execute_method)
122: 
123:         for param_name, param in sig.parameters.items():
124:             if param_name in ["self", "kwargs"]:
125:                 continue
126: 
127:             # Get type annotation
128:             param_type = type_hints.get(param_name, Any)
129:             json_type = cls._python_type_to_json_type(param_type)
130: 
131:             # Get description from docstring
132:             param_desc = param_descriptions.get(param_name, "")
133: 
134:             # Build parameter schema entry
135:             param_schema = {"type": json_type}
136: 
137:             if param_desc:
138:                 param_schema["description"] = param_desc.strip()
139: 
140:             # Add default value if available
141:             if param.default != inspect.Parameter.empty:
142:                 try:
143:                     import json
144:                     json.dumps(param.default)
145:                     param_schema["default"] = param.default
146:                 except (TypeError, ValueError):
147:                     pass
148:             else:
149:                 required.append(param_name)
150: 
151:             properties[param_name] = param_schema
152: 
153:         return {
154:             "name": tool_name,
155:             "description": description,
156:             "parameters": {
157:                 "type": "object",
158:                 "properties": properties,
159:                 "required": required
160:             }
161:         }
162: 
163:     @classmethod
164:     def get_tool_description(cls) -> str:
165:         """
166:         Get human-readable tool description.
167: 
168:         Returns:
169:             Description string extracted from docstrings
170:         """
171:         execute_doc = cls.execute.__doc__ or ""
172: 
173:         if DOCSTRING_PARSER_AVAILABLE and execute_doc:
174:             docstring = parse_docstring(execute_doc)
175:             return docstring.short_description or cls.__doc__ or ""
176: 
177:         if execute_doc:
178:             return execute_doc.strip().split('\n')[0]
179:         return cls.__doc__ or ""
180:     
181:     @abstractmethod
182:     async def execute(self, **kwargs) -> BaseToolResponse:
183:         """
184:         Execute the tool with given parameters.
185: 
186:         Args:
187:             **kwargs: Tool-specific parameters
188: 
189:         Returns:
190:             BaseToolResponse
191:         """
192:         pass
193: 
194:     def _record_guidance(self, tool_name: str, params: Dict[str, Any], result: Dict[str, Any]) -> None:
195:         """
196:         Record tool call in guidance system and add suggestions to result.
197: 
198:         This method can be called by subclasses that override execute_with_timing().
199:         Modifies result dict in-place to add _guidance field if suggestions available.
200: 
201:         Args:
202:             tool_name: Name of the tool that was executed
203:             params: Parameters passed to the tool
204:             result: Result dict (modified in-place)
205:         """
206:         if hasattr(self.factory, 'guidance') and self.factory.guidance is not None:
207:             try:
208:                 self.factory.guidance.record_tool_call(
209:                     tool_name=tool_name,
210:                     params=params,
211:                     result=result
212:                 )
213: 
214:                 # Optionally add suggestions to result metadata
215:                 suggestions = self.factory.guidance.get_suggestions()
216:                 if suggestions:
217:                     result["_guidance"] = suggestions
218: 
219:             except Exception as guidance_error:
220:                 # Don't fail tool execution if guidance fails
221:                 self.logger().warning(f"Guidance tracking failed: {guidance_error}")
222: 
223:     async def execute_with_timing(self, **kwargs) -> Dict[str, Any]:
224:         """
225:         Execute tool with automatic timing and error handling.
226: 
227:         Wrapper around execute() that adds timing and optional guidance tracking.
228: 
229:         Args:
230:             **kwargs: Tool-specific parameters
231: 
232:         Returns:
233:             Tool execution result with timing and optional guidance metadata
234:         """
235:         start_time = time.time()
236: 
237:         try:
238:             result = await self.execute(**kwargs)
239: 
240:             # Record in guidance system (subclasses can also call this)
241:             self._record_guidance(self.get_name(), kwargs, result)
242: 
243:             return result
244: 
245:         except Exception as e:
246:             self.logger().error(f"Tool execution failed: {e}", exc_info=True)
247:             return {
248:                 "success": False,
249:                 "error": str(e),
250:                 "error_type": type(e).__name__
251:             }
252: 
253:     @classmethod
254:     def is_optional(cls) -> bool:
255:         """
256:         Check if tool is optional (disabled by default).
257: 
258:         Returns:
259:             True if tool is optional
260:         """
261:         from ..markers import ToolMarkerOptional
262:         return issubclass(cls, ToolMarkerOptional)
263: 
264:     @classmethod
265:     def is_dev_only(cls) -> bool:
266:         """
267:         Check if tool is development-only.
268: 
269:         Returns:
270:             True if tool is dev-only
271:         """
272:         from ..markers import ToolMarkerDevOnly
273:         return issubclass(cls, ToolMarkerDevOnly)
274: 
275:     @classmethod
276:     def is_mutating(cls) -> bool:
277:         """
278:         Check if tool modifies state.
279: 
280:         Returns:
281:             True if tool mutates state
282:         """
283:         from ..markers import ToolMarkerMutating
284:         return issubclass(cls, ToolMarkerMutating)
285: 
286:     @classmethod
287:     def _get_meta_field(cls, field_name: str) -> Optional[str]:
288:         """
289:         Extract a :meta field: from execute() docstring.
290: 
291:         Args:
292:             field_name: Name of meta field (e.g., 'pitch', 'examples')
293: 
294:         Returns:
295:             Field description or None
296:         """
297:         execute_doc = cls.execute.__doc__ or ""
298: 
299:         if not DOCSTRING_PARSER_AVAILABLE or not execute_doc:
300:             return None
301: 
302:         docstring = parse_docstring(execute_doc)
303: 
304:         # Look for :meta field_name: field
305:         if hasattr(docstring, 'meta') and docstring.meta:
306:             for meta in docstring.meta:
307:                 if hasattr(meta, 'args') and len(meta.args) >= 2:
308:                     if meta.args[0] == 'meta' and meta.args[1] == field_name:
309:                         return meta.description
310: 
311:         return None
312: 
313:     @classmethod
314:     def get_tool_pitch(cls) -> Optional[str]:
315:         """
316:         Get brief, inciting tool pitch for instructions.
317: 
318:         Extracts the :meta pitch: field from execute() docstring.
319:         Falls back to short_description if no pitch provided.
320: 
321:         Returns:
322:             Brief pitch string or None
323:         """
324:         pitch = cls._get_meta_field('pitch')
325:         if pitch:
326:             return pitch
327: 
328:         # Fallback to short description
329:         execute_doc = cls.execute.__doc__ or ""
330:         if DOCSTRING_PARSER_AVAILABLE and execute_doc:
331:             docstring = parse_docstring(execute_doc)
332:             return docstring.short_description
333: 
334:         return None
335: 
336:     @classmethod
337:     def get_tool_examples(cls) -> Optional[str]:
338:         """
339:         Get usage examples for this tool.
340: 
341:         Extracts the :meta examples: field from execute() docstring.
342: 
343:         Returns:
344:             Markdown-formatted examples or None
345:         """
346:         return cls._get_meta_field('examples')
347: 
348:     @classmethod
349:     def get_tool_tips(cls) -> Optional[str]:
350:         """
351:         Get best practices and tips for using this tool.
352: 
353:         Extracts the :meta tips: field from execute() docstring.
354: 
355:         Returns:
356:             Markdown-formatted tips or None
357:         """
358:         return cls._get_meta_field('tips')
359: 
360:     @classmethod
361:     def get_tool_patterns(cls) -> Optional[str]:
362:         """
363:         Get common usage patterns for this tool.
364: 
365:         Extracts the :meta patterns: field from execute() docstring.
366: 
367:         Returns:
368:             Markdown-formatted patterns or None
369:         """
370:         return cls._get_meta_field('patterns')
371: 
372:     # UTILITY METHODS
373:     @classmethod
374:     def _python_type_to_json_type(cls, python_type: Any) -> str:
375:         """
376:         Convert Python type hint to JSON schema type.
377: 
378:         Args:
379:             python_type: Python type annotation
380: 
381:         Returns:
382:             JSON schema type string
383:         """
384:         # Handle string representations
385:         if isinstance(python_type, str):
386:             type_str = python_type.lower()
387:             if 'str' in type_str:
388:                 return "string"
389:             elif 'int' in type_str:
390:                 return "integer"
391:             elif 'float' in type_str or 'number' in type_str:
392:                 return "number"
393:             elif 'bool' in type_str:
394:                 return "boolean"
395:             elif 'list' in type_str or 'sequence' in type_str:
396:                 return "array"
397:             elif 'dict' in type_str:
398:                 return "object"
399:             return "string"
400: 
401:         # Get the origin for generic types
402:         origin = getattr(python_type, '__origin__', None)
403: 
404:         # Handle None/NoneType
405:         if python_type is type(None):
406:             return "null"
407: 
408:         # Direct type mappings
409:         type_map = {
410:             str: "string",
411:             int: "integer",
412:             float: "number",
413:             bool: "boolean",
414:             list: "array",
415:             dict: "object",
416:         }
417: 
418:         if python_type in type_map:
419:             return type_map[python_type]
420: 
421:         # Handle Optional, Union, List, Dict, etc.
422:         if origin is not None:
423:             if origin in (list, tuple):
424:                 return "array"
425:             elif origin is dict:
426:                 return "object"
427:             elif hasattr(python_type, '__args__'):
428:                 # For Union types, try first non-None type
429:                 for arg in python_type.__args__:
430:                     if arg is not type(None):
431:                         return cls._python_type_to_json_type(arg)
432: 
433:         # Default to string for unknown types
434:         return "string"
435:     
436:     # CONVENIANCE TOOL RETURN METHODS
437:     @classmethod
438:     def response(cls, success:bool = False, message:Any = None) -> BaseToolResponse:
439:         """Return response."""
440:         return BaseToolResponse(success=success, message=message, nisaba=cls.nisaba())
441:     
442:     @classmethod
443:     def response_success(cls, message:Any = None) -> BaseToolResponse:
444:         """Return error response."""
445:         return cls.response(success=True, message=message)
446:     
447:     @classmethod
448:     def response_error(cls, message:Any = None, exc_info:bool=False) -> BaseToolResponse:
449:         """Return error response."""
450:         cls.logger().error(message, exc_info=exc_info)
451:         return cls.response(success=False, message=message)
452:     
453:     @classmethod
454:     def response_exception(cls, e:Exception, message:Any = None) -> BaseToolResponse:
455:         """Return exception response."""
456:         error_message =  f"{message} - {type(e).__name__}: {str(e)}"
457:         return cls.response_error(message=error_message, exc_info=True)
458: 
---EDITOR_400a1dfa-dfd5-42ec-b279-0d07f666dc9f
**file**: /home/y3i12/nabu_nisaba/src/nisaba/augments.py
**lines**: 1-649 (649 lines)

1: """
2: Augments management system for dynamic context loading.
3: 
4: Provides functionality to load/unload augment files (markdown-based knowledge units)
5: and compose them for injection into Claude Code's system prompt.
6: """
7: 
8: import re
9: import logging
10: from pathlib import Path
11: from dataclasses import dataclass, field
12: from typing import Dict, List, Set, Optional, Tuple
13: from nisaba.structured_file import JsonStructuredFile
14: 
15: logger = logging.getLogger(__name__)
16: 
17: 
18: @dataclass
19: class Augment:
20:     """
21:     Represents a parsed augment.
22: 
23:     Attributes:
24:         group: Augment group/category (e.g., "dead_code_detection")
25:         name: Augment name (e.g., "find_unreferenced_callables")
26:         path: Full path identifier "group/name"
27:         content: The augment content (description, examples, queries, etc.)
28:         tools: List of tool names mentioned in TOOLS section
29:         requires: List of dependency augment paths (group/name format)
30:         file_path: Source file path for this augment
31:     """
32:     group: str
33:     name: str
34:     path: str
35:     content: str
36:     tools: List[str] = field(default_factory=list)
37:     requires: List[str] = field(default_factory=list)
38:     file_path: Optional[Path] = None
39: 
40:     @property
41:     def display_name(self) -> str:
42:         """Get display name for this augment."""
43:         return f"{self.group}/{self.name}"
44: 
45: # Module-level singleton
46: _AUGMENT_MANAGER_INSTANCE = None
47: 
48: def get_augment_manager():
49:     """Get/Set shared AugmentManager singleton."""
50:     global _AUGMENT_MANAGER_INSTANCE
51:     if _AUGMENT_MANAGER_INSTANCE:
52:         return _AUGMENT_MANAGER_INSTANCE
53:     
54:     augments_dir = Path.cwd() / ".nisaba" / "augments"
55:     composed_file = Path.cwd() / '.nisaba' / 'tui' / 'augment_view.md'
56: 
57:     _AUGMENT_MANAGER_INSTANCE = AugmentManager(augments_dir=augments_dir, composed_file=composed_file)
58:     return _AUGMENT_MANAGER_INSTANCE
59: 
60: class AugmentManager:
61:     """
62:     Manages augments lifecycle: loading, activation, composition.
63: 
64:     Augments are markdown files stored in a directory structure:
65:     {augments_dir}/{group_name}/{augment_name}.md
66: 
67:     Active augments are composed into a single markdown file that gets
68:     injected into Claude's context via the proxy.
69:     """
70: 
71:     def __init__(self, augments_dir: Path, composed_file: Path):
72:         """
73:         Initialize augments manager.
74: 
75:         Args:
76:             augments_dir: Directory containing augment files
77:             composed_file: Path to composed augments output file
78:         """        
79:         self.augments_dir = Path(augments_dir)
80:         self.composed_file = Path(composed_file)
81: 
82:         # All available augments (loaded from disk)
83:         self.available_augments: Dict[str, Augment] = {}
84: 
85:         # Currently active augments
86:         self.active_augments: Set[str] = set()
87: 
88:         # Pinned augments (always active, cannot be deactivated)
89:         self.pinned_augments: Set[str] = set()
90: 
91:         # Tool association map (for guidance integration)
92:         # Maps tool_name -> [augment_paths that mention it]
93:         self._tool_associations: Dict[str, List[str]] = {}
94: 
95:         # Cached augment tree (for system prompt injection)
96: 
97:         # Load available augments from disk
98:         self._load_augments_from_dir()
99:         
100:         # Use JsonStructuredFile for atomic state persistence
101:         self._state_file = JsonStructuredFile(
102:             file_path=self.state_file,
103:             name="augment_state",
104:             default_factory=lambda: {
105:                 "active_augments": [],
106:                 "pinned_augments": []
107:             }
108:         )
109: 
110:         self.load_state()
111: 
112:     @property
113:     def state_file(self) -> Path:
114:         """Path to state persistence file."""
115:         return Path.cwd() / '.nisaba' / 'tui' /  'augment_state.json'
116: 
117:     def save_state(self) -> None:
118:         """Save active and pinned augments to JSON using atomic operations."""
119:         state = {
120:             "active_augments": sorted(self.active_augments),
121:             "pinned_augments": sorted(self.pinned_augments)
122:         }
123: 
124:         # Use JsonStructuredFile for atomic write with locking
125:         self._state_file.write_json(state)
126:         logger.debug(f"Saved {len(self.active_augments)} active, {len(self.pinned_augments)} pinned augments to state file")
127: 
128:     def load_state(self) -> None:
129:         """Restore active and pinned augments from JSON using cached operations."""
130:         state = self._state_file.load_json()
131:         
132:         # Restore pinned augments first
133:         pinned = state.get("pinned_augments", [])
134:         for aug_path in pinned:
135:             if aug_path in self.available_augments:
136:                 self.pinned_augments.add(aug_path)
137:             else:
138:                 logger.warning(f"Skipping unavailable pinned augment: {aug_path}")
139:         
140:         # Restore active augments
141:         active = state.get("active_augments", [])
142:         for aug_path in active:
143:             if aug_path in self.available_augments:
144:                 self.active_augments.add(aug_path)
145:             else:
146:                 logger.warning(f"Skipping unavailable augment: {aug_path}")
147:         
148:         # Auto-activate pinned augments (merge into active set)
149:         self.active_augments.update(self.pinned_augments)
150:         
151:         # Rebuild tool associations and compose
152:         if self.active_augments:
153:             self._rebuild_tool_associations()
154:             self._compose_and_write()
155:         
156:         logger.info(f"Restored {len(self.active_augments)} active augments ({len(self.pinned_augments)} pinned) from state file")
157: 
158:     def _load_augments_from_dir(self) -> None:
159:         """Load all augment files from augments directory."""
160:         if not self.augments_dir.exists():
161:             logger.warning(f"Augments directory does not exist: {self.augments_dir}")
162:             return
163: 
164:         # Find all .md files in augments_dir
165:         for augment_file in self.augments_dir.rglob("*.md"):
166:             try:
167:                 augment = self._parse_augment_file(augment_file)
168:                 self.available_augments[augment.path] = augment
169:                 logger.debug(f"Loaded augment: {augment.path}")
170:             except Exception as e:
171:                 logger.warning(f"Failed to parse augment file {augment_file}: {e}")
172: 
173:         # Update augment tree cache after loading
174:         self._update_augment_tree_cache()
175: 
176:     def _parse_augment_file(self, file_path: Path) -> Augment:
177:         """
178:         Parse an augment markdown file.
179: 
180:         Expected format:
181:         # {group_name}
182:         ## {augment_name}
183:         Path: {group}/{name}
184: 
185:         {content}
186: 
187:         ## TOOLS
188:         - tool1()
189:         - tool2()
190: 
191:         ## REQUIRES
192:         - group/augment1
193:         - group/augment2
194: 
195:         Args:
196:             file_path: Path to augment file
197: 
198:         Returns:
199:             Parsed Augment object
200:         """
201:         content = file_path.read_text(encoding='utf-8')
202: 
203:         # Extract group and name from path
204:         # e.g., augments/dead_code_detection/find_unreferenced.md
205:         relative_path = file_path.relative_to(self.augments_dir)
206:         parts = relative_path.parts
207: 
208:         if len(parts) < 2:
209:             raise ValueError(f"Invalid augment file structure: {relative_path}")
210: 
211:         group = parts[0]
212:         name = parts[-1].replace('.md', '')
213:         path = f"{group}/{name}"
214: 
215:         # Extract TOOLS section
216:         tools = []
217:         tools_match = re.search(r'## TOOLS\s*\n((?:- .+\n?)+)', content, re.MULTILINE)
218:         if tools_match:
219:             tools_text = tools_match.group(1)
220:             # Extract tool names (remove - and () if present)
221:             tools = [
222:                 re.sub(r'\(\)', '', line.strip('- \n'))
223:                 for line in tools_text.split('\n')
224:                 if line.strip().startswith('-')
225:             ]
226: 
227:         # Extract REQUIRES section
228:         requires = []
229:         requires_match = re.search(r'## REQUIRES\s*\n((?:- .+\n?)+)', content, re.MULTILINE)
230:         if requires_match:
231:             requires_text = requires_match.group(1)
232:             requires = [
233:                 line.strip('- \n')
234:                 for line in requires_text.split('\n')
235:                 if line.strip().startswith('-')
236:             ]
237: 
238:         # Extract main content (everything before TOOLS section)
239:         if tools_match:
240:             main_content = content[:tools_match.start()].strip()
241:         else:
242:             main_content = content.strip()
243: 
244:         return Augment(
245:             group=group,
246:             name=name,
247:             path=path,
248:             content=main_content,
249:             tools=tools,
250:             requires=requires,
251:             file_path=file_path
252:         )
253: 
254:     def show_augments(self) -> Dict[str, List[str]]:
255:         """
256:         List all available augments grouped by category.
257: 
258:         Returns:
259:             Dict mapping group_name -> [augment_names]
260:         """
261:         grouped: Dict[str, List[str]] = {}
262: 
263:         for augment_path, augment in self.available_augments.items():
264:             if augment.group not in grouped:
265:                 grouped[augment.group] = []
266:             grouped[augment.group].append(augment.name)
267: 
268:         return grouped
269: 
270:     def _generate_augment_tree(self) -> str:
271:         """
272:         Generate tree representation of ALL available augments.
273: 
274:         Pinned augments are marked with 📌 indicator.
275: 
276:         Returns:
277:             Formatted string showing augment hierarchy
278:         """
279:         augments_dict = self.show_augments()
280: 
281:         if not augments_dict:
282:             return "# available augments: (none)"
283: 
284:         lines = ["# available augments"]
285:         for group in sorted(augments_dict.keys()):
286:             lines.append(f"  {group}/")
287:             for augment_name in sorted(augments_dict[group]):
288:                 augment_path = f"{group}/{augment_name}"
289:                 pin_indicator = " 📌" if augment_path in self.pinned_augments else ""
290:                 lines.append(f"    - {augment_name}{pin_indicator}")
291: 
292:         return "\n".join(lines)
293: 
294:     def _update_augment_tree_cache(self) -> None:
295:         """Update cached augment tree representation."""
296:         self._cached_augment_tree = self._generate_augment_tree()
297:         logger.debug(f"Updated augment tree cache: {len(self.available_augments)} augments")
298: 
299:     def activate_augments(
300:         self,
301:         patterns: List[str],
302:         exclude: List[str] = []
303:     ) -> Dict[str, List[str]]:
304:         """
305:         Activate augments matching patterns.
306: 
307:         Supports wildcards:
308:         - "group/*" - all augments in group
309:         - "group/augment_name" - specific augment
310:         - "*" or "**/*" - all augments
311: 
312:         Args:
313:             patterns: List of patterns to match
314:             exclude: List of patterns to exclude
315: 
316:         Returns:
317:             Dict with 'affected', 'dependencies'
318:         """
319:         to_activate: Set[str] = set()
320: 
321:         # Match patterns
322:         for pattern in patterns:
323:             matched = self._match_pattern(pattern)
324:             to_activate.update(matched)
325: 
326:         # Remove excluded
327:         for exclude_pattern in exclude:
328:             excluded = self._match_pattern(exclude_pattern)
329:             to_activate -= excluded
330: 
331:         # Resolve dependencies
332:         with_deps = self._resolve_dependencies(list(to_activate))
333: 
334:         # Separate direct loads from dependencies
335:         dependencies = set(with_deps) - to_activate
336: 
337:         # Update active augments
338:         self.active_augments.update(with_deps)
339: 
340:         # Update tool associations
341:         self._rebuild_tool_associations()
342: 
343:         # Compose and write
344:         self._compose_and_write()
345:         
346:         # Save state
347:         self.save_state()
348: 
349:         return {
350:             'affected': sorted(to_activate),
351:             'dependencies': sorted(dependencies)
352:         }
353: 
354:     def deactivate_augments(self, patterns: List[str]) -> Dict[str, List[str]]:
355:         """
356:         Deactivate augments matching patterns.
357: 
358:         Pinned augments cannot be deactivated and are silently skipped.
359: 
360:         Args:
361:             patterns: List of patterns to match
362: 
363:         Returns:
364:             Dict with 'unloaded' and 'skipped' lists
365:         """
366:         to_deactivate: Set[str] = set()
367: 
368:         for pattern in patterns:
369:             matched = self._match_pattern(pattern)
370:             # Only deactivate if currently active
371:             to_deactivate.update(matched & self.active_augments)
372: 
373:         # Separate pinned from deactivatable
374:         pinned_skipped = to_deactivate & self.pinned_augments
375:         to_deactivate -= self.pinned_augments
376: 
377:         # Remove from active
378:         self.active_augments -= to_deactivate
379: 
380:         # Rebuild tool associations
381:         self._rebuild_tool_associations()
382: 
383:         # Compose and write
384:         self._compose_and_write()
385: 
386:         # Save state
387:         self.save_state()
388: 
389:         return {
390:             'affected': sorted(to_deactivate),
391:             'skipped': sorted(pinned_skipped)
392:         }
393: 
394:     def pin_augment(self, patterns: List[str]) -> Dict[str, List[str]]:
395:         """
396:         Pin augments matching patterns (always active, cannot be deactivated).
397: 
398:         Args:
399:             patterns: List of patterns to match
400: 
401:         Returns:
402:             Dict with 'affected' list
403:         """
404:         to_pin: Set[str] = set()
405: 
406:         for pattern in patterns:
407:             matched = self._match_pattern(pattern)
408:             to_pin.update(matched)
409: 
410:         # Add to pinned set
411:         self.pinned_augments.update(to_pin)
412: 
413:         # Ensure pinned augments are active
414:         self.active_augments.update(to_pin)
415: 
416:         # Rebuild tool associations
417:         self._rebuild_tool_associations()
418: 
419:         # Compose and write
420:         self._compose_and_write()
421: 
422:         # Save state
423:         self.save_state()
424: 
425:         # Update augment tree cache (to show pin indicators)
426:         self._update_augment_tree_cache()
427: 
428:         return {
429:             'affected': sorted(to_pin)
430:         }
431: 
432:     def unpin_augment(self, patterns: List[str]) -> Dict[str, List[str]]:
433:         """
434:         Unpin augments matching patterns (allows deactivation).
435: 
436:         Note: Does not deactivate the augments, just removes pin protection.
437: 
438:         Args:
439:             patterns: List of patterns to match
440: 
441:         Returns:
442:             Dict with 'affected' list
443:         """
444:         to_unpin: Set[str] = set()
445: 
446:         for pattern in patterns:
447:             matched = self._match_pattern(pattern)
448:             # Only unpin if currently pinned
449:             to_unpin.update(matched & self.pinned_augments)
450: 
451:         # Remove from pinned set
452:         self.pinned_augments -= to_unpin
453: 
454:         # Save state
455:         self.save_state()
456: 
457:         # Update augment tree cache (to remove pin indicators)
458:         self._update_augment_tree_cache()
459: 
460:         return {
461:             'affected': sorted(to_unpin)
462:         }
463: 
464:     def learn_augment(self, group: str, name: str, content: str) -> Dict[str, List[str]]:
465:         """
466:         Create a new augment.
467: 
468:         Args:
469:             group: Augment group
470:             name: Augment name
471:             content: Augment content (markdown)
472: 
473:         Returns:
474:             affected
475:         """
476:         # Create group directory if needed
477:         group_dir = self.augments_dir / group
478:         group_dir.mkdir(parents=True, exist_ok=True)
479: 
480:         # Write augment file
481:         augment_file = group_dir / f"{name}.md"
482:         augment_file.write_text(content, encoding='utf-8')
483: 
484:         # Parse and add to available augments
485:         augment = self._parse_augment_file(augment_file)
486:         self.available_augments[augment.path] = augment
487: 
488:         # Update augment tree cache after adding new augment
489:         self._update_augment_tree_cache()
490: 
491:         logger.info(f"Created augment: {augment.path}")
492: 
493:         return {
494:             'affected': [ augment.path ]
495:         }
496: 
497:     def get_related_tools(self, tool_name: str) -> List[str]:
498:         """
499:         Get tools related to the given tool based on active augments.
500: 
501:         This is used by guidance system to provide tool associations.
502: 
503:         Args:
504:             tool_name: Name of tool to find relations for
505: 
506:         Returns:
507:             List of related tool names
508:         """
509:         return self._tool_associations.get(tool_name, [])
510: 
511:     def _match_pattern(self, pattern: str) -> Set[str]:
512:         """
513:         Match augment paths against a pattern.
514: 
515:         Args:
516:             pattern: Pattern to match (supports * wildcard)
517: 
518:         Returns:
519:             Set of matching augment paths
520:         """
521:         matched = set()
522: 
523:         # Convert glob pattern to regex
524:         if pattern == "*" or pattern == "**/*":
525:             # Match all
526:             return set(self.available_augments.keys())
527: 
528:         # Replace * with regex pattern
529:         regex_pattern = pattern.replace('*', '.*')
530:         regex_pattern = f'^{regex_pattern}$'
531: 
532:         try:
533:             compiled = re.compile(regex_pattern)
534:             for augment_path in self.available_augments.keys():
535:                 if compiled.match(augment_path):
536:                     matched.add(augment_path)
537:         except re.error as e:
538:             logger.warning(f"Invalid pattern '{pattern}': {e}")
539: 
540:         return matched
541: 
542:     def _resolve_dependencies(self, augment_paths: List[str]) -> List[str]:
543:         """
544:         Resolve dependencies for given augments.
545: 
546:         Uses BFS to find all required augments, with cycle detection.
547: 
548:         Args:
549:             augment_paths: List of augment paths to resolve
550: 
551:         Returns:
552:             List of augment paths including dependencies
553:         """
554:         resolved = set(augment_paths)
555:         to_process = list(augment_paths)
556:         processed = set()
557: 
558:         while to_process:
559:             current_path = to_process.pop(0)
560: 
561:             if current_path in processed:
562:                 continue
563: 
564:             processed.add(current_path)
565: 
566:             augment = self.available_augments.get(current_path)
567:             if not augment:
568:                 logger.warning(f"Augment not found: {current_path}")
569:                 continue
570: 
571:             # Add dependencies
572:             for dep_path in augment.requires:
573:                 if dep_path not in resolved:
574:                     resolved.add(dep_path)
575:                     to_process.append(dep_path)
576: 
577:         return sorted(resolved)
578: 
579:     def _rebuild_tool_associations(self) -> None:
580:         """Rebuild tool association map from active augments."""
581:         self._tool_associations.clear()
582: 
583:         for augment_path in self.active_augments:
584:             augment = self.available_augments.get(augment_path)
585:             if not augment:
586:                 continue
587: 
588:             # For each tool mentioned in this augment
589:             for tool_name in augment.tools:
590:                 if tool_name not in self._tool_associations:
591:                     self._tool_associations[tool_name] = []
592: 
593:                 # Add other tools from this augment as related
594:                 for other_tool in augment.tools:
595:                     if other_tool != tool_name and other_tool not in self._tool_associations[tool_name]:
596:                         self._tool_associations[tool_name].append(other_tool)
597: 
598:     def _compose_and_write(self) -> None:
599:         """Compose active augments into single markdown file."""
600:         # Start with augment tree (always present)
601:         parts = []
602:         if self._cached_augment_tree:
603:             parts.append(self._cached_augment_tree)
604: 
605:         if not self.active_augments:
606:             # Only augment tree, no active augments
607:             content = parts[0] if parts else ""
608:             self.composed_file.parent.mkdir(parents=True, exist_ok=True)
609:             self.composed_file.write_text(content, encoding='utf-8')
610:             logger.info("No active augments - wrote augment tree only")
611:             return
612: 
613:         # Group augments by group
614:         grouped: Dict[str, List[Augment]] = {}
615:         for augment_path in sorted(self.active_augments):
616:             augment = self.available_augments.get(augment_path)
617:             if not augment:
618:                 continue
619: 
620:             if augment.group not in grouped:
621:                 grouped[augment.group] = []
622:             grouped[augment.group].append(augment)
623: 
624:         # Compose active augments markdown
625:         lines = []
626: 
627:         for group_name in sorted(grouped.keys()):
628:             lines.append(f"# {group_name.replace('_', ' ').title()}")
629:             lines.append("")
630: 
631:             for augment in sorted(grouped[group_name], key=lambda s: s.name):
632:                 lines.append(f"## {augment.name.replace('_', ' ').title()}")
633:                 lines.append(f"Path: {augment.path}")
634:                 lines.append("")
635:                 lines.append(augment.content)
636:                 lines.append("")
637:                 lines.append("---")
638:                 lines.append("")
639: 
640:         parts.append("\n".join(lines))
641:         content = "\n\n".join(parts)
642: 
643:         # Ensure parent directory exists
644:         self.composed_file.parent.mkdir(parents=True, exist_ok=True)
645: 
646:         # Write composed file
647:         self.composed_file.write_text(content, encoding='utf-8')
648: 
649:         logger.info(f"Composed {len(self.active_augments)} augments to {self.composed_file}")