"""
Augments injection proxy using mitmproxy.

Intercepts requests to Anthropic API and replaces __NISABA_AUGMENTS_PLACEHOLDER__
with actual augments content. Supports checkpoint-based context compression.
"""

import datetime
import importlib
import json
import logging
import os
import tiktoken


from logging.handlers import RotatingFileHandler
from mitmproxy import http
from nisaba.structured_file import JsonStructuredFile, StructuredFileCache
from nisaba.wrapper.request_modifier import RequestModifier
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from nisaba.augments import AugmentManager

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Ensure log directory exists
log_dir = Path(".nisaba/logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Add file handler for proxy logs
if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
    file_handler = RotatingFileHandler(
        log_dir / "proxy.log",
        maxBytes=1*1024*1024,  # 10MB
        backupCount=3
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.info("Proxy logging initialized to .nisaba/logs/proxy.log")


# Module-level singleton for RequestModifier access
_REQUEST_MODIFIER_INSTANCE = None

def _set_request_modifier(instance):
    """Store the RequestModifier instance for tool access."""
    global _REQUEST_MODIFIER_INSTANCE
    _REQUEST_MODIFIER_INSTANCE = instance

def get_request_modifier():
    """Get the active RequestModifier instance."""
    assert(_REQUEST_MODIFIER_INSTANCE)
    return _REQUEST_MODIFIER_INSTANCE


class FileCache:
    """Manages file loading with mtime-based caching."""

    def __init__(self, file_path: Path, name: str = "file", tag: str = "TAG"):
        """
        Initialize file cache.

        Args:
            file_path: Path to the file to cache
            name: Human-readable name for logging
        """
        self.file_path = file_path
        self.name = name
        self.tag = tag
        self.content: str = ""
        self._last_mtime: Optional[float] = None

    def load(self) -> str:
        """
        Load content from file if modified since last load.

        Returns:
            File content (empty string if file doesn't exist)
        """
        if not self.file_path.exists():
            if self._last_mtime is not None:  # Only warn if file existed before
                logger.warning(f"{self.name} not found: {self.file_path}")
            self.content = ""
            self._last_mtime = None
            return self.content

        current_mtime = self.file_path.stat().st_mtime

        # Only reload if file changed (or first load)
        if current_mtime != self._last_mtime:
            self.content = f"\n---{self.tag}\n{self.file_path.read_text()}\n---{self.tag}_END"
            logger.info(f"Loaded {self.name} from {self.file_path} ({len(self.content)} chars)")
            self._last_mtime = current_mtime

        return self.content


class AugmentInjector:
    """
    mitmproxy addon that injects augments content into Anthropic API requests.

    Intercepts POST requests to api.anthropic.com, parses the JSON body,
    finds system prompt blocks containing __NISABA_AUGMENTS_PLACEHOLDER__,
    and replaces:
    - First occurrence: replaced with augments content from file
    - Remaining occurrences: deleted (replaced with empty string)
    """

    def __init__(
        self,
        augment_manager: Optional["AugmentManager"] = None
    ):
        """
        Initialize augments injector.

        Can operate in two modes:
        1. File-based (legacy): reads from augments_file
        2. Shared-state (unified): uses shared AugmentManager

        Args:
            augments_file: Path to file containing augments content.
                         If None, reads from NISABA_AUGMENTS_FILE env var.
            augment_manager: Shared AugmentManager instance (unified mode)
        """
        # Unified mode (shared AugmentManager)
        self.augment_manager = augment_manager

        # File-based caching for augments and system prompt
        self.augments_cache = StructuredFileCache(
            Path("./.nisaba/tui/augment_view.md"),
            "augments",
            "AUGMENTS"
        )
        self.system_prompt_cache = StructuredFileCache(
            Path("./.nisaba/tui/system_prompt.md"),
            "system prompt",
            "USER_SYSTEM_PROMPT_INJECTION"
        )
        self.core_system_prompt_cache = StructuredFileCache(
            Path("./.nisaba/tui/core_system_prompt.md"),
            "Core system prompt",
            "CORE_SYSTEM_PROMPT"
        )
        self.transcript_cache = StructuredFileCache(
            Path("./.nisaba/tui/compacted_transcript.md"),
            "last session transcript",
            "COMPACTED_TRANSCRIPT"
        )
        self.structural_view_cache = StructuredFileCache(
            Path("./.nisaba/tui/structural_view.md"),
            "structural view",
            "STRUCTURAL_VIEW"
        )
        self.todos_cache = StructuredFileCache(
            Path("./.nisaba/tui/todo_view.md"),
            "todos",
            "TODOS"
        )
        self.notifications_cache = StructuredFileCache(
            Path("./.nisaba/tui/notification_view.md"),
            "notifications",
            "NOTIFICATIONS"
        )
        self.checkpoint_file = JsonStructuredFile(
            file_path=Path("./.nisaba/tui/notification_state.json"),
            name="notification_state",
            default_factory=lambda: { "session_id": "", "last_tool_id_seen": "" }
        )
        
        self.filtered_tools:set[str] = { "TodoWrite" }
        self.core_system_prompt_tokens:int = 0

        # Store reference globally for tool access
        self.request_modifier:RequestModifier = RequestModifier()
        _set_request_modifier(self.request_modifier)

        # Initial load
        if augment_manager is None:
            self.augments_cache.load()
        else:
            # Unified mode - get content from AugmentManager
            logger.info("AugmentInjector initialized in unified mode (shared AugmentManager)")

        self.system_prompt_cache.load()
        self.transcript_cache.load()
        self.structural_view_cache.load()
        self.todos_cache.load()
        self.notifications_cache.load()

    def request(self, flow: http.HTTPFlow) -> None:
        """
        Intercept and modify requests.

        Called by mitmproxy for each HTTP request. If the request is to
        Anthropic API, we parse the body, replace the placeholder, and
        modify the request.

        In unified mode, also checks for checkpoint and applies compression.

        Args:
            flow: mitmproxy HTTPFlow object
        """
        # Only intercept Anthropic API requests
        if not self._is_anthropic_request(flow):
            return

        try:
            # Parse request body as JSON
            body = json.loads(flow.request.content)
            self.request_modifier.clear_visible_tools()
            body = self.request_modifier.process_request(body)

            # Detect delta and generate notifications
            self._process_notifications(body)

            # Process system prompt blocks
            if self._inject_augments(body):
                flow.request.content = json.dumps(body).encode('utf-8')
                

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse request JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing request: {e}")

    def _is_anthropic_request(self, flow: http.HTTPFlow) -> bool:
        """
        Check if this is an Anthropic API request.

        Args:
            flow: mitmproxy HTTPFlow object

        Returns:
            True if this is a request to Anthropic API
        """
        return (
            flow.request.method == "POST" and
            "api.anthropic.com" in flow.request.pretty_host
        )

    def _inject_augments(self, body: dict) -> bool:
        """
        Inject augments content into request body.

        Finds __NISABA_AUGMENTS_PLACEHOLDER__ in system blocks:
        - First occurrence: replaced with augments content
        - Remaining occurrences: deleted

        Args:
            body: Parsed JSON request body (modified in place)

        Returns:
            True if any replacements were made
        """
        # Filter native tools on every request
        if "tools" in body:
            filtered_tools = []
            for tool in body["tools"]:
                if "name" in tool and tool["name"] in self.filtered_tools:
                    continue
                filtered_tools.append(tool)
            body["tools"] = filtered_tools

        if "system" in body:
            if len(body["system"]) < 2:                
                body["system"].append(
                    {
                        "type": "text",
                        "text": (
                            f"\n{self.system_prompt_cache.load()}"
                            f"\n{self.augments_cache.load()}"
                            f"\n{self.transcript_cache.load()}"
                        ),
                        "cache_control": {
                            "type": "ephemeral"
                        }
                    }
                )
            elif "text" in body["system"][1]:
                # Generate status bar from current state
                if not self.core_system_prompt_cache.file_path.exists() or self.core_system_prompt_cache.content != body["system"][1]["text"]:
                    self.core_system_prompt_cache.write(body["system"][1]["text"])

                
                body["system"][1]["text"] = (
                    f"\n{self.system_prompt_cache.load()}"
                    f"\n{self.core_system_prompt_cache.load()}"
                    f"\n{self.augments_cache.load()}"
                    f"\n{self.transcript_cache.load()}"
                )

        
        if 'messages' in body and len(body["messages"]) > 2:
            visible_tools = self.request_modifier.get_and_visible_tool_result_views()
            if visible_tools:
                visible_tools = f"\n---RESULTS_END\n{visible_tools}\n---RESULTS_END"

            status_bar = f"\n{self._generate_status_bar(body, visible_tools)}"

            body['messages'].append( 
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"<system-reminder>\n--- WORKSPACE ---\n{(
                                    f"\n{status_bar}"
                                    f"\n{self.structural_view_cache.load()}"
                                    f"{visible_tools}" # this has a newline when populated
                                    f"\n{self.notifications_cache.load()}"
                                    f"\n{self.todos_cache.load()}"
                                )}\n</system-reminder>"
                        }
                    ]
                }
            )
            self._write_to_file(Path(os.getcwd()) / '.nisaba/modified_context.json', json.dumps(body, indent=2, ensure_ascii=False), "Modified request written")
            return True
            
        return "tools" in body or "system" in body

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

    def _process_notifications(self, body: dict) -> None:
        """
        Detect delta in messages and generate notifications for new tool calls.
        Uses session-aware checkpoint to avoid duplicate notifications on restart.
        
        Args:
            body: Parsed JSON request body
        """
        # Extract current session ID
        try:
            user_id = body.get('metadata', {}).get('user_id', '')
            if '_session_' in user_id:
                current_session_id = user_id.split('_session_')[1]
            else:
                current_session_id = None
        except Exception as e:
            logger.warning(f"Failed to extract session ID: {e}")
            current_session_id = None
        
        # Load checkpoint
        checkpoint = self.checkpoint_file.load_json()
        last_session_id = checkpoint.get('session_id')
        last_tool_id_seen = checkpoint.get('last_tool_id_seen')
        
        # Determine if this is a new session
        is_new_session = (current_session_id != last_session_id)
        
        messages = body.get('messages', [])
        
        # Collect all tool_use blocks with their IDs (in order)
        all_tool_calls = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = msg.get('content', [])
            if isinstance(content, str):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_use':
                    tool_id = block.get('id')
                    if tool_id:
                        all_tool_calls.append({
                            'id': tool_id,
                            'name': block.get('name', 'unknown'),
                            'input': block.get('input', {})
                        })
        
        # Determine which tool calls are "new" for notification
        new_tool_calls = []
        if is_new_session:
            # New session: notify all tools
            new_tool_calls = all_tool_calls
        else:
            # Same session: notify only tools after last_tool_id_seen
            found_last = (last_tool_id_seen is None)  # If None, include all
            for call in all_tool_calls:
                if found_last:
                    new_tool_calls.append(call)
                elif call['id'] == last_tool_id_seen:
                    found_last = True  # Start including from next tool
        
        # Build map of tool results (scan all messages)
        tool_results = {}
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = msg.get('content', [])
            if isinstance(content, str):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_result':
                    tool_use_id = block.get('tool_use_id')
                    if tool_use_id:
                        tool_results[tool_use_id] = block
        
        # Generate notifications
        notifications = []
        for call in new_tool_calls:
            result = tool_results.get(call['id'])
            if result:
                icon = '✗' if result.get('is_error') else '✓'
                summary = self._create_summary(call['name'], call, result)
                notifications.append(f"{icon} {call['name']}() → {summary}")
        
        # Write to file
        if notifications:
            self._write_notifications(notifications)
            logger.info(f"Generated {len(notifications)} notification(s)")
        
        # Update checkpoint with latest tool ID (if any tools exist)
        if all_tool_calls and current_session_id:
            last_tool_id = all_tool_calls[-1]['id']
            self.checkpoint_file.write_json({"session_id": current_session_id, "last_tool_id_seen": last_tool_id})
    
    def _create_summary(self, tool_name: str, call: dict, result: dict) -> str:
        """
        Create concise summary from tool result.
        Parses nisaba standard tool return format to extract semantic message.
        
        Args:
            tool_name: Name of the tool
            call: Tool call block (contains input parameters)
            result: Tool result block
            
        Returns:
            Concise summary string
        """
        import re
        
        try:
            content = result.get('content', '')
            
            # Parse JSON response from content
            if isinstance(content, list) and content:
                data = json.loads(content[0].get('text', '{}'))
            elif isinstance(content, str):
                data = json.loads(content)
            else:
                return "ok"
            
            # Extract 'data' field (contains markdown in nisaba standard format)
            data_field = data.get('data', '')
            
            # Parse markdown for **message**: field
            if isinstance(data_field, str):
                match = re.search(r'\*\*message\*\*:\s*\n\s*(.+)', data_field)
                if match:
                    return match.group(1).strip()
            
            # Fallback: use 'message' from root (also nisaba standard)
            if 'message' in data:
                return data['message']
                
        except Exception:
            pass
        
        return "ok"
    
    def _write_notifications(self, notifications: List[str]) -> None:
        """
        Write notifications to file.
        
        Args:
            notifications: List of notification strings
        """
        content = ""
        if notifications:
            content += "Recent activity:\n"
            content += "\n".join(notifications) + "\n"
        else:
            content += "(no recent activity)\n"
        
        notifications_file = Path("./.nisaba/tui/notification_view.md")
        notifications_file.write_text(content)
    

    def _estimate_tokens(self, text: str) -> int:
        """
        Accurate token estimate using tiktoken.
        
        Args:
            text: Text to estimate
            
        Returns:
            Exact token count using cl100k_base encoding
        """
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception as e:
            logger.warning(f"tiktoken encoding failed, using fallback: {e}")
            # Fallback to rough estimate if tiktoken fails
            return len(text) // 4
    
    def _generate_status_bar(self, body: dict, tool_results:str = "") -> str:
        """
        Generate status bar with segmented token usage.
        
        Calculates workspace, messages, and total token counts.
        Shows window counts for context awareness.
        Exports JSON for external status line tools.
        
        Args:
            body: Request body dict
            
        Returns:
            Formatted status bar with tags
        """
        # Extract model name
        model_name = body.get('model', 'unknown')
        
        # Load all caches (triggers mtime-based updates)
        self.system_prompt_cache.load()
        self.todos_cache.load()
        self.notifications_cache.load()
        self.augments_cache.load()
        self.structural_view_cache.load()
        self.transcript_cache.load()
        
        # Use cached token counts (no recalculation!)
        structural_view_tokens = self.structural_view_cache.token_count
        workspace_tokens = self.todos_cache.token_count + self.notifications_cache.token_count + structural_view_tokens
        
        # Count message tokens (properly, without JSON overhead)
        messages = body.get('messages', [])
        messages_tokens = 0
        for msg in messages:
            if isinstance(msg, dict):
                # Count role
                messages_tokens += self._estimate_tokens(msg.get('role', ''))
                # Count content
                content = msg.get('content', '')
                if isinstance(content, str):
                    messages_tokens += self._estimate_tokens(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            # Count actual content based on block type
                            block_type = block.get('type', '')
                            if block_type == 'text':
                                messages_tokens += self._estimate_tokens(block.get('text', ''))
                            elif block_type == 'tool_use':
                                messages_tokens += self._estimate_tokens(block.get('name', ''))
                                messages_tokens += self._estimate_tokens(str(block.get('input', {})))
                            elif block_type == 'tool_result':
                                result_content = block.get('content', '')
                                if isinstance(result_content, str):
                                    messages_tokens += self._estimate_tokens(result_content)
                                else:
                                    messages_tokens += self._estimate_tokens(str(result_content))
                            elif block_type == 'thinking':
                                messages_tokens += self._estimate_tokens(block.get('thinking', ''))
                            else:
                                # Fallback for unknown block types
                                messages_tokens += self._estimate_tokens(str(block))
        
        tool_tokens = self._estimate_tokens(json.dumps(body.get('tools', [])))
        tool_result_tokens = self._estimate_tokens(tool_results)
        # Total usage
        total_tokens = workspace_tokens + self.system_prompt_cache.token_count + self.core_system_prompt_cache.token_count + tool_tokens + self.augments_cache.token_count + tool_result_tokens + messages_tokens
        budget = 200  # 200k token budget

        # Export JSON for external status line tools
        status_data = {
            "model": model_name,
            "workspace": {
                "total": workspace_tokens,
                "system": {
                    "prompt": self.system_prompt_cache.token_count + self.core_system_prompt_cache.token_count,
                    "tools": tool_tokens,
                    "transcript": self.transcript_cache.token_count
                },
                "augments": self.augments_cache.token_count,
                "view": structural_view_tokens,
                "tool_results": tool_result_tokens,
                "notifications": self.notifications_cache.line_count - 1,  # header + endl compensation,
                "todos": self.todos_cache.line_count - 1  # header + endl compensation
            },
            "messages": messages_tokens,
            "total": total_tokens,
            "budget": budget * 1000
        }

        ws = status_data['workspace']
        
        parts = [
            f"SYSTEM({ws['system']['prompt']//1000}k)",
            f"TOOLS({ws['system']['tools']//1000}k)",
            f"AUG({ws['augments']//1000}k)",
            f"COMPTRANS({ws['system']['transcript']//1000}k)",
            f"MSG({status_data['messages']//1000}k)",
            f"WORKPACE({ws['total']//1000}k)",
            f"STVIEW({ws['view']//1000}k)",
            f"RESULTS({ws['tool_results']//1000}k)",
            f"MODEL({model_name})",
            f"{status_data['total']//1000}k/{status_data['budget']//1000}k"
        ]
        SPLIT = 4
        status = "\n".join([
            ' | '.join(parts[0:SPLIT]),
            ' | '.join(parts[SPLIT:-2]),
            ' | '.join(parts[-2:]),
        ])
        
        try:
            status_file = Path("./.nisaba/tui/status_bar_live.txt")
            status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(status_file, 'w') as f:
                status_file.write_text(status)
        except Exception as e:
            logger.warning(f"Failed to write status JSON: {e}")
        
        return f"---STATUS_BAR\n{status}\n---STATUS_BAR_END"

def load(loader):
    """
    Called when mitmproxy loads this script.

    This is the mitmproxy addon interface for script-based addons.
    """
    # Augments file comes from environment variable
    addon = AugmentInjector()

    # Add option for documentation
    loader.add_option(
        name="nisaba_augments_file",
        typespec=str,
        default="./.nisaba/tui/augment_view.md",
        help="Path to augments content file",
    )

    # Register the addon
    return addon


# Instantiate addon for mitmproxy
addons = [AugmentInjector()]
