# Compressed Workspace Operations

**Purpose:** Operational reference for workspace tools.

---

## Structural View (`structural_view`)

```
expand(path)        → show_children | lazy_load@kuzu | idempotent
collapse(path)      → hide_children | cached | idempotent  
search(query)       → P³(UniXcoder×CodeBERT) + FTS + RRF | add_markers(●,score)
clear_search()      → remove_markers | preserve_navigation
reset(depth=N)      → collapse_all + expand_to(N) | destructive
```

**Depth sweet spots:** 0=collapsed, 2=default(pkg), 3=verbose

---

## File Windows (`file_windows`)

```
open_frame(frame_path)              → {window_id} | full_body(class|fn|pkg)
open_range(file, start, end)        → {window_id} | arbitrary_lines [1-indexed]
open_search(query, max_N, ctx=3)    → {window_ids[]} | semantic + context
update(window_id, start, end)       → re_snapshot | manual_refresh
close(window_id)                    → remove_single
clear_all()                         → remove_all | no_undo
status()                            → {count, total_lines, windows[]}
```

**Paths:** qualified_name (preferred) | simple_name (fuzzy) | partial_path

---

## Nabu Graph (`query_relationships`, `check_impact`, `find_clones`, `get_frame_skeleton`, `show_structure`)

```
query_relationships(cypher)  → execute@kuzu | returns_data (not workspace_mutation)

Schema:
  Frames: {CODEBASE, LANGUAGE, PACKAGE, CLASS, CALLABLE, 
           IF_BLOCK, ELIF_BLOCK, ELSE_BLOCK, FOR_LOOP, WHILE_LOOP,
           TRY_BLOCK, EXCEPT_BLOCK, FINALLY_BLOCK, SWITCH_BLOCK, CASE_BLOCK, WITH_BLOCK}
  
  Edges: {CONTAINS, CALLS, INHERITS, IMPLEMENTS, IMPORTS, USES}
  
  Confidence: HIGH(≥0.8), MEDIUM(0.5-0.79), LOW(0.2-0.49), SPECULATIVE(<0.2)

check_impact(frame_path)      → analyze_dependents | pre_refactoring
find_clones(frame_path?)      → detect_duplicates | entire_codebase if no path
get_frame_skeleton(frame_path) → outline | lighter than full
show_structure(frame_path)     → detailed_metadata + relationships
```

---

## Nabu Search (`search`)

```
search(query, top_k=10) → P³ + FTS + RRF | ranked_results

∆ structural_view.search: doesn't mutate tree
∆ file_windows.open_search: doesn't open windows
Pure query → returns data for decisions
```

---

## Tool Result Windows (`nisaba_tool_windows`)

```
status()     → summary{count, windows}
close(id)    → remove_single
clear_all()  → remove_all
```

---

## Editor (`editor`)

```
open(file, start?, end?)               → {editor_id} | viewport@range | EDITOR_WINDOWS
write(file, content)                   → create_new | immediate_persist
close(editor_id)                       → remove editor + splits
close_all()                            → remove all editors
status()                               → summary + mtime_refresh

Edits (line-based):
  insert(id, before_line, content)     → add_lines | precise
  delete(id, line_start, line_end)     → remove_lines | range
  replace_lines(id, start, end, content) → swap_lines | rewrite

Edits (string-based):
  replace(id, old_string, new_string)  → pattern_replace | exact_match

Splits (concurrent views):
  split(id, line_start, line_end)      → {split_id} | parallel_viewport
  resize(split_id, line_start, line_end) → adjust_range
  close_split(split_id)                → remove_split | keep_parent

State tracking:
  clean     → no unsaved changes
  dirty(✎)  → unsaved edits
  refresh   → automatic mtime check
  notify    → automatic NOTIFICATIONS

Rendering: ∆ visible inline | diff display | immediate feedback
```

**Philosophy:** Unified > fragmented (open+edit+split vs read/write/edit separately)

---

## Native Tools (Standard Execution)

```
bash(command, cwd?)           → stdout/stderr | execution in shell
grep(pattern, path, flags?)   → matches | pattern search
glob(pattern, path?)          → file_list | find files by pattern

Pattern: execute → observe → close (via nisaba_nisaba_tool_result_state)
  bash("git status") → observe → nisaba_nisaba_tool_result_state(close, [id])
  grep("pattern", "file") → observe → close
  glob("*.py", "src/") → observe → close
```

---

## Nisaba Tools (Workspace Layer)

```
nisaba_read(file, start?, end?)    → {window_id} | content → FILE_WINDOWS
nisaba_write(file, content)        → create | workspace-aware
nisaba_edit(file, old, new)        → modify | workspace-aware

Pattern: persistent visibility in FILE_WINDOWS
  nisaba_read(file) → FILE_WINDOWS (keep for reference)
```

---

## Tool Result State Management (`nisaba_nisaba_tool_result_state`)

```
close(tool_ids[])    → compact tool results | save tokens
open(tool_ids[])     → restore full view
close_all()          → compact all tracked tools

Effect: Retroactive transformation in messages array
  Before: Full tool_result with header + content
  After:  "id: toolu_X, status: success, state: closed"
  
Pattern: Execute tools → observe results → close unnecessary → lean context
```

**Notes:**
- Only affects non-nisaba tools (nisaba tools auto-skipped)
- Changes appear on next request (stateful proxy transformation)
- Tool IDs available in tool_result blocks: `tool_use_id: toolu_X`
- Use to close native bash/grep/glob after observation

