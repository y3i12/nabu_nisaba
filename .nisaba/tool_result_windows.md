---TOOL_RESULT_WINDOW_8f53ee2b-1d28-44fe-8e3f-6e3eccb3eef5
**type**: read_result
**file**: src/nisaba/wrapper/request_modifier.py
**lines**: 1-378
**total_lines**: 378

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
51:         self.last_block_offset: list[int] = [-1, -1] # message block, content_block
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
98:                         }
99:                     ]
100:                 },
101:                 {
102:                     'role': 'user',
103:                     'content': [
104:                         {
105:                             'type': 'tool_result',
106:                             'tool_use_id': self._tool_use_id_state,
107:                             'content': {
108:                                 'type': 'text',
109:                                 'text': self._process_tool_result
110:                             }
111:                         }
112:                     ]
113:                 }
114:             ]
115:         }
116:     
117:     def _message_block_count(self, key:str, part:dict[Any,Any]) -> Any:
118:         self.state.last_block_offset[0] += 1 # moves message forward
119:         self.state.last_block_offset[1]  = -1 # resets content block
120:         self.state._p_state = RMPState.NOOP_CONTINUE
121:         pass
122: 
123:     def _content_block_count(self, key:str, part:dict[Any,Any]) -> Any:
124:         self.state.last_block_offset[1] += 1 # moves content forward
125:         self.state._p_state = RMPState.NOOP_CONTINUE
126:         pass
127: 
128:     def _tool_use_id_state(self, key:str, part:dict[Any,Any]) -> Any:
129:         toolu_id = part[key]
130:         logger.debug(f"  _tool_use_id_state: Found tool_use_id '{toolu_id}'")
131:         if toolu_id in self.state.tool_result_state:
132:             logger.debug(f"    Tool exists in state, returning stored content")
133:             self.state._p_state = RMPState.UPDATE_AND_CONTINUE
134:             return self.state.tool_result_state[toolu_id]['tool_result_content']
135:         
136:         logger.debug(f"    Tool is new, adding to state")
137:         self.state._p_state = RMPState.ADD_AND_CONTINUE
138: 
139:     def _process_tool_result(self, key:str, part:dict[Any,Any]) -> Any:
140:         toolu_id = part[key]
141:         logger.debug(f"  _process_tool_result: Processing tool result for '{toolu_id}'")
142:         toolu_obj = {
143:             'block_offset': self.state.last_block_offset,
144:             'tool_result_status': "success", # TODO: get this from proxy
145:             'tool_output': part['content']['text'],
146:             'window_state': "open", # TODO: integrate with window management
147:             'start_line': 0, # TODO: integrate with window management
148:             'num_lines': -1, # TODO: integrate with window management
149:             'tool_result_content': f"status: success, window_state:open, window_id: {toolu_id}"
150:         }
151: 
152:         self.state.tool_result_state[toolu_id] = toolu_obj
153:         self.state._p_state = RMPState.ADD_AND_CONTINUE
154: 
155:     def __process_request_recursive(self, part:dict[Any,Any]|list[Any], modifier_rules:dict[str,Any]|list[Any]) -> Any:
156:         if RMPState.IDLE == self.state._p_state:
157:             return 
158:         
159:         result = None
160:         result_state = RMPState.ADD_AND_CONTINUE
161:         
162:         logger.debug(f"  __process_request_recursive: state={self.state._p_state.name}, part_type={type(part).__name__}, rules_type={type(modifier_rules).__name__}")
163: 
164:         if RMPState.RECURSE_AND_ADD == self.state._p_state:
165:             if isinstance(part, dict):
166:                 assert isinstance(modifier_rules, dict)
167:                 result = {}
168:                 
169:                 logger.debug(f"    Processing dict with keys: {list(part.keys())}")
170: 
171:                 for key in part.keys():
172:                     if key not in modifier_rules:
173:                         result[key] = part[key]
174:                         logger.debug(f"      Key '{key}' not in rules, copying")
175:                     else:
176:                         logger.debug(f"      Key '{key}' MATCHED in rules, processing...")
177:                         
178:                         # Check if rule is a callable - execute it directly
179:                         if callable(modifier_rules[key]):
180:                             logger.debug(f"        Rule is callable: {modifier_rules[key].__name__}")
181:                             logger.debug(f"        Calling {modifier_rules[key].__name__}('{key}', part)")
182:                             callable_result = modifier_rules[key](key, part)
183:                             logger.debug(f"        Callable returned state: {self.state._p_state.name}")
184:                             
185:                             if RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
186:                                 result[key] = callable_result
187:                                 result_state = RMPState.UPDATE_AND_CONTINUE
188:                             elif RMPState.NOOP_CONTINUE == self.state._p_state:
189:                                 result[key] = part[key]
190:                             else:
191:                                 result[key] = part[key]
192:                         else:
193:                             # Not a callable, recurse into structure
194:                             self.state._p_state = RMPState.PROCESS_MATCH
195:                             child_result = self.__process_request_recursive(part[key], modifier_rules[key])
196:                             if RMPState.ADD_AND_CONTINUE == self.state._p_state:
197:                                 result[key] = part[key]
198:                             elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
199:                                 result[key] = child_result
200:                                 result_state = RMPState.UPDATE_AND_CONTINUE
201:                             elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
202:                                 result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
203:        
204:             elif isinstance(part, list):
205:                 assert isinstance(modifier_rules, list)
206:                 result = []
207:                 logger.debug(f"    Processing list with {len(part)} items against {len(modifier_rules)} rules")
208:                 for i, block in enumerate(part):
209:                     logger.debug(f"      List item [{i}]: {type(block).__name__}")
210:                     self.state._p_state = RMPState.RECURSE_AND_ADD
211:                     for rule_idx, modifier_rule in enumerate(modifier_rules):
212:                         logger.debug(f"        Trying rule #{rule_idx} on item [{i}]")
213:                         child_result = self.__process_request_recursive(block, modifier_rule)
214:                         if RMPState.ADD_AND_CONTINUE == self.state._p_state:
215:                             result.append(block)
216:                             break
217:                         elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
218:                             result.append(child_result)
219:                             result_state = RMPState.UPDATE_AND_CONTINUE
220:                             break
221:                         elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
222:                             result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
223:                             break
224:                         elif RMPState.NOOP_CONTINUE == self.state._p_state:
225:                             pass
226: 
227:             else:
228:                 result = part
229: 
230:         elif RMPState.PROCESS_MATCH == self.state._p_state:
231:             # FIX: Handle non-dict types in PROCESS_MATCH state
232:             if not isinstance(part, dict):
233:                 # When we have a list in PROCESS_MATCH, check if rules are also list
234:                 if isinstance(part, list) and isinstance(modifier_rules, list):
235:                     # Valid list-to-list pattern matching - switch to RECURSE_AND_ADD and re-process
236:                     logger.debug(f"    PROCESS_MATCH got list with list rules, switching to RECURSE_AND_ADD")
237:                     self.state._p_state = RMPState.RECURSE_AND_ADD
238:                     # Re-process with new state
239:                     return self.__process_request_recursive(part, modifier_rules)
240:                 else:
241:                     # Structure mismatch - skip this rule
242:                     logger.debug(f"    PROCESS_MATCH got non-dict ({type(part).__name__}), skipping rule")
243:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
244:                     return part
245:             
246:             # Check if both are dicts for dict processing
247:             if not isinstance(modifier_rules, dict):
248:                 if isinstance(part, dict):
249:                     # part is dict but rules aren't - structure mismatch
250:                     logger.debug(f"    PROCESS_MATCH got non-dict rules ({type(modifier_rules).__name__}), skipping")
251:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
252:                     return part
253:             
254:             # Now safe to proceed with dict handling (only log if we have dicts)
255:             if isinstance(part, dict) and isinstance(modifier_rules, dict):
256:                 logger.debug(f"    PROCESS_MATCH: Checking dict keys: {list(part.keys())} against rules: {list(modifier_rules.keys())}")
257:                 assert isinstance(part, dict)
258:                 assert isinstance(modifier_rules, dict)
259:             else:
260:                 # If we get here, we're in RECURSE_AND_ADD state after list detection
261:                 # This is the fall-through case - return to continue processing
262:                 pass
263: 
264:             result = {}
265: 
266:             # match strings
267:             self.state._p_state = RMPState.UPDATE_AND_CONTINUE
268:             for key in modifier_rules:
269:                 if isinstance(modifier_rules[key], str):
270:                     if key not in part or not isinstance(part[key], str) or not re.match(modifier_rules[key], part[key]):
271:                         self.state._p_state = RMPState.ADD_AND_CONTINUE
272:                         return
273: 
274:             # call functors, they can change results
275:             logger.debug(f"    Checking for callable rules...")
276:             for key in modifier_rules:
277:                 if not callable(modifier_rules[key]):
278:                     continue
279: 
280:                 logger.debug(f"      Found callable for key '{key}'")
281:                 if key not in part:
282:                     logger.debug(f"        Key '{key}' not in part, skipping callable")
283:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
284:                     return
285:                 
286:                 logger.debug(f"        Calling {modifier_rules[key].__name__}('{key}', ...)")
287:                 callable_result = modifier_rules[key](key, part)
288:                 logger.debug(f"        Callable returned state: {self.state._p_state.name}")
289: 
290:                 if RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
291:                     logger.debug(f"        Updating result with callable return value")
292:                     result = callable_result
293:                     result_state = RMPState.UPDATE_AND_CONTINUE
294:                 elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
295:                     result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
296:                     return
297:                         
298:             # recurse remaining parts
299:             for key in part:
300:                 if key in result:
301:                     continue
302: 
303:                 if key not in modifier_rules:
304:                     result[key] = part[key]
305:                     continue
306: 
307:                 self.state._p_state = RMPState.RECURSE_AND_ADD
308:                 child_result = self.__process_request_recursive(part[key], modifier_rules[key])
309:                 if RMPState.ADD_AND_CONTINUE == self.state._p_state:
310:                     result[key] = part[key]
311:                 elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
312:                     result[key] = child_result
313:                     result_state = RMPState.UPDATE_AND_CONTINUE
314:                 elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
315:                     result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
316:             
317:         self.state._p_state = result_state
318:         return result
319: 
320:     def _process_request_recursive(self, body_part:dict[Any,Any]|list[Any]) -> Any:
321:         self.state._p_state = RMPState.RECURSE_AND_ADD
322:         new_body_part = self.__process_request_recursive(part=body_part, modifier_rules=self.modifier_rules)
323:         self.state._p_state = RMPState.IDLE
324:         return new_body_part
325: 
326:     def process_request(self, body: dict[str, Any]) -> dict[str, Any]:
327:         logger.debug("=" * 60)
328:         logger.debug("RequestModifier.process_request() starting")
329:         logger.debug(f"Messages count: {len(body.get('messages', []))}")
330:         
331:         current_session_id = ""
332:         try:
333:             user_id = body.get('metadata', {}).get('user_id', '')
334:             if '_session_' in user_id:
335:                 current_session_id = user_id.split('_session_')[1]
336:                 logger.debug(f"Session ID: {current_session_id}")
337:         except Exception as e:
338:             logger.error(f"Failed to extract session ID: {e}")
339:             raise e
340:         
341:         session_path = Path(self.cache_path / current_session_id)
342:         session_path.mkdir(exist_ok=True)
343: 
344:         body = self._process_request_recursive(body)
345:         self._write_to_file(session_path / 'last_request.json', json.dumps(body, indent=2, ensure_ascii=False), "Last request written")
346:         self._write_to_file(session_path / 'state.json', json.dumps(self.state.to_dict(), indent=2, ensure_ascii=False), "State written")
347:         return body
348: 
349: 
350:     def _estimate_tokens(self, text: str) -> int:
351:         """
352:         estimate tokens of text returning **the estimate number of tokens** XD
353:         """
354:         enc = tiktoken.get_encoding("cl100k_base")
355:         return len(enc.encode(text))
356:     
357:     def _load_state_file(self) -> None:
358:         """
359:         load state file
360:         """
361:         pass
362: 
363: 
364:     def _write_to_file(self, file_path:Path, content: str, log_message: str | None  = None) -> None:
365:         """
366:         write to file file_path the content optionally displaying log_message
367:         """
368:         try:
369:             # Create/truncate file (only last message)
370:             with open(file_path, "w", encoding="utf-8") as f:
371:                 f.write(content)
372: 
373:             if log_message: logger.debug(log_message)
374: 
375:         except Exception as e:
376:             # Don't crash proxy if logging fails
377:             logger.error(f"Failed to log context: {e}")
378:         
---TOOL_RESULT_WINDOW_8f53ee2b-1d28-44fe-8e3f-6e3eccb3eef5_END

