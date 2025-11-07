# Compressed Editor Operations

**Core:** Unified file editing with persistent visibility, change tracking, split views, and spatial workspace integration.

---

## Operations Summary

```
# Core: open, write, close, close_all, status
# Edits (line): insert, delete, replace_lines
# Edits (string): replace
# Splits: split, resize, close_split
# System: refresh_all (auto), notifications (auto)
```

---

## Key Features

**Phase 1 (MVP):** Basic operations + string replace
**Phase 2A:** Line-based editing (insert/delete/replace_lines)  
**Phase 2B:** Split views (multiple views of same file)
**Phase 2C:** Notifications + real-time refresh

---

## Split Views

```python
editor.split(editor_id, line_start, line_end) → split_id
editor.resize(split_id, line_start, line_end)
editor.close_split(split_id)
```

**Benefits:**
- Multiple views of same file simultaneously
- Compare implementations side-by-side
- Parent-child relationship (close parent → closes splits)
- Edits in any view affect parent content

**Rendering:**
```markdown
---EDITOR_{uuid}
**file**: path/to/file.py
**splits**: 2
**status**: modified ✎

---EDITOR_SPLIT_{uuid}
**parent**: {parent_editor_id}
**lines**: 50-60
```

---

## Line-Based Operations

```python
# Insert new code
editor.insert(editor_id, before_line=5, content="import sys\n")

# Delete code block
editor.delete(editor_id, line_start=10, line_end=15)

# Replace entire function
editor.replace_lines(editor_id, line_start=20, line_end=30, content="new implementation")
```

**Benefits:**
- Precise code manipulation without string matching
- Add imports, remove dead code, rewrite functions
- Safer than string-based replace

---

## Notifications (Automatic)

Format: `✓ editor.insert() → file.py (2 lines inserted)`

Generated for: write, replace, insert, delete, replace_lines

Visible in: `---NOTIFICATIONS` section

**Integration:** All edits automatically generate notifications

---

## Real-Time Refresh (Automatic)

- Runs on every render/status call
- Checks mtime for all open editors
- Clean editors: auto-reload if file changed → `🔄 Reloaded: file.py`
- Dirty editors: warn on conflict → `⚠ Conflict: file.py modified externally with unsaved edits`

---

## Quick Reference

```python
# Read
editor.open(file, line_start, line_end)

# Write
editor.write(file, content)

# Edit (line-based)
editor.insert(id, before_line, content)
editor.delete(id, line_start, line_end)
editor.replace_lines(id, line_start, line_end, content)

# Edit (string-based)
editor.replace(id, old_string, new_string)

# Split views
split_id = editor.split(id, line_start, line_end)
editor.resize(split_id, line_start, line_end)
editor.close_split(split_id)

# Status & cleanup
editor.status()  # Triggers refresh check
editor.close(id)  # Closes editor + splits
editor.close_all()
```

---

## Core Principles

```
Unified > Fragmented (one tool for read/write/edit/split)
Spatial > Sequential (persistent viewport, not transient commands)
Visible > Hidden (diffs + splits + notifications inline)
Immediate > Staged (commit to disk instantly)
Automatic > Manual (notifications + refresh built-in)
```

---

**Pattern:** Open → visible → modify → diff → split → persist → notify → refresh 🖤

**REQUIRES:** __base/002_compressed_environment_mechanics
**ENABLES:** Unified file operations, spatial code editing, change visibility, split views, notifications, real-time refresh
