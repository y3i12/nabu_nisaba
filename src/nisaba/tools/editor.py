"""Editor tool - unified file editing with persistent windows."""


from nisaba.tools.base_operation_tool import BaseOperationTool, Operation
from nisaba.tui.editor_manager import get_editor_manager
from pathlib import Path
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from nisaba.factory import MCPFactory

class EditorTool(BaseOperationTool):
    """
    Execute editor operations for reading, writing, or editing files.

    The editor lives in the workspace in the message section, as the last message, wrapped in
    `<system_reminder></system_reminder>`.
    """
    
    def __init__(self, factory:"MCPFactory"):
        super().__init__(
            factory=factory
        )

    @classmethod
    def nisaba(cls) -> bool:
        return True
    
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