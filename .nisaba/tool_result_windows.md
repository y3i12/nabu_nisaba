---TOOL_RESULT_WINDOW_6e9a354f-1167-43d7-bb28-dfd83aebb041
**type**: read_result
**file**: src/nisaba/tools/editor.py
**lines**: 1-214
**total_lines**: 214

1: """Editor tool - unified file editing with persistent windows."""
2: 
3: from typing import Dict, Any, Optional
4: from pathlib import Path
5: from nisaba.tools.base import NisabaTool
6: 
7: 
8: class EditorTool(NisabaTool):
9:     """
10:     Unified file editor with persistent windows and change tracking.
11:     
12:     Replaces nisaba_read, nisaba_write, nisaba_edit with single coherent interface.
13:     """
14:     
15:     def __init__(self, factory):
16:         super().__init__(factory)
17:         self._manager = None
18:     
19:     @property
20:     def manager(self):
21:         """Lazy-initialize editor manager (persists across operations)."""
22:         if self._manager is None:
23:             from nisaba.tui.editor_manager import EditorManager
24:             self._manager = EditorManager()
25:         return self._manager
26:     
27:     async def execute(
28:         self,
29:         operation: str,
30:         file: Optional[str] = None,
31:         content: Optional[str] = None,
32:         editor_id: Optional[str] = None,
33:         old_string: Optional[str] = None,
34:         new_string: Optional[str] = None,
35:         line_start: Optional[int] = 1,
36:         line_end: Optional[int] = -1,
37:         before_line: Optional[int] = None,
38:         split_id: Optional[str] = None
39:     ) -> Dict[str, Any]:
40:         """
41:         Execute editor operation.
42:         
43:         Operations:
44:         - open: Open file in editor (returns existing if already open)
45:         - write: Write content to file and open editor
46:         - replace: Replace string in editor content
47:         - insert: Insert content before specified line
48:         - delete: Delete line range
49:         - replace_lines: Replace line range with new content
50:         - split: Create split view of editor
51:         - resize: Resize editor or split window
52:         - close_split: Close split view
53:         - close: Close editor window (and all splits)
54:         - close_all: Close all editor windows
55:         - status: Get editor status summary
56:         
57:         :meta pitch: Unified file editing with workspace persistence
58:         :meta when: Reading, writing, or editing files
59:         
60:         Args:
61:             operation: Operation type
62:             file: File path (for open, write)
63:             content: File content (for write)
64:             editor_id: Editor window ID (for replace, insert, delete, replace_lines, split, close)
65:             old_string: String to replace (for replace)
66:             new_string: Replacement string (for replace)
67:             line_start: Start line for open/delete/replace_lines/split/resize (1-indexed, default 1)
68:             line_end: End line for open/delete/replace_lines/split/resize (-1 = end of file, default -1)
69:             before_line: Line to insert before (for insert)
70:             split_id: Split ID (for close_split, resize)
71:         
72:         Returns:
73:             Dict with success status and operation result
74:         """
75:         valid_ops = ['open', 'write', 'replace', 'insert', 'delete', 'replace_lines', 'split', 'resize', 'close_split', 'close', 'close_all', 'status']
76:         
77:         if operation not in valid_ops:
78:             return {
79:                 "success": False,
80:                 "error": f"Invalid operation: {operation}. Valid: {valid_ops}",
81:                 "error_type": "ValueError",
82:                 "nisaba": True
83:             }
84:         
85:         try:
86:             if operation == 'open':
87:                 if not file:
88:                     return self._error("'file' parameter required for open")
89:                 
90:                 editor_id = self.manager.open(file, line_start, line_end)
91:                 message = f"Opened editor: {file}"
92:                 result = {"editor_id": editor_id}
93:             
94:             elif operation == 'write':
95:                 if not file or content is None:
96:                     return self._error("'file' and 'content' parameters required for write")
97:                 
98:                 editor_id = self.manager.write(file, content)
99:                 message = f"Wrote file: {file}"
100:                 result = {"editor_id": editor_id}
101:             
102:             elif operation == 'replace':
103:                 if not editor_id or not old_string or new_string is None:
104:                     return self._error("'editor_id', 'old_string', 'new_string' required for replace")
105:                 
106:                 self.manager.replace(editor_id, old_string, new_string)
107:                 message = f"Replaced in editor: {old_string[:30]}... → {new_string[:30]}..."
108:                 result = {}
109:             
110:             elif operation == 'insert':
111:                 if not editor_id or before_line is None or content is None:
112:                     return self._error("'editor_id', 'before_line', 'content' required for insert")
113:                 
114:                 self.manager.insert(editor_id, before_line, content)
115:                 num_lines = len(content.split('\n'))
116:                 message = f"Inserted {num_lines} line(s) before line {before_line}"
117:                 result = {}
118:             
119:             elif operation == 'delete':
120:                 if not editor_id or line_start is None or line_end is None:
121:                     return self._error("'editor_id', 'line_start', 'line_end' required for delete")
122:                 
123:                 self.manager.delete(editor_id, line_start, line_end)
124:                 message = f"Deleted lines {line_start}-{line_end}"
125:                 result = {}
126:             
127:             elif operation == 'replace_lines':
128:                 if not editor_id or line_start is None or line_end is None or content is None:
129:                     return self._error("'editor_id', 'line_start', 'line_end', 'content' required for replace_lines")
130:                 
131:                 self.manager.replace_lines(editor_id, line_start, line_end, content)
132:                 num_lines = len(content.split('\n'))
133:                 message = f"Replaced lines {line_start}-{line_end} with {num_lines} line(s)"
134:                 result = {}
135:             
136:             elif operation == 'split':
137:                 if not editor_id or line_start is None or line_end is None:
138:                     return self._error("'editor_id', 'line_start', 'line_end' required for split")
139:                 
140:                 split_id = self.manager.split(editor_id, line_start, line_end)
141:                 message = f"Created split view: lines {line_start}-{line_end}"
142:                 result = {"split_id": split_id}
143:             
144:             elif operation == 'resize':
145:                 window_id = split_id or editor_id
146:                 if not window_id or line_start is None or line_end is None:
147:                     return self._error("'editor_id' or 'split_id', 'line_start', 'line_end' required for resize")
148:                 
149:                 self.manager.resize(window_id, line_start, line_end)
150:                 message = f"Resized window to lines {line_start}-{line_end}"
151:                 result = {}
152:             
153:             elif operation == 'close_split':
154:                 if not split_id:
155:                     return self._error("'split_id' parameter required for close_split")
156:                 
157:                 success = self.manager.close_split(split_id)
158:                 if not success:
159:                     return self._error(f"Split not found: {split_id}")
160:                 
161:                 message = "Closed split"
162:                 result = {}
163:             
164:             elif operation == 'close':
165:                 if not editor_id:
166:                     return self._error("'editor_id' parameter required for close")
167:                 
168:                 success = self.manager.close(editor_id)
169:                 if not success:
170:                     return self._error(f"Editor not found: {editor_id}")
171:                 
172:                 message = "Closed editor"
173:                 result = {}
174:             
175:             elif operation == 'close_all':
176:                 self.manager.close_all()
177:                 message = "Closed all editors"
178:                 result = {}
179:             
180:             elif operation == 'status':
181:                 status = self.manager.status()
182:                 message = f"Editors: {status['editor_count']}, Total lines: {status['total_lines']}"
183:                 result = status
184:             
185:             # Render to markdown and write to file
186:             rendered = self.manager.render()
187:             output_file = Path.cwd() / ".nisaba" / "editor_windows.md"
188:             output_file.parent.mkdir(parents=True, exist_ok=True)
189:             output_file.write_text(rendered, encoding='utf-8')
190:             
191:             return {
192:                 "success": True,
193:                 "message": message,
194:                 "nisaba": True,
195:                 **result
196:             }
197:         
198:         except Exception as e:
199:             self.logger.error(f"Editor operation failed: {e}", exc_info=True)
200:             return {
201:                 "success": False,
202:                 "error": str(e),
203:                 "error_type": type(e).__name__,
204:                 "nisaba": True
205:             }
206:     
207:     def _error(self, msg: str) -> Dict[str, Any]:
208:         """Return error response."""
209:         return {
210:             "success": False,
211:             "error": msg,
212:             "error_type": "ValueError",
213:             "nisaba": True
214:         }
---TOOL_RESULT_WINDOW_6e9a354f-1167-43d7-bb28-dfd83aebb041_END

