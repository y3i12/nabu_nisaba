"""Editor tool - unified file editing with persistent windows."""

from abc import abstractmethod
from nisaba.tools.base_tool import BaseToolResponse
from nisaba.tools.base_operation_tool import BaseOperationTool, Operation
from nisaba.tui.editor_manager import EditorManager, get_editor_manager
from pathlib import Path
from typing import Dict, Any, Optional
from typing import Any, Dict, TYPE_CHECKING, get_type_hints

if TYPE_CHECKING:
    from nisaba.factory import MCPFactory

class EditorTool(BaseOperationTool):
    """
    Execute editor operation.

    Unified file editing with workspace persistence for reading, writing, or editing files
    """
    
    def __init__(self, factory:"MCPFactory"):
        super().__init__(
            factory=factory
        )

    @classmethod
    def nisaba(cls) -> bool:
        return True
    
    @classmethod
    def _format_str(cls, _str:str) -> str:
        return f"{_str}"
    
    @classmethod
    def _format_ok(cls, ok:bool) -> str:
        if ok:
            return "ok"
        
        return "not ok and shouldn't happen"
    
    @classmethod
    def _format_editor_id(cls, str:str) -> str:
        return f"editor_id({str})"
    
    @classmethod
    def _format_split_id(cls, str:str) -> str:
        return f"split_id({str})"

    @classmethod
    def get_operation_config(cls) -> Dict[str,Operation]:
        return cls.make_operations([
                cls.make_operation(
                    command=get_editor_manager().open,
                    name='open',
                    description='Open file in editor (returns existing if already open)',
                    result_formatter=cls._format_editor_id,
                    parameters=[
                        cls.make_parameter(name='file',required=True,description='File path')
                    ]
                ),
                cls.make_operation(
                    command=get_editor_manager().write,
                    name='write',
                    description='Write content to file and open editor',
                    result_formatter=cls._format_editor_id,
                    parameters=[
                        cls.make_parameter(name='file',required=True,description='File path'),
                        cls.make_parameter(name='content',required=True,description='File content')
                    ]
                ),
                cls.make_operation(
                    command=get_editor_manager().replace,
                    name='replace',
                    description='Replace string in editor content',
                    result_formatter=cls._format_ok,
                    parameters=[
                        cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
                        cls.make_parameter(name='old',required=True,description='String to replace'),
                        cls.make_parameter(name='new',required=True,description='Replacement string'),
                    ],
                    skip_render=True
                ),
                cls.make_operation(
                    command=get_editor_manager().replace_lines,
                    name='replace_lines',
                    description='Replace line range with new content',
                    result_formatter=cls._format_ok,
                    parameters=[
                        cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
                        cls.make_parameter(name='line_start',required=True,description='Line start'),
                        cls.make_parameter(name='line_end',required=True,description='Line end'),
                        cls.make_parameter(name='content',required=True,description='Replacement content'),
                    ],
                    skip_render=True
                ),
                cls.make_operation(
                    command=get_editor_manager().insert,
                    name='insert',
                    description='Insert content before specified line',
                    result_formatter=cls._format_ok,
                    parameters=[
                        cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
                        cls.make_parameter(name='before_line',required=True,description='Line to insert before'),
                        cls.make_parameter(name='content',required=True,description='Content to be inserted'),
                    ],
                    skip_render=True
                ),
                cls.make_operation(
                    command=get_editor_manager().delete,
                    name='delete',
                    description='Delete line range',
                    result_formatter=cls._format_ok,
                    parameters=[
                        cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
                        cls.make_parameter(name='line_start',required=True,description='Line start'),
                        cls.make_parameter(name='line_end',required=True,description='Line end'),
                    ],
                    skip_render=True
                ),
                cls.make_operation(
                    command=get_editor_manager().split,
                    name='split',
                    description='Create split view of editor',
                    result_formatter=cls._format_split_id,
                    parameters=[
                        cls.make_parameter(name='editor_id',required_or='split_id',description='Editor ID'),
                        cls.make_parameter(name='split_id',required=True,description='Slipt ID'),
                        cls.make_parameter(name='line_start',required=True,description='Line start'),
                        cls.make_parameter(name='line_end',required=True,description='Line end'),
                    ]
                ),
                cls.make_operation(
                    command=get_editor_manager().resize,
                    name='resize',
                    description='Resize editor or split window',
                    result_formatter=cls._format_ok,
                    parameters=[
                        cls.make_parameter(name='editor_id',required_or='split_id',description='Editor ID'),
                        cls.make_parameter(name='split_id',required=True,description='Slipt ID'),
                        cls.make_parameter(name='line_start',required=True,description='Line start'),
                        cls.make_parameter(name='line_end',required=True,description='Line end'),
                    ]
                ),
                cls.make_operation(
                    command=get_editor_manager().close,
                    name='close',
                    description='Close editor or split view',
                    result_formatter=cls._format_ok,
                    parameters=[
                        cls.make_parameter(name='editor_id',required_or='split_id',description='Editor ID'),
                        cls.make_parameter(name='split_id',required=True,description='Split ID'),
                    ]
                ),
                cls.make_operation(
                    command=get_editor_manager().close_all,
                    name='close_all',
                    description='Close all editor windows',
                    result_formatter=cls._format_str,
                    parameters=[]
                ),
            ])

    def _render(self):
        rendered = get_editor_manager().render()
        output_file = Path.cwd() / ".nisaba" / "tui" / "editor_view.md"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(rendered, encoding='utf-8')















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