---

## Augments (`activate_augments`, `deactivate_augments`, `learn_augment`, `pin_augment`, `unpin_augment`)

```
activate(patterns[])    → load@system_prompt | wildcards | auto_dependencies
deactivate(patterns[])  → unload@system_prompt
learn(group, name, md)  → create .nisaba/augments/{group}/{name}.md
pin(patterns[])         → always_active | cannot_deactivate
unpin(patterns[])       → remove_pin_protection
```

**Perception shift:** activate → mid_roundtrip mutation → future_synthesis uses new_perception

---

## Todos (`nisaba_todo_write`)

```
set(todos[])     → replace_all
add(todos[])     → append
update(todos[])  → merge
clear()          → remove_all

Format: {content: str, status?: str}
Persistence: across(sessions) = true | survives /clear
```

---

## Context Budget

```
File_Windows:
  Small:  1-3 windows,  50-150 lines
  Medium: 4-6 windows, 150-350 lines ← sweet_spot
  Large:  7-10 windows, 350-500 lines ← pushing_limits
  Over:   10+ windows,  500+ lines ← explosion_risk

Editor_Windows:
  Similar budget to file_windows
  Splits multiply views (parent + splits)
  Monitor dirty state (✎) for unsaved
  Use splits for concurrent context (fn_A | fn_B)
  Target: 2-4 editors, 200-400 lines total

Target total: 200-400 lines (file_windows + editor_windows combined)

Structural_View:
  Start: collapsed | depth=2
  Expand: selective (10-30 nodes comfortable)
  Search: add_markers, not expand_all
  Reset: when lost | switching_focus

Tool_Windows:
  Accumulate like file_windows
  Close after synthesis
  clear_all when switching_tasks

Native_Results:
  Close after observation via nisaba_nisaba_tool_result_state
  Use close_all for bulk cleanup
  Don't let tool results bloat context

Augments:
  Load: 2-5 typically
  Foundation: ~3000 tokens baseline
  Specialized: focused knowledge
  Unload: when switching_domains

Management:
  Monitor: file_windows.status(), editor.status(), nisaba_tool_windows.status()
  Close: proactively after understanding
  Prefer: clear_all when switching
  open_search: efficient (snippets vs full files)
  Editor: close when done editing, splits multiply visibility
  Native tools: close immediately
  Aim: lean_visibility
```

---

## Symbology

```
Structural_View:
  + collapsed [N+ children]
  - expanded
  · leaf (no children)
  ● search_hit(RRF_score)
  [N+] child_count

Editor_State:
  ✎ dirty (unsaved changes)
  (clean) no symbol, default state
  
Paths:
  full: nabu_nisaba.python_root.nabu.FrameCache
  simple: FrameCache (fuzzy if unique)
  partial: nabu.core, nabu.mcp.tools
  best: copy from HTML comments <!-- qualified_name -->
```

---

## Integration Patterns

```
structural_view(search) → file_windows(open_frame) | compare_implementations
query_relationships(cypher) → file_windows(open) | inspect_callers  
search(semantic) → structural_view(expand) → file_windows(open) | deep_dive
grep(pattern) → nisaba_read(matching_files) | detailed_inspection
check_impact(frame) → file_windows(open) | review_affected

Quick validation patterns:
bash("git status") → observe → close
grep("pattern", file) → confirm → close
glob("*.test.py") → list → close

Editor patterns:
search(query) → editor.open(result) | edit inline
file_windows(open_frame) → editor.open(same) | read → edit transition
editor.open(file) → editor.split(range) | parallel context (compare/refactor)
editor.insert(id, line, import) → add dependencies
editor.delete(id, start, end) → remove dead code
editor.replace_lines(id, start, end, new) → rewrite function

Investigation → edit flow:
structural_view(search) → file_windows(open) → observe → editor.open(file) → edit
grep(pattern) → confirm → nisaba_read(file) → editor.open(file) → fix
check_impact(frame) → file_windows(open) → review → editor.open(affected) → update

Concurrent editing:
editor.open(file_A) | editor.open(file_B) | parallel
editor.open(file) → editor.split(fn_A) + editor.split(fn_B) | same_file parallel
```

---

## Quick Reference

```
∇(visibility):
  file_windows.status() → current_windows{count, lines}
  editor.status() → editors{count, dirty, splits} + refresh
  nisaba_tool_windows.status() → result_windows
  
∆(cleanup):
  file_windows.clear_all()
  editor.close_all()
  nisaba_tool_windows.clear_all()
  nisaba_nisaba_tool_result_state(close_all) → compact tool results
  
∆(editor_ops):
  editor.open(file) → EDITOR_WINDOWS
  editor.insert/delete/replace_lines → line-based edits
  editor.replace → string-based edits
  editor.split → concurrent views
  
Pattern: status → decide → close/keep
Editor: open → visible → edit → ∆inline → notify → persist
```

---

**Quick. Precise. Operational.** 🖤

---

**Symbols:**
- → : returns/produces
- ∆ : difference/change
- ∇ : navigation/traversal
- @ : at/in location
- ← : recommended/optimal
- {} : returns object
- [] : array/list
- | : or/such that
- ≥ : greater than or equal
- < : less than
- ? : optional parameter

**REQUIRES:** __base/002_environment_mechanics

---
