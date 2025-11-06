
import datetime
import json
import logging
import os
import re
import tiktoken

from enum import Enum
from pathlib import Path
from typing import Any, Optional, List, TYPE_CHECKING
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
logger.setLevel(logging.DEBUG)

# Setup file logging to .nisaba/logs/proxy.log
log_dir = Path(".nisaba/logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Add file handler if not already present
if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
    file_handler = RotatingFileHandler(
        log_dir / "proxy.log",
        maxBytes=10*1024*1024,  # 10MB
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
        self.last_block_offset: list[int] = [-1, -1] # message block, content_block
        self._p_state:RMPState = RMPState.IDLE
        self.tool_result_state:dict[str,dict] = {
        #   "toolu_{hash}": {
        #       'block_offset': tuple[int, int],
        #       'tool_result_status': f"{(success|error)}",
        #       'tool_output': (from tool_u.parent.text),
        #       'window_state': (open|closed),
        #       'start_line': n|0,
        #       'num_lines': n|-1,
        #       'tool_result_content': f"status:{tool_result_status}, window_state:{window_state}, window_id: {toolu_{hash}}"
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
                        }
                    ]
                },
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'tool_result',
                            'tool_use_id': self._tool_use_id_state,
                            'content': {
                                'type': 'text',
                                'text': self._process_tool_result
                            }
                        }
                    ]
                }
            ]
        }
    
    def _message_block_count(self, key:str, part:dict[Any,Any]) -> Any:
        self.state.last_block_offset[0] += 1 # moves message forward
        self.state.last_block_offset[1]  = -1 # resets content block
        self.state._p_state = RMPState.NOOP_CONTINUE
        pass

    def _content_block_count(self, key:str, part:dict[Any,Any]) -> Any:
        self.state.last_block_offset[1] += 1 # moves content forward
        self.state._p_state = RMPState.NOOP_CONTINUE
        pass

    def _tool_use_id_state(self, key:str, part:dict[Any,Any]) -> Any:
        toolu_id = part[key]
        logger.debug(f"  _tool_use_id_state: Found tool_use_id '{toolu_id}'")
        if toolu_id in self.state.tool_result_state:
            logger.debug(f"    Tool exists in state, returning stored content")
            self.state._p_state = RMPState.UPDATE_AND_CONTINUE
            return self.state.tool_result_state[toolu_id]['tool_result_content']
        
        logger.debug(f"    Tool is new, adding to state")
        self.state._p_state = RMPState.ADD_AND_CONTINUE

    def _process_tool_result(self, key:str, part:dict[Any,Any]) -> Any:
        toolu_id = part[key]
        logger.debug(f"  _process_tool_result: Processing tool result for '{toolu_id}'")
        toolu_obj = {
            'block_offset': self.state.last_block_offset,
            'tool_result_status': "success", # TODO: get this from proxy
            'tool_output': part['content']['text'],
            'window_state': "open", # TODO: integrate with window management
            'start_line': 0, # TODO: integrate with window management
            'num_lines': -1, # TODO: integrate with window management
            'tool_result_content': f"status: success, window_state:open, window_id: {toolu_id}"
        }

        self.state.tool_result_state[toolu_id] = toolu_obj
        self.state._p_state = RMPState.ADD_AND_CONTINUE

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
        
        session_path = Path(self.cache_path / current_session_id)
        session_path.mkdir(exist_ok=True)

        body = self._process_request_recursive(body)
        self._write_to_file(session_path / 'last_request.json', json.dumps(body, indent=2, ensure_ascii=False))
        self._write_to_file(session_path / 'state.json', json.dumps(self.state.to_dict(), indent=2, ensure_ascii=False))
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
        