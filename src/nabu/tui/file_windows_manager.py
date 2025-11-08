"""File windows manager - persistent code visibility."""

import logging
from typing import Dict, List, Optional
from pathlib import Path

from nabu.tui.file_window import FileWindow
from nabu.db.kuzu_manager import KuzuConnectionManager
from nisaba.structured_file import JsonStructuredFile

logger = logging.getLogger(__name__)


class FileWindowsManager:
    """Manages collection of open file windows."""

    def __init__(self, db_manager: KuzuConnectionManager, factory):
        self.windows: Dict[str, FileWindow] = {}
        self.db_manager = db_manager
        self.factory = factory
        self.load_state()
        
        # Use JsonStructuredFile for atomic state persistence
        self._state_file = JsonStructuredFile(
            file_path=self.state_file,
            name="file_windows_state",
            default_factory=lambda: {"windows": {}}
        )


    @property
    def state_file(self) -> Path:
        """Path to state persistence file."""
        return Path.cwd() / '.nisaba' / 'tui' / 'file_window_state.json'

    def save_state(self) -> None:
        """Save windows state to JSON using atomic operations."""
        state = {
            "windows": {
                wid: {
                    "id": w.id,
                    "file_path": str(w.file_path),
                    "start_line": w.start_line,
                    "end_line": w.end_line,
                    "window_type": w.window_type,
                    "metadata": w.metadata,
                    "opened_at": w.opened_at
                }
                for wid, w in self.windows.items()
            }
        }
        
        # Use JsonStructuredFile for atomic write with locking
        self._state_file.write_json(state)
        logger.debug(f"Saved {len(self.windows)} windows to state file")

    def load_state(self) -> None:
        """Restore windows from JSON using cached operations."""
        state = self._state_file.load_json()
        
        for window_data in state.get("windows", {}).values():
            try:
                # Re-read content from file (handles staleness)
                content = self._read_lines(
                    window_data["file_path"],
                    window_data["start_line"],
                    window_data["end_line"]
                )
                
                # Reconstruct window
                window = FileWindow(
                    id=window_data["id"],
                    file_path=Path(window_data["file_path"]),
                    start_line=window_data["start_line"],
                    end_line=window_data["end_line"],
                    content=content,
                    window_type=window_data["window_type"],
                    metadata=window_data.get("metadata", {}),
                    opened_at=window_data.get("opened_at", 0.0)
                )
                self.windows[window.id] = window
            except Exception as e:
                logger.warning(f"Skipping window {window_data.get('id')}: {e}")
                continue
        
        logger.info(f"Restored {len(self.windows)} windows from state file")

    def open_frame_window(self, frame_path: str) -> str:
        content = self._read_lines(
            frame_data['file_path'],
            frame_data['start_line'],
            
            logger.info(f"Restored {len(self.windows)} windows from state file")
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}")

    def open_frame_window(self, frame_path: str) -> str:
        content = self._read_lines(
            frame_data['file_path'],
            frame_data['start_line'],
            frame_data['end_line']
        )

        # Create window
        window = FileWindow(
            file_path=Path(frame_data['file_path']),
            start_line=frame_data['start_line'],
            end_line=frame_data['end_line'],
            content=content,
            window_type="frame_body",
            metadata={'frame_qn': frame_data['qualified_name']}
        )

        self.windows[window.id] = window
        self.save_state()
        return window.id

    def open_range_window(self, file_path: str, start: int, end: int) -> str:
        """Open specific line range."""
        content = self._read_lines(file_path, start, end)

        window = FileWindow(
            file_path=Path(file_path),
            start_line=start,
            end_line=end,
            content=content,
            window_type="range"
        )

        self.windows[window.id] = window
        self.save_state()
        return window.id

    async def open_search_windows(
        self,
        query: str,
        max_windows: int = 5,
        context_lines: int = 3
    ) -> List[str]:
        """Open top N search results with context."""
        # Use SearchTool backend
        from nabu.mcp.tools.search_tools import SearchTool
        search_tool = SearchTool(factory=self.factory)

        result = await search_tool.execute(
            query=query,
            k=max_windows,
            frame_type_filter="CALLABLE|CLASS|PACKAGE",
            compact_metadata=False,
            context_lines=context_lines,
            max_snippets=1
        )

        if not result.get('success'):
            return []

        results = result.get('data', {}).get('results', [])
        window_ids = []

        for res in results[:max_windows]:
            # Extract snippet with context
            snippets = res.get('snippets', [])
            if snippets:
                snippet = snippets[0]
                start = snippet['line_start']
                end = snippet['line_end']
            else:
                start = res['start_line']
                end = res['end_line']

            content = self._read_lines(res['file_path'], start, end)

            window = FileWindow(
                file_path=Path(res['file_path']),
                start_line=start,
                end_line=end,
                content=content,
                window_type="search_result",
                metadata={
                    'query': query,
                    'search_score': res.get('rrf_score', 0.0),
                    'qualified_name': res.get('qualified_name', '')
                }
            )

            self.windows[window.id] = window
            window_ids.append(window.id)

        self.save_state()
        return window_ids

    def update_window(self, window_id: str, start: int, end: int) -> None:
        """Update window line range (re-snapshot)."""
        if window_id not in self.windows:
            raise ValueError(f"Window not found: {window_id}")

        window = self.windows[window_id]
        content = self._read_lines(str(window.file_path), start, end)

        window.start_line = start
        window.end_line = end
        window.content = content
        self.save_state()

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
            lines.append(f"---FILE_WINDOW_{window_id}")
            lines.append(f"**file**: {window.file_path}")
            lines.append(f"**lines**: {window.start_line}-{window.end_line} ({len(window.content)} lines)")
            lines.append(f"**type**: {window.window_type}")

            # Metadata
            for key, value in window.metadata.items():
                lines.append(f"**{key}**: {value}")

            lines.append("")

            # Content with line numbers
            for i, line in enumerate(window.content):
                line_num = window.start_line + i
                lines.append(f"{line_num}: {line}")

            lines.append(f"---FILE_WINDOW_{window_id}_END")
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
                    'file': str(w.file_path),
                    'lines': f"{w.start_line}-{w.end_line}",
                    'type': w.window_type
                }
                for w in self.windows.values()
            ]
        }

    def _get_frame_location(self, frame_path: str) -> Optional[Dict]:
        """Query kuzu for frame location."""
        query = """
        MATCH (f:Frame)
        WHERE f.qualified_name = $qname
           OR f.name = $name
        RETURN f.qualified_name AS qualified_name,
               f.file_path AS file_path,
               f.start_line AS start_line,
               f.end_line AS end_line
        LIMIT 1
        """

        result = self.db_manager.execute(query, {
            'qname': frame_path,
            'name': frame_path
        })

        if not result or not hasattr(result, 'get_as_df'):
            return None

        df = result.get_as_df()
        if df.empty:
            return None

        row = df.iloc[0]
        return {
            'qualified_name': row['qualified_name'],
            'file_path': row['file_path'],
            'start_line': int(row['start_line']),
            'end_line': int(row['end_line'])
        }

    def _read_lines(self, file_path: str, start: int, end: int) -> List[str]:
        """Read lines from file (1-indexed, inclusive)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                # Convert to 0-indexed
                return [line.rstrip('\n') for line in all_lines[start-1:end]]
        except Exception as e:
            logger.error(f"Failed to read {file_path}:{start}-{end}: {e}")
            return [f"<error reading file: {e}>"]