---TOOL_RESULT_WINDOW_18b4e835-705c-47c6-a440-24d3ba6ab8c2
**type**: bash_result
**command**: cd /home/y3i12/nabu_nisaba && python3 test_request_modifier_trace.py 2>&1
**exit_code**: 0
**cwd**: /home/y3i12/nabu_nisaba
**total_lines**: 74

================================================================================
TABLE TEST: Tool Result Tracking
================================================================================

📋 INPUT STRUCTURE:
Messages: 3
Message 0: role=user, content blocks=1
Message 1: role=assistant, content blocks=2
Message 2: role=user, content blocks=1
  - Message 2 content[0] has type: tool_result
  - Message 2 content[0] has tool_use_id: toolu_ABC

🔍 EXPECTED FLOW:
1. body (dict) -> messages (list)
2. messages[0] (dict) -> role='user' -> _message_block_count() fires
3. messages[0] -> content (list) -> content[0] (dict)
4. content[0] -> type='text' -> _content_block_count() fires
5. ... repeat for messages[1] ...
6. messages[2] -> role='user' -> _message_block_count() fires
7. messages[2] -> content[0] -> type='tool_result' -> _content_block_count() fires
8. messages[2] -> content[0] -> tool_use_id='toolu_ABC' -> _tool_use_id_state() fires ⭐
9. messages[2] -> content[0] -> content (nested) -> text -> _process_tool_result() fires ⭐

