
import os
import json
import logging
import datetime
from pathlib import Path
from typing import Any, Optional, List, TYPE_CHECKING

import tiktoken

logger = logging.getLogger(__name__)


class RequestModifierState:
    def __init__(self) -> None:
        self.session_id: str = ""
        self.last_offset: int = 0


class RequestModifier:
    def __init__(self, cache_path:str = '.nisaba/request_cache/') -> None:
        self.cache_path:Path = Path(cache_path)
        self.state_file:Path = Path(self.cache_path / 'request_modifier_state.json')
        self.current_state: RequestModifierState = RequestModifierState()
        self.cache_path.mkdir(exist_ok=True)

    def _load_state(self) -> None:
        """
        Loads or initializes the state file
        """
        pass


    def _write_to_file(self, file_path:Path, content: str, log_message: str | None  = None) -> None:
        try:
            # Create/truncate file (only last message)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            if log_message: logger.debug(log_message)

        except Exception as e:
            # Don't crash proxy if logging fails
            logger.error(f"Failed to log context: {e}")
    

    def process_request(self, body: dict[str, Any]) -> dict[str, Any]:
        current_session_id = ""
        try:
            user_id = body.get('metadata', {}).get('user_id', '')
            if '_session_' in user_id:
                current_session_id = user_id.split('_session_')[1]
        except Exception as e:
            logger.error(f"Failed to extract session ID: {e}")
            raise e
        
        session_path = Path(self.cache_path / current_session_id)
        session_path.mkdir(exist_ok=True)
           
        self._write_to_file(session_path / 'last_request.json', json.dumps(body, indent=2, ensure_ascii=False))
        return body


    def estimate_tokens(self, text: str) -> int:
        """
        Token estimate using tiktoken.
        
        Args:
            text: Text to estimate
            
        Returns:
            Token count using cl100k_base encoding
        """
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
        