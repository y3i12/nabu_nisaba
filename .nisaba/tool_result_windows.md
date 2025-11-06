---TOOL_RESULT_WINDOW_2fe64dcc-380c-4aa4-a4c2-849145c6c9b5
**type**: bash_result
**command**: echo -e "\033[31mRed text\033[0m \033[32mGreen text\033[0m \033[34mBlue text\033[0m \033[35mMagenta\033[0m \033[36mCyan\033[0m"
**exit_code**: 0
**cwd**: /home/y3i12/nabu_nisaba
**total_lines**: 1

-e [31mRed text[0m [32mGreen text[0m [34mBlue text[0m [35mMagenta[0m [36mCyan[0m
---TOOL_RESULT_WINDOW_2fe64dcc-380c-4aa4-a4c2-849145c6c9b5_END

---TOOL_RESULT_WINDOW_6774486e-4f4f-4f4b-a8ca-fbd55efdfd10
**type**: read_result
**file**: src/nisaba/wrapper/request_modifier.py
**lines**: 1-268
**total_lines**: 268

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
12: 
13: 
14: class RequestModifierPrrocessingState(Enum):
15:     IDLE = 0
16:     
17:     RECURSE_AND_ADD = 1
18:     PROCESS_MATCH = 2
19: 
20:     ADD_AND_CONTINUE = 3
21:     IGNORE_AND_CONTINUE = 4
22:     UPDATE_AND_CONTINUE = 5
23:     NOOP_CONTINUE = 6
24: 
25: RMPState = RequestModifierPrrocessingState
26: 
27: logger = logging.getLogger(__name__)
28: 
29: class RequestModifierState:
30:     def __init__(self) -> None:
31:         self.session_id: str = ""
32:         self.last_block_offset: list[int] = [-1, -1] # message block, content_block
33:         self._p_state:RMPState = RMPState.IDLE
34:         self.tool_result_state:dict[str,dict] = {
35:         #   "toolu_{hash}": {
36:         #       'block_offset': tuple[int, int],
37:         #       'tool_result_status': f"{(success|error)}",
38:         #       'tool_output': (from tool_u.parent.text),
39:         #       'window_state': (open|closed),
40:         #       'start_line': n|0,
41:         #       'num_lines': n|-1,
42:         #       'tool_result_content': f"status:{tool_result_status}, window_state:{window_state}, window_id: {toolu_{hash}}"
43:         #   }
44:         }
45: 
46: 
47: class RequestModifier:
48:     def __init__(self, cache_path:str = '.nisaba/request_cache/') -> None:
49:         self.cache_path:Path = Path(cache_path)
50:         self.state_file:Path = Path(self.cache_path / 'request_modifier_state.json')
51:         self.state: RequestModifierState = RequestModifierState()
52:         self.cache_path.mkdir(exist_ok=True)
53:         self.modifier_rules = {
54:             'messages': [
55:                 {
56:                     'role': self._message_block_count,
57:                     'content': [
58:                         {
59:                             'type': self._content_block_count,
60:                         }
61:                     ]
62:                 },
63:                 {
64:                     'role': 'user',
65:                     'content': [
66:                         {
67:                             'type': 'tool_result',
68:                             'tool_use_id': self._tool_use_id_state,
69:                             'content': {
70:                                 'type': 'text',
71:                                 'text': self._process_tool_result
72:                             }
73:                         }
74:                     ]
75:                 }
76:             ]
77:         }
78:     
79:     def _message_block_count(self, key:str, part:dict[Any,Any]) -> Any:
80:         self.state.last_block_offset[0] += 1 # moves message forward
81:         self.state.last_block_offset[1]  = -1 # resets content block
82:         self.state._p_state = RMPState.NOOP_CONTINUE
83:         pass
84: 
85:     def _content_block_count(self, key:str, part:dict[Any,Any]) -> Any:
86:         self.state.last_block_offset[1] += 1 # moves content forward
87:         self.state._p_state = RMPState.NOOP_CONTINUE
88:         pass
89: 
90:     def _tool_use_id_state(self, key:str, part:dict[Any,Any]) -> Any:
91:         toolu_id = part[key]
92:         if toolu_id in self.state.tool_result_state:
93:             self.state._p_state = RMPState.UPDATE_AND_CONTINUE
94:             return self.state.tool_result_state[toolu_id]['tool_result_content']
95:         
96:         self.state._p_state = RMPState.ADD_AND_CONTINUE
97: 
98:     def _process_tool_result(self, key:str, part:dict[Any,Any]) -> Any:
99:         toolu_id = part[key]
100:         toolu_obj = {
101:             'block_offset': self.state.last_block_offset,
102:             'tool_result_status': "success", # TODO: get this from proxy
103:             'tool_output': part['content']['text'],
104:             'window_state': "open", # TODO: integrate with window management
105:             'start_line': 0, # TODO: integrate with window management
106:             'num_lines': -1, # TODO: integrate with window management
107:             'tool_result_content': f"status: success, window_state:open, window_id: {toolu_id}"
108:         }
109: 
110:         self.state.tool_result_state[toolu_id] = toolu_obj
111:         self.state._p_state = RMPState.ADD_AND_CONTINUE
112: 
113:     def __process_request_recursive(self, part:dict[Any,Any]|list[Any], modifier_rules:dict[str,Any]|list[Any]) -> Any:
114:         if RMPState.IDLE == self.state._p_state:
115:             return 
116:         
117:         result = None
118:         result_state = RMPState.ADD_AND_CONTINUE
119: 
120:         if RMPState.RECURSE_AND_ADD == self.state._p_state:
121:             if isinstance(part, dict):
122:                 assert isinstance(modifier_rules, dict)
123:                 result = {}
124: 
125:                 for key in part.keys():
126:                     if key not in modifier_rules:
127:                         result[key] = part[key]
128:                     else:
129:                         self.state._p_state = RMPState.PROCESS_MATCH
130:                         child_result = self.__process_request_recursive(part[key], modifier_rules[key])
131:                         if RMPState.ADD_AND_CONTINUE == self.state._p_state:
132:                             result[key] = part[key]
133:                         elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
134:                             result[key] = child_result
135:                             result_state = RMPState.UPDATE_AND_CONTINUE
136:                         elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
137:                             result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
138:        
139:             elif isinstance(part, list):
140:                 assert isinstance(modifier_rules, list)
141:                 result = []
142:                 for block in part:
143:                     self.state._p_state = RMPState.RECURSE_AND_ADD
144:                     for modifier_rule in modifier_rules:
145:                         child_result = self.__process_request_recursive(block, modifier_rule)
146:                         if RMPState.ADD_AND_CONTINUE == self.state._p_state:
147:                             result.append(block)
148:                             break
149:                         elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
150:                             result.append(child_result)
151:                             result_state = RMPState.UPDATE_AND_CONTINUE
152:                             break
153:                         elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
154:                             result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
155:                             break
156:                         elif RMPState.NOOP_CONTINUE == self.state._p_state:
157:                             pass
158: 
159:             else:
160:                 result = part
161: 
162:         elif RMPState.PROCESS_MATCH == self.state._p_state:
163:             assert isinstance(part, dict)
164:             assert isinstance(modifier_rules, dict)
165: 
166:             result = {}
167: 
168:             # match strings
169:             self.state._p_state = RMPState.UPDATE_AND_CONTINUE
170:             for key in modifier_rules:
171:                 if isinstance(modifier_rules[key], str):
172:                     if key not in part or not isinstance(part[key], str) or not re.match(modifier_rules[key], part[key]):
173:                         self.state._p_state = RMPState.ADD_AND_CONTINUE
174:                         return
175: 
176:             # call functors, they can change results
177:             for key in modifier_rules:
178:                 if not callable(modifier_rules[key]):
179:                     continue
180: 
181:                 if key not in part:
182:                     self.state._p_state = RMPState.ADD_AND_CONTINUE
183:                     return
184:                 
185:                 callable_result = modifier_rules[key](key, part)
186: 
187:                 if RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
188:                     result = callable_result
189:                     result_state = RMPState.UPDATE_AND_CONTINUE
190:                 elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
191:                     result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
192:                     return
193:                         
194:             # recurse remaining parts
195:             for key in part:
196:                 if key in result:
197:                     continue
198: 
199:                 if key not in modifier_rules:
200:                     result[key] = part[key]
201: 
202:                 self.state._p_state = RMPState.RECURSE_AND_ADD
203:                 child_result = self.__process_request_recursive(part[key], modifier_rules[key])
204:                 if RMPState.ADD_AND_CONTINUE == self.state._p_state:
205:                     result[key] = part[key]
206:                 elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
207:                     result[key] = child_result
208:                     result_state = RMPState.UPDATE_AND_CONTINUE
209:                 elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
210:                     result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
211:             
212:         self.state._p_state = result_state
213:         return result
214: 
215:     def _process_request_recursive(self, body_part:dict[Any,Any]|list[Any]) -> Any:
216:         self.state._p_state = RMPState.RECURSE_AND_ADD
217:         new_body_part = self.__process_request_recursive(part=body_part, modifier_rules=self.modifier_rules)
218:         self.state._p_state = RMPState.IDLE
219:         return new_body_part
220: 
221:     def process_request(self, body: dict[str, Any]) -> dict[str, Any]:
222: 
223:         current_session_id = ""
224:         try:
225:             user_id = body.get('metadata', {}).get('user_id', '')
226:             if '_session_' in user_id:
227:                 current_session_id = user_id.split('_session_')[1]
228:         except Exception as e:
229:             logger.error(f"Failed to extract session ID: {e}")
230:             raise e
231:         
232:         session_path = Path(self.cache_path / current_session_id)
233:         session_path.mkdir(exist_ok=True)
234: 
235:         body = self._process_request_recursive(body)
236:         self._write_to_file(session_path / 'last_request.json', json.dumps(body, indent=2, ensure_ascii=False))
237:         return body
238: 
239: 
240:     def _estimate_tokens(self, text: str) -> int:
241:         """
242:         estimate tokens of text returning **the estimate number of tokens** XD
243:         """
244:         enc = tiktoken.get_encoding("cl100k_base")
245:         return len(enc.encode(text))
246:     
247:     def _load_state_file(self) -> None:
248:         """
249:         load state file
250:         """
251:         pass
252: 
253: 
254:     def _write_to_file(self, file_path:Path, content: str, log_message: str | None  = None) -> None:
255:         """
256:         write to file file_path the content optionally displaying log_message
257:         """
258:         try:
259:             # Create/truncate file (only last message)
260:             with open(file_path, "w", encoding="utf-8") as f:
261:                 f.write(content)
262: 
263:             if log_message: logger.debug(log_message)
264: 
265:         except Exception as e:
266:             # Don't crash proxy if logging fails
267:             logger.error(f"Failed to log context: {e}")
268:         
---TOOL_RESULT_WINDOW_6774486e-4f4f-4f4b-a8ca-fbd55efdfd10_END
