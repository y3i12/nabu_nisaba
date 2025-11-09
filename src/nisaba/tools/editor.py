"""Editor tool - unified file editing with persistent windows."""

from typing import Dict, Any, Optional
from pathlib import Path
from nisaba.tools.base import NisabaTool


class EditorTool(NisabaTool):
    """
    Unified file editor with persistent windows and change tracking.
    
    Replaces nisaba_read, nisaba_write, nisaba_edit with single coherent interface.
    """
    
    def __init__(self, factory):
        super().__init__(factory)
        self._manager = None
    
    @property
    def manager(self):
        """Lazy-initialize editor manager (persists across operations)."""
        if self._manager is None:
            from nisaba.tui.editor_manager import get_editor_manager
            self._manager = get_editor_manager()  # Use singleton
        return self._manager
    
    async def execute(
        self,
        operation: str,
        file: Optional[str] = None,
        content: Optional[str] = None,
        editor_id: Optional[str] = None,
        old: Optional[str] = None,
        new: Optional[str] = None,
        line_start: Optional[int] = 1,
        line_end: Optional[int] = -1,
        before_line: Optional[int] = None,
        split_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute editor operation.
        
        Operations:
        - open: Open file in editor (returns existing if already open)
        - write: Write content to file and open editor
        - replace: Replace string in editor content
        - insert: Insert content before specified line
        - delete: Delete line range
        - replace_lines: Replace line range with new content
        - split: Create split view of editor
        - resize: Resize editor or split window
        - close_split: Close split view
        - close: Close editor window (and all splits)
        - close_all: Close all editor windows
        - status: Get editor status summary
        
        :meta pitch: Unified file editing with workspace persistence
        :meta when: Reading, writing, or editing files
        Args:
            operation: Operation type
            file: File path (for open, write)
            content: File content (for write)
            editor_id: Editor window ID (for replace, insert, delete, replace_lines, split, close)
            old: String to replace (for replace)
            new: Replacement string (for replace)
            line_start: Start line for open/delete/replace_lines/split/resize (1-indexed, default 1)
            line_end: End line for open/delete/replace_lines/split/resize (-1 = end of file, default -1)
            before_line: Line to insert before (for insert)
            split_id: Split ID (for close_split, resize)
            before_line: Line to insert before (for insert)
            split_id: Split ID (for close_split, resize)
        
        Returns:
            Dict with success status and operation result
        """
        valid_ops = ['open', 'write', 'replace', 'insert', 'delete', 'replace_lines', 'split', 'resize', 'close_split', 'close', 'close_all', 'status']
        
        if operation not in valid_ops:
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Valid: {valid_ops}",
                "error_type": "ValueError",
                "nisaba": True
            }
        
        try:
            if operation == 'open':
                if not file:
                    return self._error("'file' parameter required for open")
                
                editor_id = self.manager.open(file, line_start, line_end)
                message = f"Opened editor: {file}"
                result = {"editor_id": editor_id}
            
            elif operation == 'write':
                if not file or content is None:
                    return self._error("'file' and 'content' parameters required for write")
                
                editor_id = self.manager.write(file, content)
                message = f"Wrote file: {file}"
            elif operation == 'replace':
                if not editor_id or not old or new is None:
                    return self._error("'editor_id', 'old', 'new' required for replace")
                
                self.manager.replace(editor_id, old, new)
                message = f"Replaced in editor: {old[:30]}... → {new[:30]}..."
                result = {}
            
            elif operation == 'insert':
                if not editor_id or before_line is None or content is None:
                    return self._error("'editor_id', 'before_line', 'content' required for insert")
                
                self.manager.insert(editor_id, before_line, content)
                num_lines = len(content.split('\n'))
                message = f"Inserted {num_lines} line(s) before line {before_line}"
                result = {}
            
            elif operation == 'delete':
                if not editor_id or line_start is None or line_end is None:
                    return self._error("'editor_id', 'line_start', 'line_end' required for delete")
                
                self.manager.delete(editor_id, line_start, line_end)
                message = f"Deleted lines {line_start}-{line_end}"
                result = {}
            
            elif operation == 'replace_lines':
                if not editor_id or line_start is None or line_end is None or content is None:
                    return self._error("'editor_id', 'line_start', 'line_end', 'content' required for replace_lines")
                
                self.manager.replace_lines(editor_id, line_start, line_end, content)
                num_lines = len(content.split('\n'))
                message = f"Replaced lines {line_start}-{line_end} with {num_lines} line(s)"
                result = {}
            
            elif operation == 'split':
                if not editor_id or line_start is None or line_end is None:
                    return self._error("'editor_id', 'line_start', 'line_end' required for split")
                
                split_id = self.manager.split(editor_id, line_start, line_end)
                message = f"Created split view: lines {line_start}-{line_end}"
                result = {"split_id": split_id}
            
            elif operation == 'resize':
                window_id = split_id or editor_id
                if not window_id or line_start is None or line_end is None:
                    return self._error("'editor_id' or 'split_id', 'line_start', 'line_end' required for resize")
                
                self.manager.resize(window_id, line_start, line_end)
                message = f"Resized window to lines {line_start}-{line_end}"
                result = {}
            
            elif operation == 'close_split':
                if not split_id:
                    return self._error("'split_id' parameter required for close_split")
                
                success = self.manager.close_split(split_id)
                if not success:
                    return self._error(f"Split not found: {split_id}")
                
                message = "Closed split"
                result = {}
            
            elif operation == 'close':
                if not editor_id:
                    return self._error("'editor_id' parameter required for close")
                
                success = self.manager.close(editor_id)
                if not success:
                    return self._error(f"Editor not found: {editor_id}")
                
                message = "Closed editor"
                result = {}
            
            elif operation == 'close_all':
                self.manager.close_all()
                message = "Closed all editors"
                result = {}
            
            elif operation == 'status':
                status = self.manager.status()
                message = f"Editors: {status['editor_count']}, Total lines: {status['total_lines']}"
                result = status
            
            # Render to markdown and write to file
            rendered = self.manager.render()
            output_file = Path.cwd() / ".nisaba" / "tui" / "editor_view.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(rendered, encoding='utf-8')
            
            return {
                "success": True,
                "message": message,
                "nisaba": True,
                **result
            }
        
        except Exception as e:
            self.logger.error(f"Editor operation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "nisaba": True
            }
    
    def _error(self, msg: str) -> Dict[str, Any]:
        """Return error response."""
        return {
            "success": False,
            "error": msg,
            "error_type": "ValueError",
            "nisaba": True
        }