================================================================================
EXECUTING...
================================================================================

📊 RESULTS:
Block offset: [2, 0]
Tool states tracked: 0

❌ FAILURE - No tool states captured

DEBUG: Check modifier rules structure

Modifier rules for messages:
[
  {
    "role": "<bound method RequestModifier._message_block_count of <src.nisaba.wrapper.request_modifier.RequestModifier object at 0x70d8111ffb60>>",
    "content": [
      {
        "type": "<bound method RequestModifier._content_block_count of <src.nisaba.wrapper.request_modifier.RequestModifier object at 0x70d8111ffb60>>"
      }
    ]
  },
  {
    "role": "user",
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "<bound method RequestModifier._tool_use_id_state of <src.nisaba.wrapper.request_modifier.RequestModifier object at 0x70d8111ffb60>>",
        "content": {
          "type": "text",
          "text": "<bound method RequestModifier._process_tool_result of <src.nisaba.wrapper.request_modifier.RequestModifier object at 0x70d8111ffb60>>"
        }
      }
    ]
  }
]

================================================================================
CHECKING LOGS...
================================================================================

Callable invocations found: 7
  2025-11-06 13:35:35,793 - src.nisaba.wrapper.request_modifier - DEBUG -         Calling _message_block_count('role', part)
  2025-11-06 13:35:35,794 - src.nisaba.wrapper.request_modifier - DEBUG -         Calling _content_block_count('type', part)
  2025-11-06 13:35:35,794 - src.nisaba.wrapper.request_modifier - DEBUG -         Calling _content_block_count('type', part)
  2025-11-06 13:35:35,794 - src.nisaba.wrapper.request_modifier - DEBUG -         Calling _message_block_count('role', part)
  2025-11-06 13:35:35,794 - src.nisaba.wrapper.request_modifier - DEBUG -         Calling _content_block_count('type', part)

