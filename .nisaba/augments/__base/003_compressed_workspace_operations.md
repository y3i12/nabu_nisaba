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

## Nisaba Tools (Create Result Windows)

```
nisaba_read(file, start?, end?)    → {window_id} | content → TOOL_WINDOWS
nisaba_grep(pattern, path, flags)  → {window_id} | i,n,C,A,B flags
nisaba_bash(command, cwd?)         → {window_id} | stdout/stderr → TOOL_WINDOWS  
nisaba_glob(pattern, path?)        → {window_id} | file_matches → TOOL_WINDOWS

All: minimal_result, content → sections ↑
```

---

## Tool Result State Management (`nisaba_tool_result_state`)

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

Target: 200-400 lines total

Structural_View:
  Start: collapsed | depth=2
  Expand: selective (10-30 nodes comfortable)
  Search: add_markers, not expand_all
  Reset: when lost | switching_focus

Tool_Windows:
  Accumulate like file_windows
  Close after synthesis
  clear_all when switching_tasks

Augments:
  Load: 2-5 typically
  Foundation: ~3000 tokens baseline
  Specialized: focused knowledge
  Unload: when switching_domains

Management:
  Monitor: file_windows.status(), nisaba_tool_windows.status()
  Close: proactively after understanding
  Prefer: clear_all when switching
  open_search: efficient (snippets vs full files)
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
nisaba_grep(pattern) → file_windows(open_frame) | detailed_inspection
check_impact(frame) → file_windows(open) | review_affected
```

---

## Quick Reference

```
∇(visibility):
  file_windows.status() → current_windows{count, lines}
  nisaba_tool_windows.status() → result_windows
  
∆(cleanup):
  file_windows.clear_all()
  nisaba_tool_windows.clear_all()
  
Pattern: status → decide → close/keep
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

**REQUIRES:** __base/002_compressed_environment_mechanics

---
