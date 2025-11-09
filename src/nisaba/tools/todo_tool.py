"""
Todo management tool for nisaba workspace.
"""
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pathlib import Path
from nisaba import MCPTool, MCPToolResponse
from nisaba.structured_file import StructuredFileCache

if TYPE_CHECKING:
    from nisaba.factory import MCPFactory

class TodoWriteTool(MCPTool):
    """Manage todos in persistent workspace file with numbered operations."""

    def __init__(self, factory: "MCPFactory"):
        """Initialize the TodoWriteTool with StructuredFileCache."""
        super().__init__(factory)
        # Use StructuredFileCache for atomic read-modify-write operations
        self._todos_file = StructuredFileCache(
            file_path=Path("./.nisaba/tui/todo_view.md"),
            name="todo",
            tag=None  # No tag wrapping for todos
        )

    def _parse_todos(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse numbered markdown list into structured format.
        
        Args:
            content: File content with numbered todos
            
        Returns:
            List of dicts with 'content' and 'done' keys
        """
        import re
        pattern = r'^\s*\d+\.\s*\[([ x])\]\s*(.+)$'
        
        todos = []
        for line in content.strip().split('\n'):
            if not line.strip():
                continue
            match = re.match(pattern, line)
            if match:
                done = match.group(1) == 'x'
                content_text = match.group(2).strip()
                todos.append({
                    "content": content_text,
                    "done": done
                })
        return todos
    
    def _format_todos(self, todos: List[Dict[str, Any]]) -> str:
        """
        Format structured todos into numbered markdown.
        
        Args:
            todos: List of dicts with 'content' and 'done' keys
            
        Returns:
            Formatted markdown string
        """
        lines = []
        for i, todo in enumerate(todos, start=1):
            checkbox = 'x' if todo.get('done', False) else ' '
            content = todo.get('content', '')
            lines.append(f"{i}. [{checkbox}] {content}")
        return '\n'.join(lines)
    
    def _validate_indices(self, indices: List[int], max_index: int) -> None:
        """
        Validate indices are within bounds (1-based).
        
        Args:
            indices: List of indices to validate
            max_index: Maximum valid index
            
        Raises:
            ValueError: If any index is out of bounds
        """
        for idx in indices:
            if idx < 1 or idx > max_index:
                raise ValueError(f"Index {idx} out of bounds (valid: 1-{max_index})")
    
    async def execute(
        self,
        operation: str,
        todos: Optional[List[Dict[str, Any]]] = None,
        index: Optional[int] = None,
        indices: Optional[List[int]] = None,
        position: Optional[int] = None
    ) -> MCPToolResponse:
        """
        Manage todo list with numbered operations.
        
        Todos are stored as numbered markdown in .nisaba/todos.md and injected into system prompt.
        Survives /clear and session restarts.
        
        :meta pitch: Track task progress with indexed operations
        :meta when: Use when breaking down complex tasks or tracking progress
        
        Args:
            operation: Operation type
                'set' - replace all todos (requires todos)
                'extend' - add todos at position (requires todos, optional position)
                'remove' - remove by index/indices
                'mark_done' - mark as done by index/indices
                'mark_undone' - mark as pending by index/indices
                'set_all_done' - mark all todos as done
                'clear' - remove all todos
            todos: List of todo items with 'content' and optional 'done'
                   Example: [{"content": "Fix bug", "done": false}]
            index: Single index for operations (1-based)
            indices: Multiple indices for batch operations (1-based)
            position: Position to insert for 'extend' (1-based, None=append)
        
        Returns:
            Dict with success status and message
        """
        try:
            # Ensure directory exists
            self._todos_file.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Normalize index/indices to list
            target_indices = []
            if index is not None:
                target_indices = [index]
            elif indices is not None:
                target_indices = indices
            
            # Handle operations
            if operation == "clear":
                self._todos_file.write("")
                return {
                    "success": True,
                    "message": "Cleared all todos",
                    "nisaba": True,
                }
            
            elif operation == "set":
                if todos is None:
                    return {
                        "success": False,
                        "error": "operation 'set' requires 'todos' parameter",
                        "nisaba": True,
                    }
                # Convert input format to internal format
                parsed = []
                for item in todos:
                    parsed.append({
                        "content": item.get("content", ""),
                        "done": item.get("done", False) or item.get("status") in ["completed", "done"]
                    })
                content = self._format_todos(parsed)
                self._todos_file.write(content)
                return {
                    "success": True,
                    "message": f"Set {len(parsed)} todo(s)",
                    "nisaba": True,
                }
            
            elif operation == "extend":
                if todos is None:
                    return {
                        "success": False,
                        "error": "operation 'extend' requires 'todos' parameter",
                        "nisaba": True,
                    }
                
                # Convert new todos
                new_todos = []
                for item in todos:
                    new_todos.append({
                        "content": item.get("content", ""),
                        "done": item.get("done", False) or item.get("status") in ["completed", "done"]
                    })
                
                # Use list to capture actual position in closure
                actual_position = [position if position is not None else -1]
                
                def extend_todos(content: str) -> str:
                    """Extend todos at position."""
                    existing = self._parse_todos(content) if content.strip() else []
                    
                    # Determine insert position
                    pos = position
                    if pos is None:
                        pos = len(existing) + 1
                    else:
                        if pos < 1:
                            pos = 1
                        if pos > len(existing) + 1:
                            pos = len(existing) + 1
                    
                    actual_position[0] = pos
                    
                    # Insert at position (1-based to 0-based)
                    insert_idx = pos - 1
                    result = existing[:insert_idx] + new_todos + existing[insert_idx:]
                    
                    return self._format_todos(result)
                
                # Atomic update
                self._todos_file.atomic_update(extend_todos)
                
                # Format rich message
                if len(new_todos) == 1:
                    msg = f"Extended at position {actual_position[0]}: {new_todos[0]['content']}"
                else:
                    msg = f"Extended at position {actual_position[0]} with {len(new_todos)} items"
                
                return {
                    "success": True,
                    "message": msg,
                    "nisaba": True,
                    "position": actual_position[0],
                    "items": [item["content"] for item in new_todos]
                }
            
            elif operation == "remove":
                if not target_indices:
                    return {
                        "success": False,
                        "error": "operation 'remove' requires 'index' or 'indices' parameter",
                        "nisaba": True,
                    }
                
                # Use list to capture removed items in closure
                removed_items = []
                
                def remove_items(content: str) -> str:
                    """Remove todos by index."""
                    existing = self._parse_todos(content) if content.strip() else []
                    self._validate_indices(target_indices, len(existing))
                    
                    # Collect items to remove for notification
                    for idx in target_indices:
                        removed_items.append({
                            "index": idx,
                            "content": existing[idx - 1]["content"]
                        })
                    
                    # Remove in descending order to preserve indices
                    for idx in sorted(target_indices, reverse=True):
                        del existing[idx - 1]  # Convert 1-based to 0-based
                    
                    return self._format_todos(existing)
                
                # Atomic update
                self._todos_file.atomic_update(remove_items)
                
                # Format rich message
                if len(removed_items) == 1:
                    msg = f"Removed item {removed_items[0]['index']}: {removed_items[0]['content']}"
                else:
                    items_str = ", ".join([f"{item['index']}" for item in removed_items])
                    msg = f"Removed items [{items_str}]"
                
                return {
                    "success": True,
                    "message": msg,
                    "nisaba": True,
                    "removed": removed_items
                }
            
            elif operation == "mark_done":
                if not target_indices:
                    return {
                        "success": False,
                        "error": "operation 'mark_done' requires 'index' or 'indices' parameter",
                        "nisaba": True,
                    }
                
                # Use list to capture marked items in closure
                marked_items = []
                
                def mark_done(content: str) -> str:
                    """Mark todos as done."""
                    existing = self._parse_todos(content) if content.strip() else []
                    self._validate_indices(target_indices, len(existing))
                    
                    # Collect items for notification
                    for idx in target_indices:
                        marked_items.append({
                            "index": idx,
                            "content": existing[idx - 1]["content"]
                        })
                    
                    # Mark as done
                    for idx in target_indices:
                        existing[idx - 1]["done"] = True
                    
                    return self._format_todos(existing)
                
                # Atomic update
                self._todos_file.atomic_update(mark_done)
                
                # Format rich message
                if len(marked_items) == 1:
                    msg = f"Marked done [{marked_items[0]['index']}]: {marked_items[0]['content']}"
                else:
                    items_str = ", ".join([str(item['index']) for item in marked_items])
                    msg = f"Marked done [{items_str}]"
                
                return {
                    "success": True,
                    "message": msg,
                    "nisaba": True,
                    "indices": target_indices,
                    "items": marked_items
                }
            
            elif operation == "mark_undone":
                if not target_indices:
                    return {
                        "success": False,
                        "error": "operation 'mark_undone' requires 'index' or 'indices' parameter",
                        "nisaba": True,
                    }
                
                # Use list to capture unmarked items in closure
                unmarked_items = []
                
                def mark_undone(content: str) -> str:
                    """Mark todos as undone."""
                    existing = self._parse_todos(content) if content.strip() else []
                    self._validate_indices(target_indices, len(existing))
                    
                    # Collect items for notification
                    for idx in target_indices:
                        unmarked_items.append({
                            "index": idx,
                            "content": existing[idx - 1]["content"]
                        })
                    
                    # Mark as undone
                    for idx in target_indices:
                        existing[idx - 1]["done"] = False
                    
                    return self._format_todos(existing)
                
                # Atomic update
                self._todos_file.atomic_update(mark_undone)
                
                # Format rich message
                if len(unmarked_items) == 1:
                    msg = f"Marked pending [{unmarked_items[0]['index']}]: {unmarked_items[0]['content']}"
                else:
                    items_str = ", ".join([str(item['index']) for item in unmarked_items])
                    msg = f"Marked pending [{items_str}]"
                
                return {
                    "success": True,
                    "message": msg,
                    "nisaba": True,
                    "indices": target_indices,
                    "items": unmarked_items
                }
            
            elif operation == "set_all_done":
                def mark_all_done(content: str) -> str:
                    """Mark all todos as done."""
                    existing = self._parse_todos(content) if content.strip() else []
                    
                    # Mark all as done
                    for todo in existing:
                        todo["done"] = True
                    
                    return self._format_todos(existing)
                
                # Atomic update
                self._todos_file.atomic_update(mark_all_done)
                
                # Get count from cache
                content = self._todos_file.content
                existing = self._parse_todos(content) if content.strip() else []
                
                return {
                    "success": True,
                    "nisaba": True,
                    "message": f"Marked all {len(existing)} todo(s) as done"
                }
            
            else:
                return {
                    "success": False,
                    "nisaba": True,
                    "error": f"Unknown operation: {operation}"
                }
        
        except ValueError as e:
            self.logger.error(f"Validation error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "nisaba": True,
                "error_type": "ValueError"
            }
        except Exception as e:
            self.logger.error(f"Failed to manage todos: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "nisaba": True,
                "error_type": type(e).__name__
            }

