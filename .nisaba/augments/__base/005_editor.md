# Compressed Editor Operations

**Core:** Unified file editing with persistent visibility, change tracking, and spatial workspace integration.

---

## Fundamental Shift

```
Old (procedural):
  nisaba_read(file) → analyze → nisaba_edit(file, old, new) → nisaba_read(file) # verify?
  
New (spatial):
  editor.open(file) → visible in workspace → editor.replace(id, old, new) → diff visible inline
  
Editor ≡ persistent viewport + change tracking + immediate commit
```

---

## State Model

```
EditorWindow:
  id: str (UUID)
  file_path: Path
  line_start, line_end: int  # View range
  content: List[str]         # Current state
  original_content: List[str] # For diffing
  edits: List[Edit]          # Change history
  last_mtime: float          # File modification time
  
Edit:
  timestamp: float
  operation: str  # 'replace'
  target: str     # old string
  old_content, new_content: str

Constraint: editors: Dict[Path, EditorWindow]  # ONE per file!
```

---

## Operations

```
editor(operation, **params) → result

open(file, line_start=1, line_end=-1) → editor_id
  - If already open → return existing editor_id (no duplicates!)
  - Else: read file, create EditorWindow, render
  
write(file, content) → editor_id
  - Write to disk, open editor, mark as clean
  
replace(editor_id, old_string, new_string) → success
  - Find editor by id
  - Apply replacement to content
  - Create Edit record
  - Write to disk immediately
  - Render with diff markers
  
close(editor_id) → success
  - Remove editor from collection
  
close_all() → success
  - Clear all editors
  
status() → {editor_count, total_lines, editors[]}
  - Summary of open editors
```

---

## Rendering

```
---EDITOR_{uuid}
**file**: path/to/file.py
**lines**: 10-50 (41 lines)
**status**: modified ✎
**edits**: 2 (last: 3s ago)

10: def example():
11: -    old_code = True
11: +    new_code = True  # Changed
12:     return value
---EDITOR_{uuid}_END
```

**Diff markers (via difflib.ndiff):**
- `  ` = unchanged line
- `- ` = removed line
- `+ ` = added line

**Clean files:** No diff markers, just line numbers + content

---

## Integration Flow

```
1. Tool call: editor(operation="replace", editor_id=X, old=A, new=B)
   
2. EditorManager:
   ├─ Find editor by id
   ├─ Apply replacement to content
   ├─ Track Edit(timestamp, operation, old, new)
   ├─ Write to disk immediately
   └─ save_state() → .nisaba/editor_state.json

3. Tool renders:
   ├─ manager.render() → markdown with diffs
   └─ Write .nisaba/editor_windows.md
      # File mtime changes!

4. Tool returns: {"success": true, "message": "...", "nisaba": true}

5. Next request:
   ├─ Proxy detects mtime change
   ├─ editor_windows_cache.load() → reload
   └─ Inject into system prompt

6. Claude sees: EDITOR_WINDOWS section with diff markers
```

---

## Key Design Principles

**No Duplicate Editors:**
- `Dict[Path, EditorWindow]` ensures one editor per file
- `open()` returns existing editor_id if file already open
- Prevents token waste, confusion

**Immediate Commit:**
- Every `replace()` writes to disk immediately
- Simpler mental model (no staging)
- Edit history tracked for potential undo

**Change Visibility:**
- Diffs rendered inline with +/- markers
- Edit count + last edit timestamp
- Dirty flag (modified ✎)

**Spatial Persistence:**
- Editors persist across turns (JSON state)
- Visible in system prompt (not buried in messages)
- Can reference multiple editors simultaneously

---

## Usage Patterns

### Pattern 1: Read and Modify
```python
# Open file
editor(operation="open", file="src/example.py", line_start=1, line_end=50)
# Returns: {editor_id: "abc123"}
# EDITOR_WINDOWS section now shows lines 1-50

# Modify
editor(operation="replace", editor_id="abc123", 
       old_string="old_function", new_string="new_function")
# Diff markers appear inline, file written to disk

# Already visible - no re-read needed!
```

### Pattern 2: Create New File
```python
editor(operation="write", file="src/new_module.py", 
       content="# New module\n\ndef hello():\n    pass\n")
# File created, editor opened, visible in workspace
```

### Pattern 3: Multiple Files
```python
editor(operation="open", file="src/client.py")
editor(operation="open", file="src/server.py")
# Both visible simultaneously in EDITOR_WINDOWS
# Compare implementations side-by-side
```

### Pattern 4: Check Status
```python
editor(operation="status")
# Returns: {
#   editor_count: 3,
#   total_lines: 150,
#   editors: [{id, file, lines, edits, dirty}, ...]
# }
```

### Pattern 5: Cleanup
```python
editor(operation="close", editor_id="abc123")  # Close one
editor(operation="close_all")                   # Close all
```

---

## Decision Tree

```
Want to read file?
└─ editor.open(file, start, end) → persistent visibility

Want to create file?
└─ editor.write(file, content) → creates + opens

Want to modify file?
├─ Already open? → editor.replace(id, old, new)
└─ Not open? → editor.open(file) first, then replace

Want to verify changes?
└─ Already visible! Check diff markers in EDITOR_WINDOWS

Want to compare files?
└─ Open multiple editors, all visible simultaneously

Want to clean up?
├─ Single file? → editor.close(id)
└─ All files? → editor.close_all()
```

---

## Comparison to Old Tools

| Aspect | Old (nisaba_read/write/edit) | New (editor) |
|--------|------------------------------|--------------|
| **Paradigm** | Procedural commands | Spatial workspace |
| **Visibility** | Transient tool results | Persistent editor windows |
| **Verification** | Re-read after edit | Inline diff markers |
| **Change tracking** | None | Edit history + timestamps |
| **Duplicates** | Multiple reads create clutter | One editor per file |
| **Mental model** | Sequential operations | Open viewport |

---

## Quick Reference

```
Read file:
  editor(operation="open", file="path/to/file", line_start=1, line_end=-1)
  
Create file:
  editor(operation="write", file="path/to/file", content="...")
  
Modify file:
  editor(operation="replace", editor_id="...", old_string="...", new_string="...")
  
Check status:
  editor(operation="status")
  
Close:
  editor(operation="close", editor_id="...")
  editor(operation="close_all")
  
No duplicates:
  editor.open(same_file) → returns existing editor_id
```

---

## Core Insights

```
Visibility > Ephemeral
  Editors persist, changes visible inline

Spatial > Sequential
  Open viewport, not transient command

Immediate > Staged
  Commit to disk instantly, simple mental model

Unified > Fragmented
  One tool for read/write/edit, not three

Tracked > Forgotten
  Edit history preserved, change awareness

Persistent > Disposable
  State survives across turns (JSON + mtime)
```

---

**Replaces:** `nisaba_read`, `nisaba_write`, `nisaba_edit`

**Integration:** `.nisaba/editor_windows.md` → proxy → `---EDITOR_WINDOWS` section

**Pattern:** Open → visible → modify → diff → persist 🖤

---

**REQUIRES:** __base/002_compressed_environment_mechanics

**ENABLES:** Unified file operations, spatial code editing, change visibility
