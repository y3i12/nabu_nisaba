---EDITOR_2f564a94-c575-472f-9b1b-36925b8b9bd6
**file**: /home/y3i12/nabu_nisaba/src/nisaba/tools/editor.py
**lines**: 1-155 (155 lines)

1: """Editor tool - unified file editing with persistent windows."""
2: 
3: 
4: from nisaba.tools.base_operation_tool import BaseOperationTool, Operation
5: from nisaba.tui.editor_manager import get_editor_manager
6: from pathlib import Path
7: from typing import Dict, TYPE_CHECKING
8: 
9: if TYPE_CHECKING:
10:     from nisaba.factory import MCPFactory
11: 
12: class EditorTool(BaseOperationTool):
13:     """
14:     Execute editor operations for reading, writing, or editing files.
15: 
16:     The editor lives in the workspace in the message section, as the last message, wrapped in
17:     `<system_reminder></system_reminder>`.
18:     """
19:     
20:     def __init__(self, factory:"MCPFactory"):
21:         super().__init__(
22:             factory=factory
23:         )
24: 
25:     @classmethod
26:     def nisaba(cls) -> bool:
27:         return True
28:     
29:     @classmethod
30:     def _format_editor_id(cls, str:str) -> str:
31:         return f"editor_id({str})"
32:     
33:     @classmethod
34:     def _format_split_id(cls, str:str) -> str:
35:         return f"split_id({str})"
36: 
37:     @classmethod
38:     def get_operation_config(cls) -> Dict[str,Operation]:
39:         return cls.make_operations([
40:                 cls.make_operation(
41:                     command=get_editor_manager().open,
42:                     name='open',
43:                     description='Open file in editor (returns existing if already open)',
44:                     result_formatter=cls._format_editor_id,
45:                     parameters=[
46:                         cls.make_parameter(name='file',required=True,description='File path')
47:                     ]
48:                 ),
49:                 cls.make_operation(
50:                     command=get_editor_manager().write,
51:                     name='write',
52:                     description='Write content to file and open editor',
53:                     result_formatter=cls._format_editor_id,
54:                     parameters=[
55:                         cls.make_parameter(name='file',required=True,description='File path'),
56:                         cls.make_parameter(name='content',required=True,description='File content')
57:                     ]
58:                 ),
59:                 cls.make_operation(
60:                     command=get_editor_manager().replace,
61:                     name='replace',
62:                     description='Replace string in editor content',
63:                     result_formatter=cls._format_ok,
64:                     parameters=[
65:                         cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
66:                         cls.make_parameter(name='old',required=True,description='String to replace'),
67:                         cls.make_parameter(name='new',required=True,description='Replacement string'),
68:                     ],
69:                     skip_render=True
70:                 ),
71:                 cls.make_operation(
72:                     command=get_editor_manager().replace_lines,
73:                     name='replace_lines',
74:                     description='Replace line range with new content',
75:                     result_formatter=cls._format_ok,
76:                     parameters=[
77:                         cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
78:                         cls.make_parameter(name='line_start',required=True,description='Line start'),
79:                         cls.make_parameter(name='line_end',required=True,description='Line end'),
80:                         cls.make_parameter(name='content',required=True,description='Replacement content'),
81:                     ],
82:                     skip_render=True
83:                 ),
84:                 cls.make_operation(
85:                     command=get_editor_manager().insert,
86:                     name='insert',
87:                     description='Insert content before specified line',
88:                     result_formatter=cls._format_ok,
89:                     parameters=[
90:                         cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
91:                         cls.make_parameter(name='before_line',required=True,description='Line to insert before'),
92:                         cls.make_parameter(name='content',required=True,description='Content to be inserted'),
93:                     ],
94:                     skip_render=True
95:                 ),
96:                 cls.make_operation(
97:                     command=get_editor_manager().delete,
98:                     name='delete',
99:                     description='Delete line range',
100:                     result_formatter=cls._format_ok,
101:                     parameters=[
102:                         cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
103:                         cls.make_parameter(name='line_start',required=True,description='Line start'),
104:                         cls.make_parameter(name='line_end',required=True,description='Line end'),
105:                     ],
106:                     skip_render=True
107:                 ),
108:                 cls.make_operation(
109:                     command=get_editor_manager().split,
110:                     name='split',
111:                     description='Create split view of editor',
112:                     result_formatter=cls._format_split_id,
113:                     parameters=[
114:                         cls.make_parameter(name='editor_id',required_or='split_id',description='Editor ID'),
115:                         cls.make_parameter(name='split_id',required=True,description='Slipt ID'),
116:                         cls.make_parameter(name='line_start',required=True,description='Line start'),
117:                         cls.make_parameter(name='line_end',required=True,description='Line end'),
118:                     ]
119:                 ),
120:                 cls.make_operation(
121:                     command=get_editor_manager().resize,
122:                     name='resize',
123:                     description='Resize editor or split window',
124:                     result_formatter=cls._format_ok,
125:                     parameters=[
126:                         cls.make_parameter(name='editor_id',required_or='split_id',description='Editor ID'),
127:                         cls.make_parameter(name='split_id',required=True,description='Slipt ID'),
128:                         cls.make_parameter(name='line_start',required=True,description='Line start'),
129:                         cls.make_parameter(name='line_end',required=True,description='Line end'),
130:                     ]
131:                 ),
132:                 cls.make_operation(
133:                     command=get_editor_manager().close,
134:                     name='close',
135:                     description='Close editor or split view',
136:                     result_formatter=cls._format_ok,
137:                     parameters=[
138:                         cls.make_parameter(name='editor_id',required_or='split_id',description='Editor ID'),
139:                         cls.make_parameter(name='split_id',required=True,description='Split ID'),
140:                     ]
141:                 ),
142:                 cls.make_operation(
143:                     command=get_editor_manager().close_all,
144:                     name='close_all',
145:                     description='Close all editor windows',
146:                     result_formatter=cls._format_str,
147:                     parameters=[]
148:                 ),
149:             ])
150: 
151:     def _render(self):
152:         rendered = get_editor_manager().render()
153:         output_file = Path.cwd() / ".nisaba" / "tui" / "editor_view.md"
154:         output_file.parent.mkdir(parents=True, exist_ok=True)
155:         output_file.write_text(rendered, encoding='utf-8')