Tool use ID references: 2
  2025-11-06 13:35:35,794 - src.nisaba.wrapper.request_modifier - DEBUG -     Processing dict with keys: ['type', 'tool_use_id', 'content']
  2025-11-06 13:35:35,795 - src.nisaba.wrapper.request_modifier - DEBUG -       Key 'tool_use_id' not in rules, copying
---TOOL_RESULT_WINDOW_18b4e835-705c-47c6-a440-24d3ba6ab8c2_END

---TOOL_RESULT_WINDOW_a7603c85-654a-452b-93be-18deb6543dad
**type**: read_result
**file**: src/nisaba/wrapper/request_modifier.py
**lines**: 91-115
**total_lines**: 25

91:         self.modifier_rules = {
92:             'messages': [
93:                 {
94:                     'role': self._message_block_count,
95:                     'content': [
96:                         {
97:                             'type': self._content_block_count,
98:                         }
99:                     ]
100:                 },
101:                 {
102:                     'role': 'user',
103:                     'content': [
104:                         {
105:                             'type': 'tool_result',
106:                             'tool_use_id': self._tool_use_id_state,
107:                             'content': {
108:                                 'type': 'text',
109:                                 'text': self._process_tool_result
110:                             }
111:                         }
112:                     ]
113:                 }
114:             ]
115:         }
---TOOL_RESULT_WINDOW_a7603c85-654a-452b-93be-18deb6543dad_END

