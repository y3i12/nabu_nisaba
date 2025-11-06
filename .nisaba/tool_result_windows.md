---TOOL_RESULT_WINDOW_3c12f86e-b46b-4bfc-9de9-335fe713bf7a
**type**: read_result
**file**: src/nisaba/wrapper/request_modifier.py
**lines**: 180-200
**total_lines**: 21

180:                             result[key] = part[key]
181:                         elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
182:                             result[key] = child_result
183:                             result_state = RMPState.UPDATE_AND_CONTINUE
184:                         elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
185:                             result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
186:        
187:             elif isinstance(part, list):
188:                 assert isinstance(modifier_rules, list)
189:                 result = []
190:                 logger.debug(f"    Processing list with {len(part)} items against {len(modifier_rules)} rules")
191:                 for i, block in enumerate(part):
192:                     logger.debug(f"      List item [{i}]: {type(block).__name__}")
193:                     self.state._p_state = RMPState.RECURSE_AND_ADD
194:                     for rule_idx, modifier_rule in enumerate(modifier_rules):
195:                         logger.debug(f"        Trying rule #{rule_idx} on item [{i}]")
196:                         child_result = self.__process_request_recursive(block, modifier_rule)
197:                         if RMPState.ADD_AND_CONTINUE == self.state._p_state:
198:                             result.append(block)
199:                             break
200:                         elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
---TOOL_RESULT_WINDOW_3c12f86e-b46b-4bfc-9de9-335fe713bf7a_END
