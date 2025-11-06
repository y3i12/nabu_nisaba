---TOOL_RESULT_WINDOW_18b187e1-4ebf-4c1a-8e1a-3ed251fb0413
**type**: read_result
**file**: src/nisaba/wrapper/request_modifier.py
**lines**: 1-518
**total_lines**: 518

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
11: from typing import Any, Optional, List, Dict, TYPE_CHECKING
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
59:         #       'tool_result_content': f"status:{tool_result_status}, window_state:{window_state}, window_id: {toolu_{hash}}"
60:         #   }
61:         }
62:     
63:     def to_dict(self) -> dict:
64:         """Convert state to JSON-serializable dict"""
65:         return {
66:             'session_id': self.session_id,
67:             'last_block_offset': self.last_block_offset,
68:             '_p_state': self._p_state.value,  # Convert enum to int
69:             'tool_result_state': self.tool_result_state
70:         }
71:     
72:     @classmethod
73:     def from_dict(cls, data: dict) -> 'RequestModifierState':
74:         """Reconstruct state from dict"""
75:         state = cls()
76:         state.session_id = data.get('session_id', '')
77:         state.last_block_offset = data.get('last_block_offset', [-1, -1])
78:         state._p_state = RMPState(data.get('_p_state', 0))  # Convert int back to enum
79:         state.tool_result_state = data.get('tool_result_state', {})
80:         return state
81: 
82: 
83: class RequestModifier:
84:     def __init__(self, cache_path:str = '.nisaba/request_cache/') -> None:
85:         self.cache_path:Path = Path(cache_path)
86:         self.state_file:Path = Path(self.cache_path / 'request_modifier_state.json')
87:         self.state: RequestModifierState = RequestModifierState()
88:         self.cache_path.mkdir(exist_ok=True)
89:         self.modifier_rules = {
90:             'messages': [
91:                 {
92:                     'role': self._message_block_count,
93:                     'content': [
94:                         {
95:                             'type': self._content_block_count,
96:                             'tool_use_id': self._tool_use_id_state,
97:                             'content': self._modify_tool_result_content
98:                         }
99:                     ]
100:                 }
101:             ]
102:         }
103:     
104:     def _message_block_count(self, key:str, part:dict[Any,Any]) -> Any:
105:         self.state.last_block_offset[0] += 1 # moves message forward
106:         self.state.last_block_offset[1]  = 0 # resets content block
107:         self.state._p_state = RMPState.NOOP_CONTINUE
108:         pass
109: 
110:     def _content_block_count(self, key:str, part:dict[Any,Any]) -> Any:
111:         self.state.last_block_offset[1] += 1 # moves content forward
112:         self.state._p_state = RMPState.NOOP_CONTINUE
113:         pass
114: 
115:     def _tool_use_id_state(self, key:str, part:dict[Any,Any]) -> Any:
116:         # part is the tool_result content block dict
117:         # part[key] is the tool_use_id value
118:         toolu_id = part[key]
119:         logger.debug(f"  _tool_use_id_state: Found tool_use_id '{toolu_id}'")
120:         
121:         if toolu_id in self.state.tool_result_state:
122:             logger.debug(f"    Tool exists in state, returning stored content")
123:             self.state._p_state = RMPState.UPDATE_AND_CONTINUE
124:             return self.state.tool_result_state[toolu_id]['tool_result_content']
125:         
126:         logger.debug(f"    Tool is new, adding to state")
127:         
128:         # Create tool state entry - extract output from content
129:         tool_output = ""
130:         if 'content' in part:
131:             content = part['content']
132:             # Handle both dict and list structures
133:             if isinstance(content, dict):
134:                 tool_output = content.get('text', str(content))
135:             elif isinstance(content, list):
136:                 # Extract text from first text block
137:                 for block in content:
138:                     if isinstance(block, dict) and block.get('type') == 'text':
139:                         tool_output = block.get('text', '')
140:                         break
141:             else:
142:                 tool_output = str(content)
143:         
144:         toolu_obj = {
145:             'block_offset': list(self.state.last_block_offset),  # Copy the offset, don't reference it
146:             'tool_result_status': "success",
147:             'tool_output': tool_output if tool_output else "",
148:             'window_state': "open",
149:             'tool_result_content': f"status: success, window_state:open, toolu_id: {toolu_id}\n---\n{tool_output}"
150:         }
151:         
152:         self.state.tool_result_state[toolu_id] = toolu_obj
153:         self.state._p_state = RMPState.ADD_AND_CONTINUE
154: 
155:     def _modify_tool_result_content(self, key:str, part:dict[Any,Any]) -> Any:
156:         # key is 'content', part is the entire tool_result block
157:         # Check if this tool_use_id is in state and should be compacted
158:         logger.debug(f"  _modify_tool_result_content: Checking if content should be replaced")
159:         
160:         toolu_id = part.get('tool_use_id')
161:         if not toolu_id:
162:             logger.debug(f"    No tool_use_id found, keeping original")
163:             self.state._p_state = RMPState.ADD_AND_CONTINUE
164:             return None
165:         
166:         if toolu_id in self.state.tool_result_state:
167:             tool_state = self.state.tool_result_state[toolu_id]
168:             window_state = tool_state.get('window_state', 'open')
169:             
170:             if window_state == 'closed':
171:                 # Tool is closed - replace with compact version
172:                 compact_text = (
173:                     f"id: {toolu_id}, "
174:                     f"status: {tool_state.get('tool_result_status', 'success')}, "
175:                     f"state: closed"
176:                 )
177:                 logger.debug(f"    Tool {toolu_id} is closed, replacing with compact format")
178:                 
179:                 # Match the structure of the original content
180:                 original_content = part.get('content')
181:                 if isinstance(original_content, str):
182:                     # Simple string format
183:                     self.state._p_state = RMPState.UPDATE_AND_CONTINUE
184:                     return compact_text
185:                 elif isinstance(original_content, dict):
186:                     # Dict format: {"type": "text", "text": "..."}
187:                     self.state._p_state = RMPState.UPDATE_AND_CONTINUE
188:                     return {"type": "text", "text": compact_text}
189:                 elif isinstance(original_content, list):
190:                     # List format: [{"type": "text", "text": "..."}]
191:                     self.state._p_state = RMPState.UPDATE_AND_CONTINUE
192:                     return [{"type": "text", "text": compact_text}]
193:                 else:
194:                     # Unknown format, keep original
195:                     logger.debug(f"    Unknown content format: {type(original_content)}")
196:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
197:                     return None
198:             else:
199:                 # Tool is open - keep full content
200:                 logger.debug(f"    Tool {toolu_id} is open, keeping full content")
201:                 self.state._p_state = RMPState.ADD_AND_CONTINUE
202:                 return None
203:         else:
204:             # Tool not in state yet (first encounter) - keep original
205:             logger.debug(f"    Tool {toolu_id} not in state, keeping original")
206:             self.state._p_state = RMPState.ADD_AND_CONTINUE
207:             return None
208: 
209:     def __process_request_recursive(self, part:dict[Any,Any]|list[Any], modifier_rules:dict[str,Any]|list[Any]) -> Any:
210:         if RMPState.IDLE == self.state._p_state:
211:             return 
212:         
213:         result = None
214:         result_state = RMPState.ADD_AND_CONTINUE
215:         
216:         logger.debug(f"  __process_request_recursive: state={self.state._p_state.name}, part_type={type(part).__name__}, rules_type={type(modifier_rules).__name__}")
217: 
218:         if RMPState.RECURSE_AND_ADD == self.state._p_state:
219:             if isinstance(part, dict):
220:                 assert isinstance(modifier_rules, dict)
221:                 result = {}
222:                 
223:                 logger.debug(f"    Processing dict with keys: {list(part.keys())}")
224: 
225:                 for key in part.keys():
226:                     if key not in modifier_rules:
227:                         result[key] = part[key]
228:                         logger.debug(f"      Key '{key}' not in rules, copying")
229:                     else:
230:                         logger.debug(f"      Key '{key}' MATCHED in rules, processing...")
231:                         
232:                         # Check if rule is a callable - execute it directly
233:                         if callable(modifier_rules[key]):
234:                             logger.debug(f"        Rule is callable: {modifier_rules[key].__name__}")
235:                             logger.debug(f"        Calling {modifier_rules[key].__name__}('{key}', part)")
236:                             callable_result = modifier_rules[key](key, part)
237:                             logger.debug(f"        Callable returned state: {self.state._p_state.name}")
238:                             
239:                             if RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
240:                                 result[key] = callable_result
241:                                 result_state = RMPState.UPDATE_AND_CONTINUE
242:                             elif RMPState.NOOP_CONTINUE == self.state._p_state:
243:                                 result[key] = part[key]
244:                             else:
245:                                 result[key] = part[key]
246:                         else:
247:                             # Not a callable, recurse into structure
248:                             self.state._p_state = RMPState.PROCESS_MATCH
249:                             child_result = self.__process_request_recursive(part[key], modifier_rules[key])
250:                             if RMPState.ADD_AND_CONTINUE == self.state._p_state:
251:                                 result[key] = part[key]
252:                             elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
253:                                 result[key] = child_result
254:                                 result_state = RMPState.UPDATE_AND_CONTINUE
255:                             elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
256:                                 result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
257:        
258:             elif isinstance(part, list):
259:                 assert isinstance(modifier_rules, list)
260:                 result = []
261:                 logger.debug(f"    Processing list with {len(part)} items against {len(modifier_rules)} rules")
262:                 for i, block in enumerate(part):
263:                     logger.debug(f"      List item [{i}]: {type(block).__name__}")
264:                     self.state._p_state = RMPState.RECURSE_AND_ADD
265:                     for rule_idx, modifier_rule in enumerate(modifier_rules):
266:                         logger.debug(f"        Trying rule #{rule_idx} on item [{i}]")
267:                         child_result = self.__process_request_recursive(block, modifier_rule)
268:                         if RMPState.ADD_AND_CONTINUE == self.state._p_state:
269:                             result.append(block)
270:                             break
271:                         elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
272:                             result.append(child_result)
273:                             result_state = RMPState.UPDATE_AND_CONTINUE
274:                             break
275:                         elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
276:                             result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
277:                             break
278:                         elif RMPState.NOOP_CONTINUE == self.state._p_state:
279:                             pass
280: 
281:             else:
282:                 result = part
283: 
284:         elif RMPState.PROCESS_MATCH == self.state._p_state:
285:             # FIX: Handle non-dict types in PROCESS_MATCH state
286:             if not isinstance(part, dict):
287:                 # When we have a list in PROCESS_MATCH, check if rules are also list
288:                 if isinstance(part, list) and isinstance(modifier_rules, list):
289:                     # Valid list-to-list pattern matching - switch to RECURSE_AND_ADD and re-process
290:                     logger.debug(f"    PROCESS_MATCH got list with list rules, switching to RECURSE_AND_ADD")
291:                     self.state._p_state = RMPState.RECURSE_AND_ADD
292:                     # Re-process with new state
293:                     return self.__process_request_recursive(part, modifier_rules)
294:                 else:
295:                     # Structure mismatch - skip this rule
296:                     logger.debug(f"    PROCESS_MATCH got non-dict ({type(part).__name__}), skipping rule")
297:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
298:                     return part
299:             
300:             # Check if both are dicts for dict processing
301:             if not isinstance(modifier_rules, dict):
302:                 if isinstance(part, dict):
303:                     # part is dict but rules aren't - structure mismatch
304:                     logger.debug(f"    PROCESS_MATCH got non-dict rules ({type(modifier_rules).__name__}), skipping")
305:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
306:                     return part
307:             
308:             # Now safe to proceed with dict handling (only log if we have dicts)
309:             if isinstance(part, dict) and isinstance(modifier_rules, dict):
310:                 logger.debug(f"    PROCESS_MATCH: Checking dict keys: {list(part.keys())} against rules: {list(modifier_rules.keys())}")
311:                 assert isinstance(part, dict)
312:                 assert isinstance(modifier_rules, dict)
313:             else:
314:                 # If we get here, we're in RECURSE_AND_ADD state after list detection
315:                 # This is the fall-through case - return to continue processing
316:                 pass
317: 
318:             result = {}
319: 
320:             # match strings
321:             self.state._p_state = RMPState.UPDATE_AND_CONTINUE
322:             for key in modifier_rules:
323:                 if isinstance(modifier_rules[key], str):
324:                     if key not in part or not isinstance(part[key], str) or not re.match(modifier_rules[key], part[key]):
325:                         self.state._p_state = RMPState.ADD_AND_CONTINUE
326:                         return
327: 
328:             # call functors, they can change results
329:             logger.debug(f"    Checking for callable rules...")
330:             for key in modifier_rules:
331:                 if not callable(modifier_rules[key]):
332:                     continue
333: 
334:                 logger.debug(f"      Found callable for key '{key}'")
335:                 if key not in part:
336:                     logger.debug(f"        Key '{key}' not in part, skipping callable")
337:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
338:                     return
339:                 
340:                 logger.debug(f"        Calling {modifier_rules[key].__name__}('{key}', ...)")
341:                 callable_result = modifier_rules[key](key, part)
342:                 logger.debug(f"        Callable returned state: {self.state._p_state.name}")
343: 
344:                 if RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
345:                     logger.debug(f"        Updating result with callable return value")
346:                     result = callable_result
347:                     result_state = RMPState.UPDATE_AND_CONTINUE
348:                 elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
349:                     result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
350:                     return
351:                         
352:             # recurse remaining parts
353:             for key in part:
354:                 if key in result:
355:                     continue
356: 
357:                 if key not in modifier_rules:
358:                     result[key] = part[key]
359:                     continue
360: 
361:                 self.state._p_state = RMPState.RECURSE_AND_ADD
362:                 child_result = self.__process_request_recursive(part[key], modifier_rules[key])
363:                 if RMPState.ADD_AND_CONTINUE == self.state._p_state:
364:                     result[key] = part[key]
365:                 elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
366:                     result[key] = child_result
367:                     result_state = RMPState.UPDATE_AND_CONTINUE
368:                 elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
369:                     result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
370:             
371:         self.state._p_state = result_state
372:         return result
373: 
374:     def _process_request_recursive(self, body_part:dict[Any,Any]|list[Any]) -> Any:
375:         self.state._p_state = RMPState.RECURSE_AND_ADD
376:         new_body_part = self.__process_request_recursive(part=body_part, modifier_rules=self.modifier_rules)
377:         self.state._p_state = RMPState.IDLE
378:         return new_body_part
379: 
380:     def process_request(self, body: dict[str, Any]) -> dict[str, Any]:
381:         logger.debug("=" * 60)
382:         logger.debug("RequestModifier.process_request() starting")
383:         logger.debug(f"Messages count: {len(body.get('messages', []))}")
384:         
385:         current_session_id = ""
386:         try:
387:             user_id = body.get('metadata', {}).get('user_id', '')
388:             if '_session_' in user_id:
389:                 current_session_id = user_id.split('_session_')[1]
390:                 logger.debug(f"Session ID: {current_session_id}")
391:         except Exception as e:
392:             logger.error(f"Failed to extract session ID: {e}")
393:             raise e
394:         
395:         session_path = Path(self.cache_path / current_session_id)
396:         session_path.mkdir(exist_ok=True)
397: 
398:         body = self._process_request_recursive(body)
399:         self._write_to_file(session_path / 'last_request.json', json.dumps(body, indent=2, ensure_ascii=False), "Last request written")
400:         self._write_to_file(session_path / 'state.json', json.dumps(self.state.to_dict(), indent=2, ensure_ascii=False), "State written")
401:         return body
402: 
403: 
404:     def _estimate_tokens(self, text: str) -> int:
405:         """
406:         estimate tokens of text returning **the estimate number of tokens** XD
407:         """
408:         enc = tiktoken.get_encoding("cl100k_base")
409:         return len(enc.encode(text))
410:     
411:     def _load_state_file(self) -> None:
412:         """
413:         load state file
414:         """
415:         pass
416: 
417: 
418:     def _write_to_file(self, file_path:Path, content: str, log_message: str | None  = None) -> None:
419:         """
420:         write to file file_path the content optionally displaying log_message
421:         """
422:         try:
423:             # Create/truncate file (only last message)
424:             with open(file_path, "w", encoding="utf-8") as f:
425:                 f.write(content)
426: 
427:             if log_message: logger.debug(log_message)
428: 
429:         except Exception as e:
430:             # Don't crash proxy if logging fails
431:             logger.error(f"Failed to log context: {e}")
432:     
433:     def close_tool_results(self, tool_ids: List[str]) -> Dict[str, Any]:
434:         """
435:         Close tool results (compact view in future requests).
436:         
437:         Args:
438:             tool_ids: List of tool IDs to close
439:             
440:         Returns:
441:             Dict with success status and modified tool IDs
442:         """
443:         modified = []
444:         not_found = []
445:         
446:         for tool_id in tool_ids:
447:             if tool_id in self.state.tool_result_state:
448:                 self.state.tool_result_state[tool_id]['window_state'] = 'closed'
449:                 # Update the content string for consistency
450:                 tool_obj = self.state.tool_result_state[tool_id]
451:                 tool_obj['tool_result_content'] = (
452:                     f"id: {tool_id}, "
453:                     f"status: {tool_obj.get('tool_result_status', 'success')}, "
454:                     f"state: closed"
455:                 )
456:                 modified.append(tool_id)
457:                 logger.debug(f"Closed tool result: {tool_id}")
458:             else:
459:                 not_found.append(tool_id)
460:                 logger.debug(f"Tool result not found: {tool_id}")
461:         
462:         return {
463:             'modified': modified,
464:             'not_found': not_found
465:         }
466:     
467:     def open_tool_results(self, tool_ids: List[str]) -> Dict[str, Any]:
468:         """
469:         Open tool results (full view in future requests).
470:         
471:         Args:
472:             tool_ids: List of tool IDs to open
473:             
474:         Returns:
475:             Dict with success status and modified tool IDs
476:         """
477:         modified = []
478:         not_found = []
479:         
480:         for tool_id in tool_ids:
481:             if tool_id in self.state.tool_result_state:
482:                 self.state.tool_result_state[tool_id]['window_state'] = 'open'
483:                 # Restore full content format
484:                 tool_obj = self.state.tool_result_state[tool_id]
485:                 tool_obj['tool_result_content'] = (
486:                     f"status: {tool_obj.get('tool_result_status', 'success')}, "
487:                     f"window_state: open, "
488:                     f"window_id: {tool_id}\n"
489:                     f"---\n"
490:                     f"{tool_obj.get('tool_output', '')}"
491:                 )
492:                 modified.append(tool_id)
493:                 logger.debug(f"Opened tool result: {tool_id}")
494:             else:
495:                 not_found.append(tool_id)
496:                 logger.debug(f"Tool result not found: {tool_id}")
497:         
498:         return {
499:             'modified': modified,
500:             'not_found': not_found
501:         }
502:     
503:     def get_tool_states(self) -> Dict[str, Dict]:
504:         """
505:         Get all tracked tool states.
506:         
507:         Returns:
508:             Dict of tool_id -> tool state info
509:         """
510:         return {
511:             tool_id: {
512:                 'window_state': info['window_state'],
513:                 'status': info['tool_result_status'],
514:                 'offset': info['block_offset']
515:             }
516:             for tool_id, info in self.state.tool_result_state.items()
517:         }
518:         
---TOOL_RESULT_WINDOW_18b187e1-4ebf-4c1a-8e1a-3ed251fb0413_END
