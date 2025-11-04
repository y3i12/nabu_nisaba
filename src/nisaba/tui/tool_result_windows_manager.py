"""Tool result windows manager - persistent tool output visibility."""

import logging
import json
import subprocess
from typing import Dict, List, Optional
from pathlib import Path

from nisaba.tui.tool_result_window import ToolResultWindow

logger = logging.getLogger(__name__)


class ToolResultWindowsManager:
    """Manages collection of tool result windows."""

    def __init__(self):
        self.windows: Dict[str, ToolResultWindow] = {}
        self.max_render_lines = 10000  # Default truncation
        self.load_state()

    @property
    def state_file(self) -> Path:
        """Path to state persistence file."""
        return Path.cwd() / ".nisaba" / "tool_result_windows_state.json"

    def save_state(self) -> None:
        """Save windows state to JSON."""
        state = {
            "windows": {
                wid: {
                    "id": w.id,
                    "window_type": w.window_type,
                    "content": w.content,
                    "metadata": w.metadata,
                    "opened_at": w.opened_at,
                    "file_path": w.file_path,
                    "start_line": w.start_line,
                    "end_line": w.end_line,
                    "command": w.command,
                    "exit_code": w.exit_code,
                    "pattern": w.pattern,
                    "glob_pattern": w.glob_pattern
                }
                for wid, w in self.windows.items()
            }
        }

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2), encoding='utf-8')
        logger.debug(f"Saved {len(self.windows)} tool result windows to state file")

    def load_state(self) -> None:
        """Restore windows from JSON."""
        if not self.state_file.exists():
            logger.debug("No state file found, starting with empty tool result windows")
            return

        try:
            state = json.loads(self.state_file.read_text(encoding='utf-8'))

            for window_data in state.get("windows", {}).values():
                window = ToolResultWindow(
                    id=window_data["id"],
                    window_type=window_data["window_type"],
                    content=window_data["content"],
                    metadata=window_data.get("metadata", {}),
                    opened_at=window_data.get("opened_at", 0.0),
                    file_path=window_data.get("file_path", ""),
                    start_line=window_data.get("start_line", 0),
                    end_line=window_data.get("end_line", 0),
                    command=window_data.get("command", ""),
                    exit_code=window_data.get("exit_code", 0),
                    pattern=window_data.get("pattern", ""),
                    glob_pattern=window_data.get("glob_pattern", "")
                )
                self.windows[window.id] = window

            logger.info(f"Restored {len(self.windows)} tool result windows from state file")
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}")

    def create_read_window(self, file_path: str, start_line: int = None, end_line: int = None) -> str:
        """Create window for file read result."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if start_line is not None and end_line is not None:
                # Slice specific range
                content = [line.rstrip('\n') for line in lines[start_line-1:end_line]]
                actual_start = start_line
                actual_end = end_line
            else:
                # Full file
                content = [line.rstrip('\n') for line in lines]
                actual_start = 1
                actual_end = len(lines)

            window = ToolResultWindow(
                window_type="read_result",
                content=content,
                file_path=file_path,
                start_line=actual_start,
                end_line=actual_end,
                metadata={'total_lines': len(content)}
            )

            self.windows[window.id] = window
            self.save_state()
            return window.id
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            # Create error window
            window = ToolResultWindow(
                window_type="read_result",
                content=[f"<error reading file: {e}>"],
                file_path=file_path,
                metadata={'error': str(e)}
            )
            self.windows[window.id] = window
            self.save_state()
            return window.id

    def create_bash_window(self, command: str, cwd: str = None) -> str:
        """Create window for bash command result."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=120
            )

            # Merge stdout and stderr
            output = result.stdout + result.stderr
            content = output.splitlines()

            window = ToolResultWindow(
                window_type="bash_result",
                content=content,
                command=command,
                exit_code=result.returncode,
                metadata={
                    'total_lines': len(content),
                    'cwd': cwd or str(Path.cwd())
                }
            )

            self.windows[window.id] = window
            self.save_state()
            return window.id
        except subprocess.TimeoutExpired:
            window = ToolResultWindow(
                window_type="bash_result",
                content=["<command timed out after 120s>"],
                command=command,
                exit_code=-1,
                metadata={'error': 'timeout'}
            )
            self.windows[window.id] = window
            self.save_state()
            return window.id
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            window = ToolResultWindow(
                window_type="bash_result",
                content=[f"<error executing command: {e}>"],
                command=command,
                exit_code=-1,
                metadata={'error': str(e)}
            )
            self.windows[window.id] = window
            self.save_state()
            return window.id

    def create_grep_window(self, pattern: str, path: str = ".", **kwargs) -> str:
        """Create window for grep result."""
        # Build grep command from kwargs
        grep_args = []
        if kwargs.get('i'):
            grep_args.append('-i')
        if kwargs.get('n'):
            grep_args.append('-n')
        if kwargs.get('A'):
            grep_args.append(f"-A {kwargs['A']}")
        if kwargs.get('B'):
            grep_args.append(f"-B {kwargs['B']}")
        if kwargs.get('C'):
            grep_args.append(f"-C {kwargs['C']}")

        # Use ripgrep if available, fallback to grep
        command = f"rg {' '.join(grep_args)} -e '{pattern}' {path} 2>/dev/null || grep -r {' '.join(grep_args)} -e '{pattern}' {path}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )

            content = result.stdout.splitlines()

            window = ToolResultWindow(
                window_type="grep_result",
                content=content,
                pattern=pattern,
                metadata={
                    'total_lines': len(content),
                    'path': path,
                    'args': kwargs
                }
            )

            self.windows[window.id] = window
            self.save_state()
            return window.id
        except Exception as e:
            logger.error(f"Failed to grep: {e}")
            window = ToolResultWindow(
                window_type="grep_result",
                content=[f"<error: {e}>"],
                pattern=pattern,
                metadata={'error': str(e)}
            )
            self.windows[window.id] = window
            self.save_state()
            return window.id

    def create_glob_window(self, pattern: str, path: str = ".") -> str:
        """Create window for glob result."""
        from glob import glob

        try:
            matches = glob(f"{path}/{pattern}", recursive=True)
            content = sorted(matches)

            window = ToolResultWindow(
                window_type="glob_result",
                content=content,
                glob_pattern=pattern,
                metadata={
                    'total_lines': len(content),
                    'path': path
                }
            )

            self.windows[window.id] = window
            self.save_state()
            return window.id
        except Exception as e:
            logger.error(f"Failed to glob: {e}")
            window = ToolResultWindow(
                window_type="glob_result",
                content=[f"<error: {e}>"],
                glob_pattern=pattern,
                metadata={'error': str(e)}
            )
            self.windows[window.id] = window
            self.save_state()
            return window.id

    def close_window(self, window_id: str) -> None:
        """Remove window."""
        if window_id in self.windows:
            del self.windows[window_id]
            self.save_state()

    def clear_all(self) -> None:
        """Remove all windows."""
        self.windows.clear()
        self.save_state()

    def render(self) -> str:
        """Render all windows to markdown."""
        if not self.windows:
            return ""

        lines = []

        for window_id, window in self.windows.items():
            # Window header
            lines.append(f"---TOOL_RESULT_WINDOW_{window_id}")
            lines.append(f"**type**: {window.window_type}")

            # Type-specific metadata
            if window.window_type == "read_result":
                lines.append(f"**file**: {window.file_path}")
                lines.append(f"**lines**: {window.start_line}-{window.end_line}")
            elif window.window_type == "bash_result":
                lines.append(f"**command**: {window.command}")
                lines.append(f"**exit_code**: {window.exit_code}")
            elif window.window_type == "grep_result":
                lines.append(f"**pattern**: {window.pattern}")
            elif window.window_type == "glob_result":
                lines.append(f"**pattern**: {window.glob_pattern}")

            # Additional metadata
            for key, value in window.metadata.items():
                if key not in ['total_lines', 'error']:
                    lines.append(f"**{key}**: {value}")

            total_lines = len(window.content)
            lines.append(f"**total_lines**: {total_lines}")
            lines.append("")

            # Content with truncation
            if total_lines > self.max_render_lines:
                # Show first half + last half
                half = self.max_render_lines // 2
                displayed = window.content[:half] + [f"... ({total_lines - self.max_render_lines} lines omitted) ..."] + window.content[-half:]
                lines.append(f"**truncated**: showing {self.max_render_lines} of {total_lines} lines")
                lines.append("")
            else:
                displayed = window.content

            # Render content
            if window.window_type == "read_result" and window.start_line > 0:
                # Line numbers for file reads
                for i, line in enumerate(displayed):
                    line_num = window.start_line + i
                    lines.append(f"{line_num}: {line}")
            else:
                # Plain output for commands
                lines.extend(displayed)

            lines.append(f"---TOOL_RESULT_WINDOW_{window_id}_END")
            lines.append("")

        return '\n'.join(lines)

    def total_lines(self) -> int:
        """Sum of all window line counts."""
        return sum(len(w.content) for w in self.windows.values())

    def get_state_summary(self) -> Dict:
        """Get current state for tool responses."""
        return {
            'window_count': len(self.windows),
            'total_lines': self.total_lines(),
            'windows': [
                {
                    'id': w.id,
                    'type': w.window_type,
                    'lines': len(w.content),
                    'metadata': w.metadata
                }
                for w in self.windows.values()
            ]
        }
