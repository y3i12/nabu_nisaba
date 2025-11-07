
import datetime
import json
import logging
import os
import re
import tiktoken

from enum import Enum
from pathlib import Path
from typing import Any, Optional, List, Dict, TYPE_CHECKING
from logging.handlers import RotatingFileHandler


class RequestModifierPrrocessingState(Enum):
    IDLE = 0
    
    RECURSE_AND_ADD = 1
    PROCESS_MATCH = 2

    ADD_AND_CONTINUE = 3
    IGNORE_AND_CONTINUE = 4
    UPDATE_AND_CONTINUE = 5
    NOOP_CONTINUE = 6

RMPState = RequestModifierPrrocessingState

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# Setup file logging to .nisaba/logs/proxy.log
log_dir = Path(".nisaba/logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Add file handler if not already present
if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
    file_handler = RotatingFileHandler(
        log_dir / "proxy.log",
        maxBytes=1*1024*1024,  # 1MB
        backupCount=3
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

class RequestModifierState:
    def __init__(self) -> None:
        self.session_id: str = ""
        self.last_block_offset: list[int] = [0, 0] # message block, content_block
        self._p_state:RMPState = RMPState.IDLE
        self.tool_result_state:dict[str,dict] = {
        #   "toolu_{hash}": {
        #       'block_offset': tuple[int, int],
        #       'tool_output': (from tool_u.parent.text),
        #       'window_state': (open|closed),
        #       'tool_result_content': f"window_state:{window_state}, tool_use_id: {toolu_{hash}}"
        #   }
        }
    
    def to_dict(self) -> dict:
        """Convert state to JSON-serializable dict"""
        return {
            'session_id': self.session_id,
            'last_block_offset': self.last_block_offset,
            '_p_state': self._p_state.value,  # Convert enum to int
            'tool_result_state': self.tool_result_state
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RequestModifierState':
        """Reconstruct state from dict"""
        state = cls()
        state.session_id = data.get('session_id', '')
        state.last_block_offset = data.get('last_block_offset', [-1, -1])
        state._p_state = RMPState(data.get('_p_state', 0))  # Convert int back to enum
        state.tool_result_state = data.get('tool_result_state', {})
        return state


class RequestModifier:
    def __init__(self, cache_path:str = '.nisaba/request_cache/') -> None:
        self.cache_path:Path = Path(cache_path)
        self.state_file:Path = Path(self.cache_path / 'request_modifier_state.json')
        self.state: RequestModifierState = RequestModifierState()
        self.cache_path.mkdir(exist_ok=True)
        self.modifier_rules = {
            'messages': [
                {
                    'role': self._message_block_count,
                    'content': [
                        {
                            'type': self._content_block_count,
                            'tool_use_id': self._tool_use_id_state,
                            'content': self._modify_tool_result_content
                        }
                    ]
                }
            ]
        }
    
    def _message_block_count(self, key:str, part:dict[Any,Any]) -> Any:
        self.state.last_block_offset[0] += 1 # moves message forward
        self.state.last_block_offset[1]  = 0 # resets content block
        self.state._p_state = RMPState.NOOP_CONTINUE
        pass

    def _is_nisaba_tool(self, part: dict[Any, Any]) -> bool:
        """Check if tool result is from a nisaba tool by parsing content."""
        content = part.get('content', {})
        
        # Extract text from different content structures
        if isinstance(content, dict):
            text = content.get('text', '')
        elif isinstance(content, list) and content:
            text = content[0].get('text', '') if isinstance(content[0], dict) else ''
        else:
            return False
        
        # Try to parse JSON and check for nisaba flag
        if text:
            try:
                output = json.loads(text)
                return output.get('nisaba') is True
            except:
                pass  # Not JSON or parse error
        
        return False
    
    def _content_block_count(self, key:str, part:dict[Any,Any]) -> Any:
        self.state.last_block_offset[1] += 1 # moves content forward
        self.state._p_state = RMPState.NOOP_CONTINUE
        pass

    def _tool_use_id_state(self, key:str, part:dict[Any,Any]) -> Any:
        # part is the tool_result content block dict
        # part[key] is the tool_use_id value
        toolu_id = part[key]
        logger.debug(f"  _tool_use_id_state: Found tool_use_id '{toolu_id}'")
        
        # Check if nisaba tool (parse once, cache result in state)
        is_nisaba = self._is_nisaba_tool(part)
        
        if toolu_id in self.state.tool_result_state:
            logger.debug(f"    Tool exists in state (already tracked)")
            self.state._p_state = RMPState.ADD_AND_CONTINUE  # Keep original ID
            return None  # Don't replace anything
        
        logger.debug(f"    Tool is new, adding to state (is_nisaba={is_nisaba})")
        
        # Create tool state entry - extract output from content
        tool_output = ""
        if 'content' in part:
            content = part['content']
            # Handle both dict and list structures
            if isinstance(content, dict):
                tool_output = content.get('text', str(content))
            elif isinstance(content, list):
                # Extract text from first text block
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        tool_output = block.get('text', '')
                        break
            else:
                tool_output = str(content)
        
        toolu_obj = {
            'block_offset': list(self.state.last_block_offset),  # Copy the offset, don't reference it
            'tool_output': tool_output if tool_output else "",
            'window_state': "open",
            'is_nisaba': is_nisaba,  # Cache nisaba detection result
            'tool_result_content': (
                                        # Nisaba tools: no header, just plain output
                                        tool_output if is_nisaba
                                        # Regular tools: add header + separator
                                        else (
                                            f"window_state:open, tool_use_id: {toolu_id}\n"
                                            f"---\n"
                                            f"{tool_output}"
                                        )
                                    )
        }
        
        self.state.tool_result_state[toolu_id] = toolu_obj
        self.state._p_state = RMPState.ADD_AND_CONTINUE

    def _modify_tool_result_content(self, key:str, part:dict[Any,Any]) -> Any:
        # key is 'content', part is the entire tool_result block
        # Check if this tool_use_id is in state and should be compacted
        logger.debug(f"  _modify_tool_result_content: Checking if content should be replaced")
        
        toolu_id = part.get('tool_use_id')
        if not toolu_id:
            logger.debug(f"    No tool_use_id found, keeping original")
            self.state._p_state = RMPState.ADD_AND_CONTINUE
            return None
        
        if toolu_id not in self.state.tool_result_state:
            # Tool not in state yet (first encounter) - keep original
            logger.debug(f"    Tool {toolu_id} not in state, keeping original")
            self.state._p_state = RMPState.ADD_AND_CONTINUE
            return None
        
        tool_state = self.state.tool_result_state[toolu_id]
        
        # Check cached nisaba flag (no parsing needed!)
        if tool_state.get('is_nisaba', False):
            logger.debug(f"    Nisaba tool (from cached flag), keeping original")
            self.state._p_state = RMPState.ADD_AND_CONTINUE
            return None
        
        window_state = tool_state.get('window_state', 'open')
        
        if window_state == "open":
            # Tool is open - add header + separator + content
            full_text = tool_state.get('tool_result_content', '')
            logger.debug(f"    Tool {toolu_id} is open, adding header to content")
            self.state._p_state = RMPState.UPDATE_AND_CONTINUE
            return [{"type": "text", "text": full_text}]
        # Tool is closed - replace with compact version
        compact_text = f"window_state:closed, tool_use_id: {toolu_id}\n"
        logger.debug(f"    Tool {toolu_id} is closed, replacing with compact format")
        
        # Match the structure of the original content
        original_content = part.get('content')
        if isinstance(original_content, str):
            # Simple string format
            self.state._p_state = RMPState.UPDATE_AND_CONTINUE
            return compact_text
        elif isinstance(original_content, dict):
            # Dict format: {"type": "text", "text": "..."}
            self.state._p_state = RMPState.UPDATE_AND_CONTINUE
            return {"type": "text", "text": compact_text}
        elif isinstance(original_content, list):
            # List format: [{"type": "text", "text": "..."}]
            self.state._p_state = RMPState.UPDATE_AND_CONTINUE
            return [{"type": "text", "text": compact_text}]
        else:
            # Unknown format, keep original
            logger.debug(f"    Unknown content format: {type(original_content)}")
            self.state._p_state = RMPState.ADD_AND_CONTINUE
            return None

    def __process_request_recursive(self, part:dict[Any,Any]|list[Any], modifier_rules:dict[str,Any]|list[Any]) -> Any:
        if RMPState.IDLE == self.state._p_state:
            return 
        
        result = None
        result_state = RMPState.ADD_AND_CONTINUE
        
        logger.debug(f"  __process_request_recursive: state={self.state._p_state.name}, part_type={type(part).__name__}, rules_type={type(modifier_rules).__name__}")

        if RMPState.RECURSE_AND_ADD == self.state._p_state:
            if isinstance(part, dict):
                assert isinstance(modifier_rules, dict)
                result = {}
                
                logger.debug(f"    Processing dict with keys: {list(part.keys())}")

                for key in part.keys():
                    if key not in modifier_rules:
                        result[key] = part[key]
                        logger.debug(f"      Key '{key}' not in rules, copying")
                    else:
                        logger.debug(f"      Key '{key}' MATCHED in rules, processing...")
                        
                        # Check if rule is a callable - execute it directly
                        if callable(modifier_rules[key]):
                            logger.debug(f"        Rule is callable: {modifier_rules[key].__name__}")
                            logger.debug(f"        Calling {modifier_rules[key].__name__}('{key}', part)")
                            callable_result = modifier_rules[key](key, part)
                            logger.debug(f"        Callable returned state: {self.state._p_state.name}")
                            
                            if RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
                                result[key] = callable_result
                                result_state = RMPState.UPDATE_AND_CONTINUE
                            elif RMPState.NOOP_CONTINUE == self.state._p_state:
                                result[key] = part[key]
                            else:
                                result[key] = part[key]
                        else:
                            # Not a callable, recurse into structure
                            self.state._p_state = RMPState.PROCESS_MATCH
                            child_result = self.__process_request_recursive(part[key], modifier_rules[key])
                            if RMPState.ADD_AND_CONTINUE == self.state._p_state:
                                result[key] = part[key]
                            elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
                                result[key] = child_result
                                result_state = RMPState.UPDATE_AND_CONTINUE
                            elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
                                result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
       
            elif isinstance(part, list):
                assert isinstance(modifier_rules, list)
                result = []
                logger.debug(f"    Processing list with {len(part)} items against {len(modifier_rules)} rules")
                for i, block in enumerate(part):
                    logger.debug(f"      List item [{i}]: {type(block).__name__}")
                    self.state._p_state = RMPState.RECURSE_AND_ADD
                    for rule_idx, modifier_rule in enumerate(modifier_rules):
                        logger.debug(f"        Trying rule #{rule_idx} on item [{i}]")
                        child_result = self.__process_request_recursive(block, modifier_rule)
                        if RMPState.ADD_AND_CONTINUE == self.state._p_state:
                            result.append(block)
                            break
                        elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
                            result.append(child_result)
                            result_state = RMPState.UPDATE_AND_CONTINUE
                            break
                        elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
                            result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
                            break
                        elif RMPState.NOOP_CONTINUE == self.state._p_state:
                            pass

            else:
                result = part

        elif RMPState.PROCESS_MATCH == self.state._p_state:
            # FIX: Handle non-dict types in PROCESS_MATCH state
            if not isinstance(part, dict):
                # When we have a list in PROCESS_MATCH, check if rules are also list
                if isinstance(part, list) and isinstance(modifier_rules, list):
                    # Valid list-to-list pattern matching - switch to RECURSE_AND_ADD and re-process
                    logger.debug(f"    PROCESS_MATCH got list with list rules, switching to RECURSE_AND_ADD")
                    self.state._p_state = RMPState.RECURSE_AND_ADD
                    # Re-process with new state
                    return self.__process_request_recursive(part, modifier_rules)
                else:
                    # Structure mismatch - skip this rule
                    logger.debug(f"    PROCESS_MATCH got non-dict ({type(part).__name__}), skipping rule")
                    self.state._p_state = RMPState.ADD_AND_CONTINUE
                    return part
            
            # Check if both are dicts for dict processing
            if not isinstance(modifier_rules, dict):
                if isinstance(part, dict):
                    # part is dict but rules aren't - structure mismatch
                    logger.debug(f"    PROCESS_MATCH got non-dict rules ({type(modifier_rules).__name__}), skipping")
                    self.state._p_state = RMPState.ADD_AND_CONTINUE
                    return part
            
            # Now safe to proceed with dict handling (only log if we have dicts)
            if isinstance(part, dict) and isinstance(modifier_rules, dict):
                logger.debug(f"    PROCESS_MATCH: Checking dict keys: {list(part.keys())} against rules: {list(modifier_rules.keys())}")
                assert isinstance(part, dict)
                assert isinstance(modifier_rules, dict)
            else:
                # If we get here, we're in RECURSE_AND_ADD state after list detection
                # This is the fall-through case - return to continue processing
                pass

            result = {}

            # match strings
            self.state._p_state = RMPState.UPDATE_AND_CONTINUE
            for key in modifier_rules:
                if isinstance(modifier_rules[key], str):
                    if key not in part or not isinstance(part[key], str) or not re.match(modifier_rules[key], part[key]):
                        self.state._p_state = RMPState.ADD_AND_CONTINUE
                        return

            # call functors, they can change results
            logger.debug(f"    Checking for callable rules...")
            for key in modifier_rules:
                if not callable(modifier_rules[key]):
                    continue

                logger.debug(f"      Found callable for key '{key}'")
                if key not in part:
                    logger.debug(f"        Key '{key}' not in part, skipping callable")
                    self.state._p_state = RMPState.ADD_AND_CONTINUE
                    return
                
                logger.debug(f"        Calling {modifier_rules[key].__name__}('{key}', ...)")
                callable_result = modifier_rules[key](key, part)
                logger.debug(f"        Callable returned state: {self.state._p_state.name}")

                if RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
                    logger.debug(f"        Updating result with callable return value")
                    result = callable_result
                    result_state = RMPState.UPDATE_AND_CONTINUE
                elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
                    result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
                    return
                        
            # recurse remaining parts
            for key in part:
                if key in result:
                    continue

                if key not in modifier_rules:
                    result[key] = part[key]
                    continue

                self.state._p_state = RMPState.RECURSE_AND_ADD
                child_result = self.__process_request_recursive(part[key], modifier_rules[key])
                if RMPState.ADD_AND_CONTINUE == self.state._p_state:
                    result[key] = part[key]
                elif RMPState.UPDATE_AND_CONTINUE == self.state._p_state:
                    result[key] = child_result
                    result_state = RMPState.UPDATE_AND_CONTINUE
                elif RMPState.IGNORE_AND_CONTINUE == self.state._p_state:
                    result_state = RMPState.UPDATE_AND_CONTINUE # don't add but update structure
            
        self.state._p_state = result_state
        return result

    def _process_request_recursive(self, body_part:dict[Any,Any]|list[Any]) -> Any:
        self.state._p_state = RMPState.RECURSE_AND_ADD
        new_body_part = self.__process_request_recursive(part=body_part, modifier_rules=self.modifier_rules)
        self.state._p_state = RMPState.IDLE
        return new_body_part

    def process_request(self, body: dict[str, Any]) -> dict[str, Any]:
        logger.debug("=" * 60)
        logger.debug("RequestModifier.process_request() starting")
        logger.debug(f"Messages count: {len(body.get('messages', []))}")
        
        current_session_id = ""
        try:
            user_id = body.get('metadata', {}).get('user_id', '')
            if '_session_' in user_id:
                current_session_id = user_id.split('_session_')[1]
                logger.debug(f"Session ID: {current_session_id}")
        except Exception as e:
            logger.error(f"Failed to extract session ID: {e}")
            raise e
        
        if "" == current_session_id:
            return body
        
        # inner_content_list = [{'text': 'Warmup'}]
        # outer_content_list = [{'content':inner_content_list}]

        # try:
        #     if  body.get('messages', outer_content_list)[0].get('content', inner_content_list)[0].get('text', 'Warmup') == 'Warmup':
        #         return body
        # except Exception as e:
        #     logger.warning(f"Error while detecting `Warmup` message - skipping request, error: {e}")
        #     return body

            # if re.match(body.get('model', 'haiku'), 'haiku'):
            #     return body

        session_path = Path(self.cache_path / current_session_id)
        session_path.mkdir(exist_ok=True)
        
        self._write_to_file(session_path / 'original_context.json', json.dumps(body, indent=2, ensure_ascii=False), "Original request written")

        body = self._process_request_recursive(body)
        self._write_to_file(session_path / 'modified_context.json', json.dumps(body, indent=2, ensure_ascii=False), "Last request written")
        self._write_to_file(session_path / 'state.json', json.dumps(self.state.to_dict(), indent=2, ensure_ascii=False), "State written")
        return body


    def _estimate_tokens(self, text: str) -> int:
        """
        estimate tokens of text returning **the estimate number of tokens** XD
        """
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    
    def _load_state_file(self) -> None:
        """
        load state file
        """
        pass


    def _write_to_file(self, file_path:Path, content: str, log_message: str | None  = None) -> None:
        """
        write to file file_path the content optionally displaying log_message
        """
        try:
            # Create/truncate file (only last message)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            if log_message: logger.debug(log_message)

        except Exception as e:
            # Don't crash proxy if logging fails
            logger.error(f"Failed to log context: {e}")
    
    def close_tool_results(self, tool_ids: List[str]) -> Dict[str, Any]:
        """
        Close tool results (compact view in future requests).
        
        Args:
            tool_ids: List of tool IDs to close
            
        Returns:
            Dict with success status and modified tool IDs
        """
        modified = []
        not_found = []
        
        for tool_id in tool_ids:
            if tool_id in self.state.tool_result_state:
                # Skip nisaba tools - they shouldn't be closed
                if self.state.tool_result_state[tool_id].get('is_nisaba', False):
                    not_found.append(tool_id)
                    logger.debug(f"Skipping nisaba tool: {tool_id}")
                    continue
                
                self.state.tool_result_state[tool_id]['window_state'] = 'closed'
                # Update the content string for consistency
                tool_obj = self.state.tool_result_state[tool_id]
                tool_obj['tool_result_content'] = f"window_state:closed, tool_use_id: {tool_id}\n"
                modified.append(tool_id)
                logger.debug(f"Closed tool result: {tool_id}")
            else:
                not_found.append(tool_id)
                logger.debug(f"Tool result not found: {tool_id}")
        
        return {
            'modified': modified,
            'not_found': not_found
        }
    
    def open_tool_results(self, tool_ids: List[str]) -> Dict[str, Any]:
        """
        Open tool results (full view in future requests).
        
        Args:
            tool_ids: List of tool IDs to open
            
        Returns:
            Dict with success status and modified tool IDs
        """
        modified = []
        not_found = []
        
        for tool_id in tool_ids:
            if tool_id in self.state.tool_result_state:
                # Skip nisaba tools - they shouldn't be opened/closed
                if self.state.tool_result_state[tool_id].get('is_nisaba', False):
                    not_found.append(tool_id)
                    logger.debug(f"Skipping nisaba tool: {tool_id}")
                    continue
                
                self.state.tool_result_state[tool_id]['window_state'] = 'open'
                # Restore full content format
                tool_obj = self.state.tool_result_state[tool_id]
                tool_obj['tool_result_content'] = (
                    f"window_state:open, tool_use_id: {tool_id}\n"
                    f"---\n"
                    f"{tool_obj.get('tool_output', '')}"
                )
                modified.append(tool_id)
                logger.debug(f"Opened tool result: {tool_id}")
            else:
                not_found.append(tool_id)
                logger.debug(f"Tool result not found: {tool_id}")
        
        return {
            'modified': modified,
            'not_found': not_found
        }
    
    def get_tool_states(self) -> Dict[str, Dict]:
        """
        Get all tracked tool states.
        
        Returns:
            Dict of tool_id -> tool state info
        """
        return {
            tool_id: {
                'window_state': info['window_state'],
                'status': info['tool_result_status'],
                'offset': info['block_offset']
            }
            for tool_id, info in self.state.tool_result_state.items()
        }
        