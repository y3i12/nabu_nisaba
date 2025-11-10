---EDITOR_23ba004b-bd68-40ee-b07d-8a4818ed84b3
**file**: /home/y3i12/nabu_nisaba/src/nisaba/tools/editor.py
**lines**: 1-218 (218 lines)

1: """Editor tool - unified file editing with persistent windows."""
2: 
3: from abc import abstractmethod
4: from nisaba.tools.base_tool import BaseToolResponse
5: from nisaba.tools.base_operation_tool import BaseOperationTool, Operation
6: from nisaba.tui.editor_manager import EditorManager, get_editor_manager
7: from pathlib import Path
8: from typing import Dict, Any, Optional
9: from typing import Any, Dict, TYPE_CHECKING, get_type_hints
10: 
11: if TYPE_CHECKING:
12:     from nisaba.factory import MCPFactory
13: 
14: class EditorTool(BaseOperationTool):
15:     """
16:     Execute editor operation.
17: 
18:     Unified file editing with workspace persistence for reading, writing, or editing files
19:     """
20:     
21:     def __init__(self, factory:"MCPFactory"):
22:         super().__init__(
23:             factory=factory
24:         )
25: 
26:     @classmethod
27:     def nisaba(cls) -> bool:
28:         return True
29:     
30:     @classmethod
31:     def _format_str(cls, _str:str) -> str:
32:         return f"{_str}"
33:     
34:     @classmethod
35:     def _format_ok(cls, ok:bool) -> str:
36:         if ok:
37:             return "ok"
38:         
39:         return "not ok and shouldn't happen"
40:     
41:     @classmethod
42:     def _format_editor_id(cls, str:str) -> str:
43:         return f"editor_id({str})"
44:     
45:     @classmethod
46:     def _format_split_id(cls, str:str) -> str:
47:         return f"split_id({str})"
48: 
49:     @classmethod
50:     def get_operation_config(cls) -> Dict[str,Operation]:
51:         return cls.make_operations([
52:                 cls.make_operation(
53:                     command=get_editor_manager().open,
54:                     name='open',
55:                     description='Open file in editor (returns existing if already open)',
56:                     result_formatter=cls._format_editor_id,
57:                     parameters=[
58:                         cls.make_parameter(name='file',required=True,description='File path')
59:                     ]
60:                 ),
61:                 cls.make_operation(
62:                     command=get_editor_manager().write,
63:                     name='write',
64:                     description='Write content to file and open editor',
65:                     result_formatter=cls._format_editor_id,
66:                     parameters=[
67:                         cls.make_parameter(name='file',required=True,description='File path'),
68:                         cls.make_parameter(name='content',required=True,description='File content')
69:                     ]
70:                 ),
71:                 cls.make_operation(
72:                     command=get_editor_manager().replace,
73:                     name='replace',
74:                     description='Replace string in editor content',
75:                     result_formatter=cls._format_ok,
76:                     parameters=[
77:                         cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
78:                         cls.make_parameter(name='old',required=True,description='String to replace'),
79:                         cls.make_parameter(name='new',required=True,description='Replacement string'),
80:                     ],
81:                     skip_render=True
82:                 ),
83:                 cls.make_operation(
84:                     command=get_editor_manager().replace_lines,
85:                     name='replace_lines',
86:                     description='Replace line range with new content',
87:                     result_formatter=cls._format_ok,
88:                     parameters=[
89:                         cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
90:                         cls.make_parameter(name='line_start',required=True,description='Line start'),
91:                         cls.make_parameter(name='line_end',required=True,description='Line end'),
92:                         cls.make_parameter(name='content',required=True,description='Replacement content'),
93:                     ],
94:                     skip_render=True
95:                 ),
96:                 cls.make_operation(
97:                     command=get_editor_manager().insert,
98:                     name='insert',
99:                     description='Insert content before specified line',
100:                     result_formatter=cls._format_ok,
101:                     parameters=[
102:                         cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
103:                         cls.make_parameter(name='before_line',required=True,description='Line to insert before'),
104:                         cls.make_parameter(name='content',required=True,description='Content to be inserted'),
105:                     ],
106:                     skip_render=True
107:                 ),
108:                 cls.make_operation(
109:                     command=get_editor_manager().delete,
110:                     name='delete',
111:                     description='Delete line range',
112:                     result_formatter=cls._format_ok,
113:                     parameters=[
114:                         cls.make_parameter(name='editor_id',required=True,description='Editor ID'),
115:                         cls.make_parameter(name='line_start',required=True,description='Line start'),
116:                         cls.make_parameter(name='line_end',required=True,description='Line end'),
117:                     ],
118:                     skip_render=True
119:                 ),
120:                 cls.make_operation(
121:                     command=get_editor_manager().split,
122:                     name='split',
123:                     description='Create split view of editor',
124:                     result_formatter=cls._format_split_id,
125:                     parameters=[
126:                         cls.make_parameter(name='editor_id',required_or='split_id',description='Editor ID'),
127:                         cls.make_parameter(name='split_id',required=True,description='Slipt ID'),
128:                         cls.make_parameter(name='line_start',required=True,description='Line start'),
129:                         cls.make_parameter(name='line_end',required=True,description='Line end'),
130:                     ]
131:                 ),
132:                 cls.make_operation(
133:                     command=get_editor_manager().resize,
134:                     name='resize',
135:                     description='Resize editor or split window',
136:                     result_formatter=cls._format_ok,
137:                     parameters=[
138:                         cls.make_parameter(name='editor_id',required_or='split_id',description='Editor ID'),
139:                         cls.make_parameter(name='split_id',required=True,description='Slipt ID'),
140:                         cls.make_parameter(name='line_start',required=True,description='Line start'),
141:                         cls.make_parameter(name='line_end',required=True,description='Line end'),
142:                     ]
143:                 ),
144:                 cls.make_operation(
145:                     command=get_editor_manager().close,
146:                     name='close',
147:                     description='Close editor or split view',
148:                     result_formatter=cls._format_ok,
149:                     parameters=[
150:                         cls.make_parameter(name='editor_id',required_or='split_id',description='Editor ID'),
151:                         cls.make_parameter(name='split_id',required=True,description='Split ID'),
152:                     ]
153:                 ),
154:                 cls.make_operation(
155:                     command=get_editor_manager().close_all,
156:                     name='close_all',
157:                     description='Close all editor windows',
158:                     result_formatter=cls._format_str,
159:                     parameters=[]
160:                 ),
161:             ])
162: 
163:     def _render(self):
164:         rendered = get_editor_manager().render()
165:         output_file = Path.cwd() / ".nisaba" / "tui" / "editor_view.md"
166:         output_file.parent.mkdir(parents=True, exist_ok=True)
167:         output_file.write_text(rendered, encoding='utf-8')
168: 
169: 
170: 
171: 
172: 
173: 
174: 
175: 
176: 
177: 
178: 
179: 
180: 
181: 
182: 
183: """
184: Execute editor operation.
185: 
186: Operations:
187: - open: Open file in editor (returns existing if already open)
188: - write: Write content to file and open editor
189: - replace: Replace string in editor content
190: - insert: Insert content before specified line
191: - delete: Delete line range
192: - replace_lines: Replace line range with new content
193: - split: Create split view of editor
194: - resize: Resize editor or split window
195: - close_split: Close split view
196: - close: Close editor window (and all splits)
197: - close_all: Close all editor windows
198: - status: Get editor status summary
199: 
200: :meta pitch: Unified file editing with workspace persistence
201: :meta when: Reading, writing, or editing files
202: Args:
203:     operation: Operation type
204:     file: File path (for open, write)
205:     content: File content (for write)
206:     editor_id: Editor window ID (for replace, insert, delete, replace_lines, split, close)
207:     old: String to replace (for replace)
208:     new: Replacement string (for replace)
209:     line_start: Start line for open/delete/replace_lines/split/resize (1-indexed, default 1)
210:     line_end: End line for open/delete/replace_lines/split/resize (-1 = end of file, default -1)
211:     before_line: Line to insert before (for insert)
212:     split_id: Split ID (for close_split, resize)
213:     before_line: Line to insert before (for insert)
214:     split_id: Split ID (for close_split, resize)
215: 
216: Returns:
217:     Dict with success status and operation result
218: """