---TOOL_RESULT_WINDOW_80077eb4-8377-4b1b-bd11-751cb5f816ef
**type**: read_result
**file**: src/nisaba/tui/editor_manager.py
**lines**: 1-737
**total_lines**: 737

1: """Editor manager - unified file editing with persistent windows."""
2: 
3: import json
4: import logging
5: import difflib
6: import time
7: from pathlib import Path
8: from typing import Dict, List, Optional, Any
9: 
10: from nisaba.tui.editor_window import EditorWindow, Edit
11: 
12: logger = logging.getLogger(__name__)
13: 
14: 
15: class EditorManager:
16:     """
17:     Manages collection of editor windows.
18:     
19:     Key features:
20:     - One editor per file (no duplicates)
21:     - Immediate commit to disk
22:     - Change tracking with edit history
23:     - Diff rendering with inline markers
24:     """
25:     
26:     def __init__(self):
27:         self.editors: Dict[Path, EditorWindow] = {}  # file_path → editor
28:         self.state_file = Path.cwd() / ".nisaba" / "editor_state.json"
29:         self.output_file = Path.cwd() / ".nisaba" / "editor_windows.md"
30:         self.load_state()
31:     
32:     def open(self, file: str, line_start: int = 1, line_end: int = -1) -> str:
33:         """
34:         Open file in editor. Returns existing editor_id if already open.
35:         
36:         Args:
37:             file: File path
38:             line_start: Start line (1-indexed)
39:             line_end: End line (-1 = end of file, inclusive)
40:         
41:         Returns:
42:             editor_id
43:         """
44:         file_path = Path(file).resolve()
45:         
46:         # Return existing editor if already open
47:         if file_path in self.editors:
48:             logger.info(f"File already open: {file_path}")
49:             return self.editors[file_path].id
50:         
51:         # Read file
52:         try:
53:             with open(file_path, 'r', encoding='utf-8') as f:
54:                 all_lines = f.readlines()
55:             
56:             # Strip newlines
57:             all_lines = [line.rstrip('\n') for line in all_lines]
58:             
59:             # Handle line range
60:             if line_end == -1:
61:                 content = all_lines[line_start-1:] if line_start > 1 else all_lines
62:                 actual_end = len(all_lines)
63:             else:
64:                 content = all_lines[line_start-1:line_end]
65:                 actual_end = line_end
66:             
67:             # Get file mtime
68:             mtime = file_path.stat().st_mtime
69:             
70:             # Create editor
71:             editor = EditorWindow(
72:                 file_path=file_path,
73:                 line_start=line_start,
74:                 line_end=actual_end,
75:                 content=content,
76:                 original_content=content.copy(),
77:                 edits=[],
78:                 last_mtime=mtime
79:             )
80:             
81:             self.editors[file_path] = editor
82:             self.save_state()
83:             
84:             logger.info(f"Opened editor: {file_path} ({len(content)} lines)")
85:             return editor.id
86:             
87:         except Exception as e:
88:             logger.error(f"Failed to open {file_path}: {e}", exc_info=True)
89:             raise
90:     
91:     def write(self, file: str, content: str) -> str:
92:         """
93:         Write content to file and open editor.
94:         
95:         Args:
96:             file: File path
97:             content: File content
98:         
99:         Returns:
100:             editor_id
101:         """
102:         file_path = Path(file).resolve()
103:         
104:         try:
105:             # Create parent directories
106:             file_path.parent.mkdir(parents=True, exist_ok=True)
107:             
108:             # Write to disk
109:             file_path.write_text(content, encoding='utf-8')
110:             logger.info(f"Wrote file: {file_path}")
111:             
112:             # Open editor (will create new or return existing)
113:             editor_id = self.open(str(file_path))
114:             self._add_notification(f"✓ editor.write() → created {file_path.name}")
115:             return editor_id
116:             
117:         except Exception as e:
118:             logger.error(f"Failed to write {file_path}: {e}", exc_info=True)
119:             raise
120:     
121:     def replace(self, editor_id: str, old_string: str, new_string: str) -> bool:
122:         """
123:         Replace string in editor content and write to disk.
124:         
125:         Args:
126:             editor_id: Editor window ID
127:             old_string: String to replace
128:             new_string: Replacement string
129:         
130:         Returns:
131:             True if successful
132:         """
133:         editor = self._get_editor_by_id(editor_id)
134:         if not editor:
135:             raise ValueError(f"Editor not found: {editor_id}")
136:         
137:         # Check if string exists
138:         full_content = '\n'.join(editor.content)
139:         if old_string not in full_content:
140:             raise ValueError(f"String not found in editor: {old_string[:50]}...")
141:         
142:         # Apply replacement
143:         old_content_lines = editor.content.copy()
144:         new_content_lines = [line.replace(old_string, new_string) for line in editor.content]
145:         
146:         # Track edit
147:         edit = Edit(
148:             timestamp=time.time(),
149:             operation='replace',
150:             target=old_string,
151:             old_content='\n'.join(old_content_lines),
152:             new_content='\n'.join(new_content_lines)
153:         )
154:         
155:         editor.edits.append(edit)
156:         editor.content = new_content_lines
157:         
158:         # Write to disk immediately
159:         self._write_to_disk(editor)
160:         self.save_state()
161:         
162:         self._add_notification(f"✓ editor.replace() → {editor.file_path.name} (string replaced)")
163:         logger.info(f"Replaced in {editor.file_path}: {old_string[:30]}... → {new_string[:30]}...")
164:         return True
165:     
166:     def insert(self, editor_id: str, before_line: int, content: str) -> bool:
167:         """
168:         Insert content before specified line.
169:         
170:         Args:
171:             editor_id: Editor window ID
172:             before_line: Line number to insert before (1-indexed, relative to editor view)
173:             content: Content to insert (can be multi-line string)
174:         
175:         Returns:
176:             True if successful
177:         """
178:         editor = self._get_editor_by_id(editor_id)
179:         if not editor:
180:             raise ValueError(f"Editor not found: {editor_id}")
181:         
182:         # Validate line number
183:         if before_line < editor.line_start or before_line > editor.line_end + 1:
184:             raise ValueError(f"Line {before_line} out of range ({editor.line_start}-{editor.line_end})")
185:         
186:         # Convert to array index
187:         insert_idx = before_line - editor.line_start
188:         
189:         # Store old content
190:         old_content_lines = editor.content.copy()
191:         
192:         # Split content into lines and insert
193:         insert_lines = content.split('\n')
194:         editor.content[insert_idx:insert_idx] = insert_lines
195:         
196:         # Update line_end to reflect new content
197:         editor.line_end += len(insert_lines)
198:         
199:         # Track edit
200:         edit = Edit(
201:             timestamp=time.time(),
202:             operation='insert',
203:             target=f"before line {before_line}",
204:             old_content='\n'.join(old_content_lines),
205:             new_content='\n'.join(editor.content)
206:         )
207:         editor.edits.append(edit)
208:         
209:         # Write to disk and save state
210:         self._write_to_disk(editor)
211:         self.save_state()
212:         
213:         self._add_notification(f"✓ editor.insert() → {editor.file_path.name} ({len(insert_lines)} lines inserted)")
214:         logger.info(f"Inserted {len(insert_lines)} lines before line {before_line} in {editor.file_path}")
215:         return True
216:     
217:     def delete(self, editor_id: str, line_start: int, line_end: int) -> bool:
218:         """
219:         Delete line range.
220:         
221:         Args:
222:             editor_id: Editor window ID
223:             line_start: Start line (1-indexed, relative to editor view)
224:             line_end: End line (inclusive)
225:         
226:         Returns:
227:             True if successful
228:         """
229:         editor = self._get_editor_by_id(editor_id)
230:         if not editor:
231:             raise ValueError(f"Editor not found: {editor_id}")
232:         
233:         # Validate line numbers
234:         if line_start < editor.line_start or line_end > editor.line_end:
235:             raise ValueError(f"Lines {line_start}-{line_end} out of range ({editor.line_start}-{editor.line_end})")
236:         if line_start > line_end:
237:             raise ValueError(f"Invalid range: {line_start} > {line_end}")
238:         
239:         # Convert to array indices
240:         start_idx = line_start - editor.line_start
241:         end_idx = line_end - editor.line_start + 1  # +1 because end is inclusive
242:         
243:         # Store old content
244:         old_content_lines = editor.content.copy()
245:         
246:         # Delete lines
247:         lines_deleted = end_idx - start_idx
248:         del editor.content[start_idx:end_idx]
249:         
250:         # Update line_end to reflect deletion
251:         editor.line_end -= lines_deleted
252:         
253:         # Track edit
254:         edit = Edit(
255:             timestamp=time.time(),
256:             operation='delete',
257:             target=f"lines {line_start}-{line_end}",
258:             old_content='\n'.join(old_content_lines),
259:             new_content='\n'.join(editor.content)
260:         )
261:         editor.edits.append(edit)
262:         
263:         # Write to disk and save state
264:         self._write_to_disk(editor)
265:         self.save_state()
266:         
267:         self._add_notification(f"✓ editor.delete() → {editor.file_path.name} ({lines_deleted} lines deleted)")
268:         logger.info(f"Deleted lines {line_start}-{line_end} from {editor.file_path}")
269:         return True
270:     
271:     def replace_lines(self, editor_id: str, line_start: int, line_end: int, content: str) -> bool:
272:         """
273:         Replace line range with new content.
274:         
275:         Args:
276:             editor_id: Editor window ID
277:             line_start: Start line (1-indexed, relative to editor view)
278:             line_end: End line (inclusive)
279:             content: New content (can be multi-line string)
280:         
281:         Returns:
282:             True if successful
283:         """
284:         editor = self._get_editor_by_id(editor_id)
285:         if not editor:
286:             raise ValueError(f"Editor not found: {editor_id}")
287:         
288:         # Validate line numbers
289:         if line_start < editor.line_start or line_end > editor.line_end:
290:             raise ValueError(f"Lines {line_start}-{line_end} out of range ({editor.line_start}-{editor.line_end})")
291:         if line_start > line_end:
292:             raise ValueError(f"Invalid range: {line_start} > {line_end}")
293:         
294:         # Convert to array indices
295:         start_idx = line_start - editor.line_start
296:         end_idx = line_end - editor.line_start + 1  # +1 because end is inclusive
297:         
298:         # Store old content
299:         old_content_lines = editor.content.copy()
300:         
301:         # Split new content and replace
302:         new_lines = content.split('\n')
303:         lines_removed = end_idx - start_idx
304:         editor.content[start_idx:end_idx] = new_lines
305:         
306:         # Update line_end to reflect change
307:         editor.line_end = editor.line_end - lines_removed + len(new_lines)
308:         
309:         # Track edit
310:         edit = Edit(
311:             timestamp=time.time(),
312:             operation='replace_lines',
313:             target=f"lines {line_start}-{line_end}",
314:             old_content='\n'.join(old_content_lines),
315:             new_content='\n'.join(editor.content)
316:         )
317:         editor.edits.append(edit)
318:         
319:         # Write to disk and save state
320:         self._write_to_disk(editor)
321:         self.save_state()
322:         
323:         self._add_notification(f"✓ editor.replace_lines() → {editor.file_path.name} ({len(new_lines)} lines replaced)")
324:         logger.info(f"Replaced lines {line_start}-{line_end} in {editor.file_path}")
325:         return True
326:     
327:     def split(self, editor_id: str, line_start: int, line_end: int) -> str:
328:         """
329:         Create split view of editor.
330:         
331:         Args:
332:             editor_id: Parent editor window ID
333:             line_start: Start line for split (1-indexed, relative to editor view)
334:             line_end: End line for split (inclusive)
335:         
336:         Returns:
337:             split_id
338:         """
339:         editor = self._get_editor_by_id(editor_id)
340:         if not editor:
341:             raise ValueError(f"Editor not found: {editor_id}")
342:         
343:         # Validate line numbers
344:         if line_start < editor.line_start or line_end > editor.line_end:
345:             raise ValueError(f"Lines {line_start}-{line_end} out of range ({editor.line_start}-{editor.line_end})")
346:         if line_start > line_end:
347:             raise ValueError(f"Invalid range: {line_start} > {line_end}")
348:         
349:         # Import Split from editor_window
350:         from nisaba.tui.editor_window import Split
351:         
352:         # Create split
353:         split = Split(
354:             parent_id=editor.id,
355:             line_start=line_start,
356:             line_end=line_end
357:         )
358:         
359:         editor.splits[split.id] = split
360:         self.save_state()
361:         
362:         logger.info(f"Created split {split.id} for {editor.file_path} lines {line_start}-{line_end}")
363:         return split.id
364:     
365:     def resize(self, window_id: str, line_start: int, line_end: int) -> bool:
366:         """
367:         Resize editor or split window.
368:         
369:         Args:
370:             window_id: Editor ID or split ID
371:             line_start: New start line
372:             line_end: New end line
373:         
374:         Returns:
375:             True if successful
376:         """
377:         # Try editor first
378:         editor = self._get_editor_by_id(window_id)
379:         if editor:
380:             # Resizing editor
381:             if line_start < 1:
382:                 raise ValueError(f"Invalid line_start: {line_start}")
383:             
384:             editor.line_start = line_start
385:             editor.line_end = line_end
386:             self.save_state()
387:             logger.info(f"Resized editor {window_id} to lines {line_start}-{line_end}")
388:             return True
389:         
390:         # Try split
391:         for editor in self.editors.values():
392:             if window_id in editor.splits:
393:                 split = editor.splits[window_id]
394:                 
395:                 # Validate against editor bounds
396:                 if line_start < editor.line_start or line_end > editor.line_end:
397:                     raise ValueError(f"Lines {line_start}-{line_end} out of range ({editor.line_start}-{editor.line_end})")
398:                 
399:                 split.line_start = line_start
400:                 split.line_end = line_end
401:                 self.save_state()
402:                 logger.info(f"Resized split {window_id} to lines {line_start}-{line_end}")
403:                 return True
404:         
405:         raise ValueError(f"Window not found: {window_id}")
406:     
407:     def close_split(self, split_id: str) -> bool:
408:         """
409:         Close split view.
410:         
411:         Args:
412:             split_id: Split ID
413:         
414:         Returns:
415:             True if successful
416:         """
417:         for editor in self.editors.values():
418:             if split_id in editor.splits:
419:                 del editor.splits[split_id]
420:                 self.save_state()
421:                 logger.info(f"Closed split {split_id}")
422:                 return True
423:         
424:         return False
425:     
426:     def refresh_all(self) -> List[str]:
427:         """
428:         Check for external file changes and reload if needed.
429:         
430:         Returns:
431:             List of notification messages
432:         """
433:         notifications = []
434:         
435:         for editor in self.editors.values():
436:             if not editor.file_path.exists():
437:                 notifications.append(f"⚠ File deleted: {editor.file_path}")
438:                 continue
439:             
440:             current_mtime = editor.file_path.stat().st_mtime
441:             
442:             if current_mtime != editor.last_mtime:
443:                 # File changed externally
444:                 if editor.is_dirty:
445:                     # Conflict: dirty editor + external change
446:                     notifications.append(f"⚠ Conflict: {editor.file_path} modified externally with unsaved edits")
447:                 else:
448:                     # Clean reload
449:                     try:
450:                         content = editor.file_path.read_text().splitlines()
451:                         # Adjust to current view range
452:                         if editor.line_end == -1 or editor.line_end > len(content):
453:                             editor.line_end = len(content)
454:                         
455:                         editor.content = content[editor.line_start-1:editor.line_end]
456:                         editor.original_content = editor.content.copy()
457:                         editor.last_mtime = current_mtime
458:                         self.save_state()
459:                         
460:                         notifications.append(f"🔄 Reloaded: {editor.file_path}")
461:                     except Exception as e:
462:                         notifications.append(f"✗ Failed to reload {editor.file_path}: {e}")
463:         
464:         return notifications
465:     
466:     def _add_notification(self, message: str) -> None:
467:         """
468:         Add notification to notifications file.
469:         
470:         Args:
471:             message: Notification message
472:         """
473:         notifications_file = Path(".nisaba/notifications.md")
474:         
475:         # Read existing notifications
476:         if notifications_file.exists():
477:             content = notifications_file.read_text()
478:             lines = content.splitlines()
479:             
480:             # Keep only "Recent activity:" header and existing notifications
481:             if lines and lines[0] == "Recent activity:":
482:                 existing = lines[1:]
483:             else:
484:                 existing = []
485:         else:
486:             existing = []
487:         
488:         # Add new notification at top
489:         new_notifications = [message] + existing
490:         
491:         # Keep last 10 notifications
492:         new_notifications = new_notifications[:10]
493:         
494:         # Write back
495:         content = "Recent activity:\\n" + "\\n".join(new_notifications) + "\\n"
496:         notifications_file.write_text(content)
497:     
498:     def close(self, editor_id: str) -> bool:
499:         """
500:         Close editor window.
501:         
502:         Args:
503:             editor_id: Editor window ID
504:         
505:         Returns:
506:             True if successful
507:         """
508:         editor = self._get_editor_by_id(editor_id)
509:         if not editor:
510:             return False
511:         
512:         del self.editors[editor.file_path]
513:         self.save_state()
514:         
515:         logger.info(f"Closed editor: {editor.file_path}")
516:         return True
517:     
518:     def close_all(self) -> None:
519:         """Close all editor windows."""
520:         self.editors.clear()
521:         self.save_state()
522:         logger.info("Closed all editors")
523:     
524:     def status(self) -> Dict[str, Any]:
525:         """
526:         Get status summary.
527:         
528:         Returns:
529:             Dict with editor count, total lines, and editor list
530:         """
531:         total_lines = sum(len(editor.content) for editor in self.editors.values())
532:         
533:         return {
534:             "editor_count": len(self.editors),
535:             "total_lines": total_lines,
536:             "editors": [
537:                 {
538:                     "id": editor.id,
539:                     "file": str(editor.file_path),
540:                     "lines": f"{editor.line_start}-{editor.line_end}",
541:                     "line_count": len(editor.content),
542:                     "edits": len(editor.edits),
543:                     "dirty": editor.is_dirty
544:                 }
545:                 for editor in self.editors.values()
546:             ]
547:         }
548:     
549:     def render(self) -> str:
550:         """
551:         Render all editors and splits to markdown with diff markers.
552:         
553:         Returns:
554:             Markdown string
555:         """
556:         # Check for external changes first
557:         refresh_notifications = self.refresh_all()
558:         for notif in refresh_notifications:
559:             self._add_notification(notif)
560:         
561:         if not self.editors:
562:             return ""
563:         
564:         lines = []
565:         
566:         for editor in self.editors.values():
567:             # Render main editor
568:             lines.append(f"---EDITOR_{editor.id}")
569:             lines.append(f"**file**: {editor.file_path}")
570:             lines.append(f"**lines**: {editor.line_start}-{editor.line_end} ({len(editor.content)} lines)")
571:             
572:             if editor.splits:
573:                 lines.append(f"**splits**: {len(editor.splits)}")
574:             
575:             if editor.is_dirty:
576:                 lines.append(f"**status**: modified ✎")
577:                 lines.append(f"**edits**: {len(editor.edits)} (last: {self._format_time_ago(editor.edits[-1].timestamp)})")
578:             
579:             lines.append("")
580:             
581:             # Render content with diff markers if modified
582:             if editor.is_dirty:
583:                 diff_lines = self._generate_inline_diff(editor)
584:                 lines.extend(diff_lines)
585:             else:
586:                 for i, line in enumerate(editor.content):
587:                     line_num = editor.line_start + i
588:                     lines.append(f"{line_num}: {line}")
589:             
590:             lines.append(f"---EDITOR_{editor.id}_END")
591:             lines.append("")
592:             
593:             # Render splits
594:             for split in editor.splits.values():
595:                 lines.append(f"---EDITOR_SPLIT_{split.id}")
596:                 lines.append(f"**parent**: {split.parent_id}")
597:                 lines.append(f"**file**: {editor.file_path}")
598:                 lines.append(f"**lines**: {split.line_start}-{split.line_end}")
599:                 lines.append("")
600:                 
601:                 # Get content slice from editor
602:                 start_idx = split.line_start - editor.line_start
603:                 end_idx = split.line_end - editor.line_start + 1
604:                 split_content = editor.content[start_idx:end_idx]
605:                 
606:                 for i, line in enumerate(split_content):
607:                     line_num = split.line_start + i
608:                     lines.append(f"{line_num}: {line}")
609:                 
610:                 lines.append(f"---EDITOR_SPLIT_{split.id}_END")
611:                 lines.append("")
612:         
613:         return '\n'.join(lines)
614:     
615:     def save_state(self) -> None:
616:         """Save editor state to JSON."""
617:         state = {
618:             "editors": {
619:                 str(file_path): editor.to_dict()
620:                 for file_path, editor in self.editors.items()
621:             }
622:         }
623:         
624:         self.state_file.parent.mkdir(parents=True, exist_ok=True)
625:         self.state_file.write_text(json.dumps(state, indent=2), encoding='utf-8')
626:         logger.debug(f"Saved {len(self.editors)} editors to state file")
627:     
628:     def load_state(self) -> None:
629:         """Restore editors from JSON."""
630:         if not self.state_file.exists():
631:             logger.debug("No state file found, starting with empty editors")
632:             return
633:         
634:         try:
635:             state = json.loads(self.state_file.read_text(encoding='utf-8'))
636:             
637:             for file_path_str, editor_data in state.get("editors", {}).items():
638:                 file_path = Path(file_path_str)
639:                 
640:                 # Re-read content from file (handles external changes)
641:                 try:
642:                     with open(file_path, 'r', encoding='utf-8') as f:
643:                         all_lines = f.readlines()
644:                     
645:                     all_lines = [line.rstrip('\n') for line in all_lines]
646:                     
647:                     # Extract range
648:                     start = editor_data["line_start"]
649:                     end = editor_data["line_end"]
650:                     
651:                     if end == -1 or end > len(all_lines):
652:                         content = all_lines[start-1:]
653:                     else:
654:                         content = all_lines[start-1:end]
655:                     
656:                     # Restore editor
657:                     editor = EditorWindow.from_dict(editor_data, content)
658:                     self.editors[file_path] = editor
659:                     
660:                 except Exception as e:
661:                     logger.warning(f"Skipping editor {file_path}: {e}")
662:                     continue
663:             
664:             logger.info(f"Restored {len(self.editors)} editors from state file")
665:         except Exception as e:
666:             logger.warning(f"Failed to load state file: {e}")
667:     
668:     def _get_editor_by_id(self, editor_id: str) -> Optional[EditorWindow]:
669:         """Find editor by ID."""
670:         for editor in self.editors.values():
671:             if editor.id == editor_id:
672:                 return editor
673:         return None
674:     
675:     def _write_to_disk(self, editor: EditorWindow) -> None:
676:         """Write editor content back to file."""
677:         try:
678:             # Read full file
679:             with open(editor.file_path, 'r', encoding='utf-8') as f:
680:                 all_lines = f.readlines()
681:             
682:             all_lines = [line.rstrip('\n') for line in all_lines]
683:             
684:             # Replace the range
685:             start_idx = editor.line_start - 1
686:             end_idx = editor.line_end
687:             
688:             new_lines = (
689:                 all_lines[:start_idx] +
690:                 editor.content +
691:                 all_lines[end_idx:]
692:             )
693:             
694:             # Write back
695:             editor.file_path.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
696:             
697:             # Update mtime
698:             editor.last_mtime = editor.file_path.stat().st_mtime
699:             
700:         except Exception as e:
701:             logger.error(f"Failed to write {editor.file_path}: {e}", exc_info=True)
702:             raise
703:     
704:     def _generate_inline_diff(self, editor: EditorWindow) -> List[str]:
705:         """Generate diff with +/- markers inline."""
706:         diff = difflib.ndiff(editor.original_content, editor.content)
707:         
708:         lines = []
709:         line_num = editor.line_start
710:         
711:         for d in diff:
712:             prefix = d[0]
713:             content = d[2:]
714:             
715:             if prefix == ' ':  # Unchanged
716:                 lines.append(f"{line_num}: {content}")
717:                 line_num += 1
718:             elif prefix == '-':  # Removed
719:                 lines.append(f"{line_num}: -{content}")
720:             elif prefix == '+':  # Added
721:                 lines.append(f"{line_num}: +{content}")
722:                 line_num += 1
723:         
724:         return lines
725:     
726:     def _format_time_ago(self, timestamp: float) -> str:
727:         """Format timestamp as relative time."""
728:         seconds = time.time() - timestamp
729:         
730:         if seconds < 60:
731:             return f"{int(seconds)}s ago"
732:         elif seconds < 3600:
733:             return f"{int(seconds / 60)}m ago"
734:         elif seconds < 86400:
735:             return f"{int(seconds / 3600)}h ago"
736:         else:
737:             return f"{int(seconds / 86400)}d ago"
---TOOL_RESULT_WINDOW_80077eb4-8377-4b1b-bd11-751cb5f816ef_END

