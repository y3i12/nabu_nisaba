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
            from nisaba.tui.editor_manager import EditorManager
            self._manager = EditorManager()
        return self._manager
    
    async def execute(
        self,
        operation: str,
        file: Optional[str] = None,
        content: Optional[str] = None,
        editor_id: Optional[str] = None,
        old_string: Optional[str] = None,
        new_string: Optional[str] = None,
        line_start: Optional[int] = 1,
        line_end: Optional[int] = -1
    ) -> Dict[str, Any]:
        """
        Execute editor operation.
        
        Operations:
        - open: Open file in editor (returns existing if already open)
        - write: Write content to file and open editor
        - replace: Replace string in editor content
        - close: Close editor window
        - close_all: Close all editor windows
        - status: Get editor status summary
        
        :meta pitch: Unified file editing with workspace persistence
        :meta when: Reading, writing, or editing files
        
        Args:
            operation: Operation type
            file: File path (for open, write)
            content: File content (for write)
            editor_id: Editor window ID (for replace, close)
            old_string: String to replace (for replace)
            new_string: Replacement string (for replace)
            line_start: Start line for open (1-indexed, default 1)
            line_end: End line for open (-1 = end of file, default -1)
        
        Returns:
            Dict with success status and operation result
        """
        valid_ops = ['open', 'write', 'replace', 'close', 'close_all', 'status']
        
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
                result = {"editor_id": editor_id}
            
            elif operation == 'replace':
                if not editor_id or not old_string or new_string is None:
                    return self._error("'editor_id', 'old_string', 'new_string' required for replace")
                
                self.manager.replace(editor_id, old_string, new_string)
                message = f"Replaced in editor: {old_string[:30]}... → {new_string[:30]}..."
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
            output_file = Path.cwd() / ".nisaba" / "editor_windows.md"
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
