---TOOL_RESULT_WINDOW_5707e32d-2f61-4144-8399-505bfe1fae88
**type**: read_result
**file**: src/nisaba/wrapper/request_modifier.py
**lines**: 1-380
**total_lines**: 380

1: 
2: import datetime
3: import json
4: import logging
5: import os
6: import re
7: import tiktoken
8: 
9: from enum import Enum
10: from pathlib import Path
11: from typing import Any, Optional, List, TYPE_CHECKING
12: from logging.handlers import RotatingFileHandler
13: 
14: 
15: class RequestModifierPrrocessingState(Enum):
16:     IDLE = 0
17:     
18:     RECURSE_AND_ADD = 1
19:     PROCESS_MATCH = 2
20: 
21:     ADD_AND_CONTINUE = 3
22:     IGNORE_AND_CONTINUE = 4
23:     UPDATE_AND_CONTINUE = 5
24:     NOOP_CONTINUE = 6
25: 
26: RMPState = RequestModifierPrrocessingState
27: 
28: logger = logging.getLogger(__name__)
29: logger.setLevel(logging.DEBUG)
30: 
31: # Setup file logging to .nisaba/logs/proxy.log
32: log_dir = Path(".nisaba/logs")
33: log_dir.mkdir(parents=True, exist_ok=True)
34: 
35: # Add file handler if not already present
36: if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
37:     file_handler = RotatingFileHandler(
38:         log_dir / "proxy.log",
39:         maxBytes=1*1024*1024,  # 1MB
40:         backupCount=3
41:     )
42:     file_handler.setFormatter(logging.Formatter(
43:         '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
44:     ))
45:     file_handler.setLevel(logging.DEBUG)
46:     logger.addHandler(file_handler)
47: 
48: class RequestModifierState:
49:     def __init__(self) -> None:
50:         self.session_id: str = ""
51:         self.last_block_offset: list[int] = [0, 0] # message block, content_block
52:         self._p_state:RMPState = RMPState.IDLE
53:         self.tool_result_state:dict[str,dict] = {
54:         #   "toolu_{hash}": {
55:         #       'block_offset': tuple[int, int],
56:         #       'tool_result_status': f"{(success|error)}",
57:         #       'tool_output': (from tool_u.parent.text),
58:         #       'window_state': (open|closed),
59:         #       'start_line': n|0,
60:         #       'num_lines': n|-1,
61:         #       'tool_result_content': f"status:{tool_result_status}, window_state:{window_state}, window_id: {toolu_{hash}}"
62:         #   }
63:         }
64:     
65:     def to_dict(self) -> dict:
66:         """Convert state to JSON-serializable dict"""
67:         return {
68:             'session_id': self.session_id,
69:             'last_block_offset': self.last_block_offset,
70:             '_p_state': self._p_state.value,  # Convert enum to int
71:             'tool_result_state': self.tool_result_state
72:         }
73:     
74:     @classmethod
75:     def from_dict(cls, data: dict) -> 'RequestModifierState':
76:         """Reconstruct state from dict"""
77:         state = cls()
78:         state.session_id = data.get('session_id', '')
79:         state.last_block_offset = data.get('last_block_offset', [-1, -1])
80:         state._p_state = RMPState(data.get('_p_state', 0))  # Convert int back to enum
81:         state.tool_result_state = data.get('tool_result_state', {})
82:         return state
83: 
84: 
85: class RequestModifier:
86:     def __init__(self, cache_path:str = '.nisaba/request_cache/') -> None:
87:         self.cache_path:Path = Path(cache_path)
88:         self.state_file:Path = Path(self.cache_path / 'request_modifier_state.json')
89:         self.state: RequestModifierState = RequestModifierState()
90:         self.cache_path.mkdir(exist_ok=True)
91:         self.modifier_rules = {
92:             'messages': [
93:                 {
94:                     'role': self._message_block_count,
95:                     'content': [
96:                         {
97:                             'type': self._content_block_count,
98:                             'tool_use_id': self._tool_use_id_state
99:                         }
100:                     ]
101:                 }
102:             ]
103:         }
104:     
105:     def _message_block_count(self, key:str, part:dict[Any,Any]) -> Any:
106:         self.state.last_block_offset[0] += 1 # moves message forward
107:         self.state.last_block_offset[1]  = 0 # resets content block
108:         self.state._p_state = RMPState.NOOP_CONTINUE
109:         pass
110: 
111:     def _content_block_count(self, key:str, part:dict[Any,Any]) -> Any:
112:         self.state.last_block_offset[1] += 1 # moves content forward
113:         self.state._p_state = RMPState.NOOP_CONTINUE
114:         pass
115: 
116:     def _tool_use_id_state(self, key:str, part:dict[Any,Any]) -> Any:
117:         # part is the tool_result content block dict
118:         # part[key] is the tool_use_id value
119:         toolu_id = part[key]
120:         logger.debug(f"  _tool_use_id_state: Found tool_use_id '{toolu_id}'")
121:         
122:         if toolu_id in self.state.tool_result_state:
123:             logger.debug(f"    Tool exists in state, returning stored content")
124:             self.state._p_state = RMPState.UPDATE_AND_CONTINUE
125:             return self.state.tool_result_state[toolu_id]['tool_result_content']
126:         
127:         logger.debug(f"    Tool is new, adding to state")
128:         
129:         # Create tool state entry
130:         tool_output = ""
131:         if 'content' in part and isinstance(part['content'], dict):
132:             tool_output = part['content'].get('text', '')
133:         
134:         toolu_obj = {
135:             'block_offset': list(self.state.last_block_offset),  # Copy the offset, don't reference it
136:             'tool_result_status': "success",
137:             'tool_output': tool_output,
138:             'window_state': "open",
139:             'start_line': 0,
140:             'num_lines': -1,
141:             'tool_result_content': f"status: success, window_state:open, window_id: {toolu_id}"
142:         }
143:         
144:         self.state.tool_result_state[toolu_id] = toolu_obj
145:         self.state._p_state = RMPState.ADD_AND_CONTINUE
146: 
147:     def _process_tool_result(self, key:str, part:dict[Any,Any]) -> Any:
148:         # key is 'type', part is the entire tool_result content block
149:         # We need to get tool_use_id from the parent, which we don't have access to
150:         # This needs to be rethought - for now, extract from already-seen tool results
151:         logger.debug(f"  _process_tool_result: Processing tool result content")
152:         
153:         # We can't properly implement this without the parent context containing tool_use_id
154:         # The architecture needs adjustment - callables need access to parent context
155:         self.state._p_state = RMPState.ADD_AND_CONTINUE
156: 
157:     def __process_request_recursive(self, part:dict[Any,Any]|list[Any], modifier_rules:dict[str,Any]|list[Any]) -> Any:
158:         if RMPState.IDLE == self.state._p_state:
159:             return 
160:         
161:         result = None
162:         result_state = RMPState.ADD_AND_CONTINUE
163:         
164:         logger.debug(f"  __process_request_recursive: state={self.state._p_state.name}, part_type={type(part).__name__}, rules_type={type(modifier_rules).__name__}")
165: 
166:         if RMPState.RECURSE_AND_ADD == self.state._p_state:
167:             if isinstance(part, dict):
168:                 assert isinstance(modifier_rules, dict)
169:                 result = {}
170:                 
171:                 logger.debug(f"    Processing dict with keys: {list(part.keys())}")
172: 
173:                 for key in part.keys():
174:                     if key not in modifier_rules:
175:                         result[key] = part[key]
176:                         logger.debug(f"      Key '{key}' not in rules, copying")
177:                     else:
178:                         logger.debug(f"      Key '{key}' MATCHED in rules, processing...")
179:                         
180:                         # Check if rule is a callable - execute it directly
181:                         if callable(modifier_rules[key]):
182:                             logger.debug(f"        Rule is callable: {modifier_rules[key].__name__}")
183:                             logger.debug(f"        Calling {modifier_rules[key].__name__}('{key}', part)")
184:                             callable_result = modifier_rules[key](key, part)
185:                             logger.debug(f"        Callable returned state: {self.state._p_state.name}")
186:                             
187:                             if RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
188:                                 result[key] = callable_result
189:                                 result_state = RMPState.UPDATE_AND_CONTINUE
190:                             elif RMPState.NOOP_CONTINUE == self.state._p_state:
191:                                 result[key] = part[key]
192:                             else:
193:                                 result[key] = part[key]
194:                         else:
195:                             # Not a callable, recurse into structure
196:                             self.state._p_state = RMPState.PROCESS_MATCH
197:                             child_result = self.__process_request_recursive(part[key], modifier_rules[key])
198:                             if RMPState.ADD_AND_CONTINUE == self.state._p_state:
199:                                 result[key] = part[key]
200:                             elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
201:                                 result[key] = child_result
202:                                 result_state = RMPState.UPDATE_AND_CONTINUE
203:                             elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
204:                                 result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
205:        
206:             elif isinstance(part, list):
207:                 assert isinstance(modifier_rules, list)
208:                 result = []
209:                 logger.debug(f"    Processing list with {len(part)} items against {len(modifier_rules)} rules")
210:                 for i, block in enumerate(part):
211:                     logger.debug(f"      List item [{i}]: {type(block).__name__}")
212:                     self.state._p_state = RMPState.RECURSE_AND_ADD
213:                     for rule_idx, modifier_rule in enumerate(modifier_rules):
214:                         logger.debug(f"        Trying rule #{rule_idx} on item [{i}]")
215:                         child_result = self.__process_request_recursive(block, modifier_rule)
216:                         if RMPState.ADD_AND_CONTINUE == self.state._p_state:
217:                             result.append(block)
218:                             break
219:                         elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
220:                             result.append(child_result)
221:                             result_state = RMPState.UPDATE_AND_CONTINUE
222:                             break
223:                         elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
224:                             result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
225:                             break
226:                         elif RMPState.NOOP_CONTINUE == self.state._p_state:
227:                             pass
228: 
229:             else:
230:                 result = part
231: 
232:         elif RMPState.PROCESS_MATCH == self.state._p_state:
233:             # FIX: Handle non-dict types in PROCESS_MATCH state
234:             if not isinstance(part, dict):
235:                 # When we have a list in PROCESS_MATCH, check if rules are also list
236:                 if isinstance(part, list) and isinstance(modifier_rules, list):
237:                     # Valid list-to-list pattern matching - switch to RECURSE_AND_ADD and re-process
238:                     logger.debug(f"    PROCESS_MATCH got list with list rules, switching to RECURSE_AND_ADD")
239:                     self.state._p_state = RMPState.RECURSE_AND_ADD
240:                     # Re-process with new state
241:                     return self.__process_request_recursive(part, modifier_rules)
242:                 else:
243:                     # Structure mismatch - skip this rule
244:                     logger.debug(f"    PROCESS_MATCH got non-dict ({type(part).__name__}), skipping rule")
245:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
246:                     return part
247:             
248:             # Check if both are dicts for dict processing
249:             if not isinstance(modifier_rules, dict):
250:                 if isinstance(part, dict):
251:                     # part is dict but rules aren't - structure mismatch
252:                     logger.debug(f"    PROCESS_MATCH got non-dict rules ({type(modifier_rules).__name__}), skipping")
253:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
254:                     return part
255:             
256:             # Now safe to proceed with dict handling (only log if we have dicts)
257:             if isinstance(part, dict) and isinstance(modifier_rules, dict):
258:                 logger.debug(f"    PROCESS_MATCH: Checking dict keys: {list(part.keys())} against rules: {list(modifier_rules.keys())}")
259:                 assert isinstance(part, dict)
260:                 assert isinstance(modifier_rules, dict)
261:             else:
262:                 # If we get here, we're in RECURSE_AND_ADD state after list detection
263:                 # This is the fall-through case - return to continue processing
264:                 pass
265: 
266:             result = {}
267: 
268:             # match strings
269:             self.state._p_state = RMPState.UPDATE_AND_CONTINUE
270:             for key in modifier_rules:
271:                 if isinstance(modifier_rules[key], str):
272:                     if key not in part or not isinstance(part[key], str) or not re.match(modifier_rules[key], part[key]):
273:                         self.state._p_state = RMPState.ADD_AND_CONTINUE
274:                         return
275: 
276:             # call functors, they can change results
277:             logger.debug(f"    Checking for callable rules...")
278:             for key in modifier_rules:
279:                 if not callable(modifier_rules[key]):
280:                     continue
281: 
282:                 logger.debug(f"      Found callable for key '{key}'")
283:                 if key not in part:
284:                     logger.debug(f"        Key '{key}' not in part, skipping callable")
285:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
286:                     return
287:                 
288:                 logger.debug(f"        Calling {modifier_rules[key].__name__}('{key}', ...)")
289:                 callable_result = modifier_rules[key](key, part)
290:                 logger.debug(f"        Callable returned state: {self.state._p_state.name}")
291: 
292:                 if RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
293:                     logger.debug(f"        Updating result with callable return value")
294:                     result = callable_result
295:                     result_state = RMPState.UPDATE_AND_CONTINUE
296:                 elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
297:                     result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
298:                     return
299:                         
300:             # recurse remaining parts
301:             for key in part:
302:                 if key in result:
303:                     continue
304: 
305:                 if key not in modifier_rules:
306:                     result[key] = part[key]
307:                     continue
308: 
309:                 self.state._p_state = RMPState.RECURSE_AND_ADD
310:                 child_result = self.__process_request_recursive(part[key], modifier_rules[key])
311:                 if RMPState.ADD_AND_CONTINUE == self.state._p_state:
312:                     result[key] = part[key]
313:                 elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
314:                     result[key] = child_result
315:                     result_state = RMPState.UPDATE_AND_CONTINUE
316:                 elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
317:                     result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
318:             
319:         self.state._p_state = result_state
320:         return result
321: 
322:     def _process_request_recursive(self, body_part:dict[Any,Any]|list[Any]) -> Any:
323:         self.state._p_state = RMPState.RECURSE_AND_ADD
324:         new_body_part = self.__process_request_recursive(part=body_part, modifier_rules=self.modifier_rules)
325:         self.state._p_state = RMPState.IDLE
326:         return new_body_part
327: 
328:     def process_request(self, body: dict[str, Any]) -> dict[str, Any]:
329:         logger.debug("=" * 60)
330:         logger.debug("RequestModifier.process_request() starting")
331:         logger.debug(f"Messages count: {len(body.get('messages', []))}")
332:         
333:         current_session_id = ""
334:         try:
335:             user_id = body.get('metadata', {}).get('user_id', '')
336:             if '_session_' in user_id:
337:                 current_session_id = user_id.split('_session_')[1]
338:                 logger.debug(f"Session ID: {current_session_id}")
339:         except Exception as e:
340:             logger.error(f"Failed to extract session ID: {e}")
341:             raise e
342:         
343:         session_path = Path(self.cache_path / current_session_id)
344:         session_path.mkdir(exist_ok=True)
345: 
346:         body = self._process_request_recursive(body)
347:         self._write_to_file(session_path / 'last_request.json', json.dumps(body, indent=2, ensure_ascii=False), "Last request written")
348:         self._write_to_file(session_path / 'state.json', json.dumps(self.state.to_dict(), indent=2, ensure_ascii=False), "State written")
349:         return body
350: 
351: 
352:     def _estimate_tokens(self, text: str) -> int:
353:         """
354:         estimate tokens of text returning **the estimate number of tokens** XD
355:         """
356:         enc = tiktoken.get_encoding("cl100k_base")
357:         return len(enc.encode(text))
358:     
359:     def _load_state_file(self) -> None:
360:         """
361:         load state file
362:         """
363:         pass
364: 
365: 
366:     def _write_to_file(self, file_path:Path, content: str, log_message: str | None  = None) -> None:
367:         """
368:         write to file file_path the content optionally displaying log_message
369:         """
370:         try:
371:             # Create/truncate file (only last message)
372:             with open(file_path, "w", encoding="utf-8") as f:
373:                 f.write(content)
374: 
375:             if log_message: logger.debug(log_message)
376: 
377:         except Exception as e:
378:             # Don't crash proxy if logging fails
379:             logger.error(f"Failed to log context: {e}")
380:         
---TOOL_RESULT_WINDOW_5707e32d-2f61-4144-8399-505bfe1fae88_END