---TOOL_RESULT_WINDOW_05ec80e5-59b7-4598-873a-2a74670d091d
**type**: read_result
**file**: src/nisaba/tui/editor_window.py
**lines**: 1-107
**total_lines**: 107

1: """Editor window dataclasses for persistent code editing."""
2: 
3: import time
4: from dataclasses import dataclass, field
5: from pathlib import Path
6: from typing import List, Any, Dict
7: from uuid import uuid4
8: 
9: 
10: @dataclass
11: class Edit:
12:     """Record of a single edit operation."""
13:     timestamp: float
14:     operation: str  # 'replace', 'replace_lines', 'insert', 'delete'
15:     target: str  # old string or line range description
16:     old_content: str
17:     new_content: str
18: 
19: 
20: 
21: @dataclass
22: class Split:
23:     """Split view of an editor window."""
24:     id: str = field(default_factory=lambda: str(uuid4()))
25:     parent_id: str = ""
26:     line_start: int = 1
27:     line_end: int = 1
28:     opened_at: float = field(default_factory=lambda: time.time())
29:     
30:     def to_dict(self) -> Dict[str, Any]:
31:         """Serialize for JSON."""
32:         return {
33:             "id": self.id,
34:             "parent_id": self.parent_id,
35:             "line_start": self.line_start,
36:             "line_end": self.line_end,
37:             "opened_at": self.opened_at
38:         }
39:     
40:     @classmethod
41:     def from_dict(cls, data: Dict[str, Any]) -> "Split":
42:         """Restore from JSON."""
43:         return cls(
44:             id=data["id"],
45:             parent_id=data["parent_id"],
46:             line_start=data["line_start"],
47:             line_end=data["line_end"],
48:             opened_at=data.get("opened_at", time.time())
49:         )
50: 
51: 
52: @dataclass
53: class EditorWindow:
54:     """
55:     Represents an open editor window with change tracking.
56:     
57:     One editor per file - no duplicates allowed.
58:     """
59:     id: str = field(default_factory=lambda: str(uuid4()))
60:     file_path: Path = field(default_factory=Path)
61:     line_start: int = 1
62:     line_end: int = -1
63:     content: List[str] = field(default_factory=list)
64:     original_content: List[str] = field(default_factory=list)
65:     edits: List[Edit] = field(default_factory=list)
66:     splits: Dict[str, Split] = field(default_factory=dict)
67:     last_mtime: float = 0.0
68:     opened_at: float = field(default_factory=lambda: time.time())
69:     
70:     @property
71:     def is_dirty(self) -> bool:
72:         """Check if editor has unsaved changes."""
73:         return len(self.edits) > 0
74:     
75:     def to_dict(self) -> Dict[str, Any]:
76:         """Serialize for JSON persistence."""
77:         return {
78:             "id": self.id,
79:             "file_path": str(self.file_path),
80:             "line_start": self.line_start,
81:             "line_end": self.line_end,
82:             "opened_at": self.opened_at,
83:             "last_mtime": self.last_mtime,
84:             "edit_count": len(self.edits),
85:             "splits": {sid: split.to_dict() for sid, split in self.splits.items()}
86:         }
87:     
88:     @classmethod
89:     def from_dict(cls, data: Dict[str, Any], content: List[str]) -> "EditorWindow":
90:         """Restore from JSON (content re-read from file)."""
91:         # Restore splits
92:         splits = {}
93:         for sid, split_data in data.get("splits", {}).items():
94:             splits[sid] = Split.from_dict(split_data)
95:         
96:         return cls(
97:             id=data["id"],
98:             file_path=Path(data["file_path"]),
99:             line_start=data["line_start"],
100:             line_end=data["line_end"],
101:             content=content,
102:             original_content=content.copy(),
103:             edits=[],  # Fresh start on reload
104:             splits=splits,
105:             last_mtime=data.get("last_mtime", 0.0),
106:             opened_at=data.get("opened_at", time.time())
107:         )
---TOOL_RESULT_WINDOW_05ec80e5-59b7-4598-873a-2a74670d091d_END