---TOOL_RESULT_WINDOW_bcc25e25-d47d-4c2a-96b1-e9e2270f62b8
**type**: read_result
**file**: src/nisaba/wrapper/request_modifier.py
**lines**: 195-215
**total_lines**: 21

195:                             child_result = self.__process_request_recursive(part[key], modifier_rules[key])
196:                             if RMPState.ADD_AND_CONTINUE == self.state._p_state:
197:                                 result[key] = part[key]
198:                             elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
199:                                 result[key] = child_result
200:                                 result_state = RMPState.UPDATE_AND_CONTINUE
201:                             elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
202:                                 result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
203:        
204:             elif isinstance(part, list):
205:                 assert isinstance(modifier_rules, list)
206:                 result = []
207:                 logger.debug(f"    Processing list with {len(part)} items against {len(modifier_rules)} rules")
208:                 for i, block in enumerate(part):
209:                     logger.debug(f"      List item [{i}]: {type(block).__name__}")
210:                     self.state._p_state = RMPState.RECURSE_AND_ADD
211:                     for rule_idx, modifier_rule in enumerate(modifier_rules):
212:                         logger.debug(f"        Trying rule #{rule_idx} on item [{i}]")
213:                         child_result = self.__process_request_recursive(block, modifier_rule)
214:                         if RMPState.ADD_AND_CONTINUE == self.state._p_state:
215:                             result.append(block)
---TOOL_RESULT_WINDOW_bcc25e25-d47d-4c2a-96b1-e9e2270f62b8_END

---TOOL_RESULT_WINDOW_5929c1fa-1dab-43b7-82de-8978f8357f91
**type**: bash_result
**command**: cd /home/y3i12/nabu_nisaba && python3 test_request_modifier_trace.py 2>&1 | tail -30
**exit_code**: 0
**cwd**: /home/y3i12/nabu_nisaba
**total_lines**: 30

    test_tool_result_tracking()
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/home/y3i12/nabu_nisaba/test_request_modifier_trace.py", line 88, in test_tool_result_tracking
    result = modifier.process_request(test_body)
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 344, in process_request
    body = self._process_request_recursive(body)
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 322, in _process_request_recursive
    new_body_part = self.__process_request_recursive(part=body_part, modifier_rules=self.modifier_rules)
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 195, in __process_request_recursive
    child_result = self.__process_request_recursive(part[key], modifier_rules[key])
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 239, in __process_request_recursive
    return self.__process_request_recursive(part, modifier_rules)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 213, in __process_request_recursive
    child_result = self.__process_request_recursive(block, modifier_rule)
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 195, in __process_request_recursive
    child_result = self.__process_request_recursive(part[key], modifier_rules[key])
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 239, in __process_request_recursive
    return self.__process_request_recursive(part, modifier_rules)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 213, in __process_request_recursive
    child_result = self.__process_request_recursive(block, modifier_rule)
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 195, in __process_request_recursive
    child_result = self.__process_request_recursive(part[key], modifier_rules[key])
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 287, in __process_request_recursive
    callable_result = modifier_rules[key](key, part)
  File "/home/y3i12/nabu_nisaba/src/nisaba/wrapper/request_modifier.py", line 145, in _process_tool_result
    'tool_output': part['content']['text'],
                   ~~~~^^^^^^^^^^^
KeyError: 'content'
---TOOL_RESULT_WINDOW_5929c1fa-1dab-43b7-82de-8978f8357f91_END
