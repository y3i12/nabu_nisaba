"""Editor manager - unified file editing with persistent windows."""

import json
import logging
import difflib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from nisaba.tui.editor_window import EditorWindow, Edit
from nisaba.structured_file import JsonStructuredFile

logger = logging.getLogger(__name__)


class EditorManager:
    """
    Manages collection of editor windows.
    
    Key features:
    - One editor per file (no duplicates)
    - Immediate commit to disk
    - Change tracking with edit history
    - Diff rendering with inline markers
    """
    
    def __init__(self):
        self.editors: Dict[Path, EditorWindow] = {}  # file_path → editor
        state_file = Path.cwd() / '.nisaba' / 'tui' / 'editor_tui.json'
        self.output_file = Path.cwd() / '.nisaba' / 'tui' / 'editor_view.md'
        
        # Use JsonStructuredFile for atomic state persistence
        self._state_file = JsonStructuredFile(
            file_path=state_file,
            name="editor_state",
            default_factory=lambda: {"editors": {}}
        )
        
        self.load_state()
    
    def open(self, file: str, line_start: int = 1, line_end: int = -1) -> str:
        """
        Open file in editor. Returns existing editor_id if already open.
        
        Args:
            file: File path
            line_start: Start line (1-indexed)
            line_end: End line (-1 = end of file, inclusive)
        
        Returns:
            editor_id
        """
        file_path = Path(file).resolve()
        
        # Return existing editor if already open
        if file_path in self.editors:
            logger.info(f"File already open: {file_path}")
            return self.editors[file_path].id
        
        # Read file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # Strip newlines
            all_lines = [line.rstrip('\n') for line in all_lines]
            
            # Handle line range
            if line_end == -1:
                content = all_lines[line_start-1:] if line_start > 1 else all_lines
                actual_end = len(all_lines)
            else:
                content = all_lines[line_start-1:line_end]
                actual_end = line_end
            
            # Get file mtime
            mtime = file_path.stat().st_mtime
            
            # Create editor
            editor = EditorWindow(
                file_path=file_path,
                line_start=line_start,
                line_end=actual_end,
                content=content,
                original_content=content.copy(),
                edits=[],
                last_mtime=mtime
            )
            
            self.editors[file_path] = editor
            self.save_state()
            
            logger.info(f"Opened editor: {file_path} ({len(content)} lines)")
            return editor.id
            
        except Exception as e:
            logger.error(f"Failed to open {file_path}: {e}", exc_info=True)
            raise
    
    def write(self, file: str, content: str) -> str:
        """
        Write content to file and open editor.
        
        Args:
            file: File path
            content: File content
        
        Returns:
            editor_id
        """
        file_path = Path(file).resolve()
        
        try:
            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to disk
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"Wrote file: {file_path}")
            
            # Open editor (will create new or return existing)
            editor_id = self.open(str(file_path))
            self._add_notification(f"✓ editor.write() → created {file_path.name}")
            return editor_id
            
        except Exception as e:
            logger.error(f"Failed to write {file_path}: {e}", exc_info=True)
            raise
    
    def replace(self, editor_id: str, old: str, new: str) -> bool:
        """
        Replace string in editor content and write to disk.
        
        Args:
            editor_id: Editor window ID
            old: String to replace
            new: Replacement string
        
        Returns:
            True if successful
        """
        editor = self._get_editor_by_id(editor_id)
        if not editor:
            raise ValueError(f"Editor not found: {editor_id}")
        
        # Check if string exists
        full_content = '\n'.join(editor.content)
        if old not in full_content:
            raise ValueError(f"String not found in editor: {old[:50]}...")
        
        # Apply replacement
        old_content_lines = editor.content.copy()
        new_content_lines = [line.replace(old, new) for line in editor.content]
        
        # Track edit
        edit = Edit(
            timestamp=time.time(),
            operation='replace',
            target=old,
            old_content='\n'.join(old_content_lines),
            new_content='\n'.join(new_content_lines)
        )
        
        editor.edits.append(edit)
        editor.content = new_content_lines
        
        # Write to disk immediately
        self._write_to_disk(editor)
        self.save_state()
        
        self._add_notification(f"✓ editor.replace() → {editor.file_path.name} (string replaced)")
        logger.info(f"Replaced in {editor.file_path}: {old[:30]}... → {new[:30]}...")
        return True
    
    def insert(self, editor_id: str, before_line: int, content: str) -> bool:
        """
        Insert content before specified line.
        
        Args:
            editor_id: Editor window ID
            before_line: Line number to insert before (1-indexed, relative to editor view)
            content: Content to insert (can be multi-line string)
        
        Returns:
            True if successful
        """
        editor = self._get_editor_by_id(editor_id)
        if not editor:
            raise ValueError(f"Editor not found: {editor_id}")
        
        # Validate line number
        if before_line < editor.line_start or before_line > editor.line_end + 1:
            raise ValueError(f"Line {before_line} out of range ({editor.line_start}-{editor.line_end})")
        
        # Convert to array index
        insert_idx = before_line - editor.line_start
        
        # Store old content
        old_content_lines = editor.content.copy()
        
        # Split content into lines and insert
        insert_lines = content.split('\n')
        editor.content[insert_idx:insert_idx] = insert_lines
        
        # Update line_end to reflect new content
        editor.line_end += len(insert_lines)
        
        # Track edit
        edit = Edit(
            timestamp=time.time(),
            operation='insert',
            target=f"before line {before_line}",
            old_content='\n'.join(old_content_lines),
            new_content='\n'.join(editor.content)
        )
        editor.edits.append(edit)
        
        # Write to disk and save state
        self._write_to_disk(editor)
        self.save_state()
        
        self._add_notification(f"✓ editor.insert() → {editor.file_path.name} ({len(insert_lines)} lines inserted)")
        logger.info(f"Inserted {len(insert_lines)} lines before line {before_line} in {editor.file_path}")
        return True
    
    def delete(self, editor_id: str, line_start: int, line_end: int) -> bool:
        """
        Delete line range.
        
        Args:
            editor_id: Editor window ID
            line_start: Start line (1-indexed, relative to editor view)
            line_end: End line (inclusive)
        
        Returns:
            True if successful
        """
        editor = self._get_editor_by_id(editor_id)
        if not editor:
            raise ValueError(f"Editor not found: {editor_id}")
        
        # Validate line numbers
        if line_start < editor.line_start or line_end > editor.line_end:
            raise ValueError(f"Lines {line_start}-{line_end} out of range ({editor.line_start}-{editor.line_end})")
        if line_start > line_end:
            raise ValueError(f"Invalid range: {line_start} > {line_end}")
        
        # Convert to array indices
        start_idx = line_start - editor.line_start
        end_idx = line_end - editor.line_start + 1  # +1 because end is inclusive
        
        # Store old content
        old_content_lines = editor.content.copy()
        
        # Delete lines
        lines_deleted = end_idx - start_idx
        del editor.content[start_idx:end_idx]
        
        # Update line_end to reflect deletion
        editor.line_end -= lines_deleted
        
        # Track edit
        edit = Edit(
            timestamp=time.time(),
            operation='delete',
            target=f"lines {line_start}-{line_end}",
            old_content='\n'.join(old_content_lines),
            new_content='\n'.join(editor.content)
        )
        editor.edits.append(edit)
        
        # Write to disk and save state
        self._write_to_disk(editor)
        self.save_state()
        
        self._add_notification(f"✓ editor.delete() → {editor.file_path.name} ({lines_deleted} lines deleted)")
        logger.info(f"Deleted lines {line_start}-{line_end} from {editor.file_path}")
        return True
    
    def replace_lines(self, editor_id: str, line_start: int, line_end: int, content: str) -> bool:
        """
        Replace line range with new content.
        
        Args:
            editor_id: Editor window ID
            line_start: Start line (1-indexed, relative to editor view)
            line_end: End line (inclusive)
            content: New content (can be multi-line string)
        
        Returns:
            True if successful
        """
        editor = self._get_editor_by_id(editor_id)
        if not editor:
            raise ValueError(f"Editor not found: {editor_id}")
        
        # Validate line numbers
        if line_start < editor.line_start or line_end > editor.line_end:
            raise ValueError(f"Lines {line_start}-{line_end} out of range ({editor.line_start}-{editor.line_end})")
        if line_start > line_end:
            raise ValueError(f"Invalid range: {line_start} > {line_end}")
        
        # Convert to array indices
        start_idx = line_start - editor.line_start
        end_idx = line_end - editor.line_start + 1  # +1 because end is inclusive
        
        # Store old content
        old_content_lines = editor.content.copy()
        
        # Split new content and replace
        new_lines = content.split('\n')
        lines_removed = end_idx - start_idx
        editor.content[start_idx:end_idx] = new_lines
        
        # Update line_end to reflect change
        editor.line_end = editor.line_end - lines_removed + len(new_lines)
        
        # Track edit
        edit = Edit(
            timestamp=time.time(),
            operation='replace_lines',
            target=f"lines {line_start}-{line_end}",
            old_content='\n'.join(old_content_lines),
            new_content='\n'.join(editor.content)
        )
        editor.edits.append(edit)
        
        # Write to disk and save state
        self._write_to_disk(editor)
        self.save_state()
        
        self._add_notification(f"✓ editor.replace_lines() → {editor.file_path.name} ({len(new_lines)} lines replaced)")
        logger.info(f"Replaced lines {line_start}-{line_end} in {editor.file_path}")
        return True
    
    def split(self, editor_id: str, line_start: int, line_end: int) -> str:
        """
        Create split view of editor.
        
        Args:
            editor_id: Parent editor window ID
            line_start: Start line for split (1-indexed, relative to editor view)
            line_end: End line for split (inclusive)
        
        Returns:
            split_id
        """
        editor = self._get_editor_by_id(editor_id)
        if not editor:
            raise ValueError(f"Editor not found: {editor_id}")
        
        # Validate line numbers
        if line_start < editor.line_start or line_end > editor.line_end:
            raise ValueError(f"Lines {line_start}-{line_end} out of range ({editor.line_start}-{editor.line_end})")
        if line_start > line_end:
            raise ValueError(f"Invalid range: {line_start} > {line_end}")
        
        # Import Split from editor_window
        from nisaba.tui.editor_window import Split
        
        # Create split
        split = Split(
            parent_id=editor.id,
            line_start=line_start,
            line_end=line_end
        )
        
        editor.splits[split.id] = split
        self.save_state()
        
        logger.info(f"Created split {split.id} for {editor.file_path} lines {line_start}-{line_end}")
        return split.id
    
    def resize(self, window_id: str, line_start: int, line_end: int) -> bool:
        """
        Resize editor or split window.
        
        Args:
            window_id: Editor ID or split ID
            line_start: New start line
            line_end: New end line
        
        Returns:
            True if successful
        """
        # Try editor first
        editor = self._get_editor_by_id(window_id)
        if editor:
            # Resizing editor
            if line_start < 1:
                raise ValueError(f"Invalid line_start: {line_start}")
            
            editor.line_start = line_start
            editor.line_end = line_end
            self.save_state()
            logger.info(f"Resized editor {window_id} to lines {line_start}-{line_end}")
            return True
        
        # Try split
        for editor in self.editors.values():
            if window_id in editor.splits:
                split = editor.splits[window_id]
                
                # Validate against editor bounds
                if line_start < editor.line_start or line_end > editor.line_end:
                    raise ValueError(f"Lines {line_start}-{line_end} out of range ({editor.line_start}-{editor.line_end})")
                
                split.line_start = line_start
                split.line_end = line_end
                self.save_state()
                logger.info(f"Resized split {window_id} to lines {line_start}-{line_end}")
                return True
        
        raise ValueError(f"Window not found: {window_id}")
    
    def close_split(self, split_id: str) -> bool:
        """
        Close split view.
        
        Args:
            split_id: Split ID
        
        Returns:
            True if successful
        """
        for editor in self.editors.values():
            if split_id in editor.splits:
                del editor.splits[split_id]
                self.save_state()
                logger.info(f"Closed split {split_id}")
                return True
        
        return False
    
    def refresh_all(self) -> List[str]:
        """
        Check for external file changes and reload if needed.
        
        Returns:
            List of notification messages
        """
        notifications = []
        
        for editor in self.editors.values():
            if not editor.file_path.exists():
                notifications.append(f"⚠ File deleted: {editor.file_path}")
                continue
            
            current_mtime = editor.file_path.stat().st_mtime
            
            if current_mtime != editor.last_mtime:
                # File changed externally
                if editor.is_dirty:
                    # Conflict: dirty editor + external change
                    notifications.append(f"⚠ Conflict: {editor.file_path} modified externally with unsaved edits")
                else:
                    # Clean reload
                    try:
                        content = editor.file_path.read_text().splitlines()
                        # Adjust to current view range
                        if editor.line_end == -1 or editor.line_end > len(content):
                            editor.line_end = len(content)
                        
                        editor.content = content[editor.line_start-1:editor.line_end]
                        editor.original_content = editor.content.copy()
                        editor.last_mtime = current_mtime
                        self.save_state()
                        
                        notifications.append(f"🔄 Reloaded: {editor.file_path}")
                    except Exception as e:
                        notifications.append(f"✗ Failed to reload {editor.file_path}: {e}")
        
        return notifications
    
    def _add_notification(self, message: str) -> None:
        """
        Add notification to notifications file.
        
        Args:
            message: Notification message
        """
        notifications_file = Path(".nisaba/tui/notification_view.md")
        
        # Read existing notifications
        if notifications_file.exists():
            content = notifications_file.read_text()
            lines = content.splitlines()
            
            # Keep only "Recent activity:" header and existing notifications
            if lines and lines[0] == "Recent activity:":
                existing = lines[1:]
            else:
                existing = []
        else:
            existing = []
        
        # Add new notification at top
        new_notifications = [message] + existing
        
        # Keep last 10 notifications
        new_notifications = new_notifications[:10]
        
        # Write back
        content = "Recent activity:\\n" + "\\n".join(new_notifications) + "\\n"
        notifications_file.write_text(content)
    
    def close(self, editor_id: str) -> bool:
        """
        Close editor window.
        
        Args:
            editor_id: Editor window ID
        
        Returns:
            True if successful
        """
        editor = self._get_editor_by_id(editor_id)
        if not editor:
            return False
        
        del self.editors[editor.file_path]
        self.save_state()
        
        logger.info(f"Closed editor: {editor.file_path}")
        return True
    
    def close_all(self) -> None:
        """Close all editor windows."""
        self.editors.clear()
        self.save_state()
        logger.info("Closed all editors")
    
    def status(self) -> Dict[str, Any]:
        """
        Get status summary.
        
        Returns:
            Dict with editor count, total lines, and editor list
        """
        total_lines = sum(len(editor.content) for editor in self.editors.values())
        
        return {
            "editor_count": len(self.editors),
            "total_lines": total_lines,
            "editors": [
                {
                    "id": editor.id,
                    "file": str(editor.file_path),
                    "lines": f"{editor.line_start}-{editor.line_end}",
                    "line_count": len(editor.content),
                    "edits": len(editor.edits),
                    "dirty": editor.is_dirty
                }
                for editor in self.editors.values()
            ]
        }
    
    def render(self) -> str:
        """
        Render all editors and splits to markdown with diff markers.
        
        Returns:
            Markdown string
        """
        # Check for external changes first
        refresh_notifications = self.refresh_all()
        for notif in refresh_notifications:
            self._add_notification(notif)
        
        if not self.editors:
            return ""
        
        lines = []
        
        for editor in self.editors.values():
            # Render main editor
            lines.append(f"---EDITOR_{editor.id}")
            lines.append(f"**file**: {editor.file_path}")
            lines.append(f"**lines**: {editor.line_start}-{editor.line_end} ({len(editor.content)} lines)")
            
            if editor.splits:
                lines.append(f"**splits**: {len(editor.splits)}")
            
            if editor.is_dirty:
                lines.append(f"**status**: modified ✎")
                lines.append(f"**edits**: {len(editor.edits)}")
            
            lines.append("")
            
            # Always render clean content with line numbers
            for i, line in enumerate(editor.content):
                line_num = editor.line_start + i
                lines.append(f"{line_num}: {line}")
            
            # If dirty, add change history section at bottom
            if editor.is_dirty:
                lines.append("")
                lines.append("---")
                lines.append("**recent changes:**")
                history_lines = self._format_edit_history(editor)
                lines.extend(history_lines)
            # Render splits
            for split in editor.splits.values():
                lines.append(f"---EDITOR_SPLIT_{split.id}")
                lines.append(f"**parent**: {split.parent_id}")
                lines.append(f"**file**: {editor.file_path}")
                lines.append(f"**lines**: {split.line_start}-{split.line_end}")
                lines.append("")
                
                # Get content slice from editor
                start_idx = split.line_start - editor.line_start
                end_idx = split.line_end - editor.line_start + 1
                split_content = editor.content[start_idx:end_idx]
                
                for i, line in enumerate(split_content):
                    line_num = split.line_start + i
                    lines.append(f"{line_num}: {line}")
                
                lines.append(f"---EDITOR_SPLIT_{split.id}_END")
                lines.append("")
        
        return '\n'.join(lines)
    
    def save_state(self) -> None:
        """Save editor state to JSON using atomic file operations."""
        state = {
            "editors": {
                str(file_path): editor.to_dict()
                for file_path, editor in self.editors.items()
            }
        }
        
        # Use JsonStructuredFile for atomic write with locking
        self._state_file.write_json(state)
        logger.debug(f"Saved {len(self.editors)} editors to state file")
    
    def load_state(self) -> None:
        """Restore editors from JSON using cached file operations."""
        state = self._state_file.load_json()
        
        for file_path_str, editor_data in state.get("editors", {}).items():
            file_path = Path(file_path_str)
            # Re-read content from file (handles external changes)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                
                all_lines = [line.rstrip('\n') for line in all_lines]
                
                # Extract range
                start = editor_data["line_start"]
                end = editor_data["line_end"]
                
                if end == -1 or end > len(all_lines):
                    content = all_lines[start-1:]
                else:
                    content = all_lines[start-1:end]
                
                # Restore editor
                editor = EditorWindow.from_dict(editor_data, content)
                self.editors[file_path] = editor
                
            except Exception as e:
                logger.warning(f"Skipping editor {file_path}: {e}")
    
    def _get_editor_by_id(self, editor_id: str) -> Optional[EditorWindow]:
        """Find editor by ID."""
        for editor in self.editors.values():
            if editor.id == editor_id:
                return editor
        return None
    
    def _write_to_disk(self, editor: EditorWindow) -> None:
        """Write editor content back to file."""
        try:
            # Read full file
            with open(editor.file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            all_lines = [line.rstrip('\n') for line in all_lines]
            
            # Replace the range
            start_idx = editor.line_start - 1
            end_idx = editor.line_end
            
            new_lines = (
                all_lines[:start_idx] +
                editor.content +
                all_lines[end_idx:]
            )
            
            # Write back
            editor.file_path.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
            
            # Update mtime
            editor.last_mtime = editor.file_path.stat().st_mtime
            
        except Exception as e:
            logger.error(f"Failed to write {editor.file_path}: {e}", exc_info=True)
            raise
    
    def _generate_inline_diff(self, editor: EditorWindow) -> List[str]:
        """Generate diff with +/- markers inline."""
        diff = difflib.ndiff(editor.original_content, editor.content)
        
        lines = []
        line_num = editor.line_start
        
        for d in diff:
            prefix = d[0]
            content = d[2:]
            
            if prefix == ' ':  # Unchanged
                lines.append(f"{line_num}: {content}")
                line_num += 1
            elif prefix == '-':  # Removed
                lines.append(f"{line_num}: -{content}")
            elif prefix == '+':  # Added
                lines.append(f"{line_num}: +{content}")
                line_num += 1
        
        return lines
    
    def _format_edit_history(self, editor: EditorWindow) -> List[str]:
        """
        Format edit history as readable change summary.
        
        Returns list of formatted lines showing recent edits with mini-diffs.
        """
        lines = []
        
        # Show last N edits (e.g., last 5)
        recent_edits = editor.edits[-3:] if len(editor.edits) > 3 else editor.edits
        
        for edit in recent_edits:
            # Format: "  Line 2: replaced"
            lines.append(f"  {edit.target}: {edit.operation}")
            
            # Show mini-diff for the change
            old_lines = edit.old_content.split('\n')
            new_lines = edit.new_content.split('\n')
            
            # Limit diff to first few lines if large
            max_diff_lines = 10
            if len(old_lines) > max_diff_lines or len(new_lines) > max_diff_lines:
                lines.append(f"    (Large change: {len(old_lines)} → {len(new_lines)} lines)")
            else:
                # Generate compact diff
                diff = difflib.ndiff(old_lines, new_lines)
                diff_lines = [d.rstrip() for d in diff]
                
                # Indent and add to output
                for d in diff_lines[:max_diff_lines]:
                    lines.append(f"    {d}")
            
            lines.append("")  # Blank line between edits
        
        return lines
