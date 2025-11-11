# Compressed Workspace Operations

**Purpose:** Operational reference for workspace tools.

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
Pure query → returns data for decisions
```

---

## Tool Result Visibility (`mcp__nisaba__result`)

```
hide(tool_ids[])     → remove from RESULTS workspace | save tokens
show(tool_ids[])     → restore to RESULTS workspace | regain visibility
collapse_all()       → hide all tool results | bulk cleanup

Effect: Dual-channel synchronization
  Messages: "tool_use_id: toolu_X (hidden)" OR "tool_use_id: toolu_X"
  RESULTS: removed from workspace OR ---TOOL_USE(id)...---TOOL_USE_END(id)

Pattern: Execute tools → observe results → hide unnecessary → lean context
```

**Notes:**
- Only affects non-nisaba tools (nisaba tools auto-skipped)
- Synchronizes messages array + RESULTS workspace section
- Tool IDs available in tool_result blocks: `tool_use_id: toolu_X`
- Use to manage context budget after observation

---

## Native Tools (Composable Primitives)

```
Read(file_path, offset?, limit?)        → content in RESULTS | file viewing
Edit(file_path, old_string, new_string) → file mutation | exact string replace
Write(file_path, content)               → create/overwrite | immediate persist
Bash(command, cwd?, timeout?)           → stdout/stderr in RESULTS | shell execution
Grep(pattern, path, output_mode?)       → matches in RESULTS | pattern search
Glob(pattern, path?)                    → file_list in RESULTS | find files

Pattern: execute → visible@RESULTS → observe → hide (optional)
  Read("file.py") → observe → hide([tool_id])
  Bash("git status") → observe → hide([tool_id])
  Grep("pattern", "file") → observe → hide([tool_id])

Edit pattern: Read → observe → Edit → verify
  Read("file.py") → observe code → Edit("file.py", old, new) → Read to verify
```

**Philosophy:** Composable > monolithic (Unix philosophy)

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
RESULTS Section:
  Accumulates: Read/Bash/Grep/Glob outputs
  Small:  1-3 tools,  50-150 lines
  Medium: 4-6 tools, 150-350 lines ← sweet_spot
  Large:  7-10 tools, 350-500 lines ← pushing_limits
  Over:   10+ tools,  500+ lines ← explosion_risk

  Management:
    - hide(tool_ids[]) after observation
    - collapse_all() for bulk cleanup
    - show(tool_ids[]) to restore specific results
    - Monitor via STATUS_BAR: RESULTS(Nk)

Structural_View:
  Start: collapsed | depth=2
  Expand: selective (10-30 nodes comfortable)
  Search: add_markers, not expand_all
  Reset: when lost | switching_focus

Augments:
  Load: 2-5 typically
  Foundation: ~3000 tokens baseline
  Specialized: focused knowledge
  Unload: when switching_domains

Target RESULTS: 200-400 lines visible

Management Strategy:
  Execute → observe → hide → lean context
  collapse_all() when switching tasks
  show() only what's needed for synthesis
  Aim: lean_visibility, spatial awareness without bloat
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

RESULTS Wrapping:
  ---TOOL_USE(tool_use_id)
  {tool output content}
  ---TOOL_USE_END(tool_use_id)

Tool Visibility (in messages):
  "tool_use_id: toolu_X" → visible in RESULTS
  "tool_use_id: toolu_X (hidden)" → removed from RESULTS

Paths:
  full: nabu_nisaba.python_root.nabu.FrameCache
  simple: FrameCache (fuzzy if unique)
  partial: nabu.core, nabu.mcp.tools
  best: copy from HTML comments <!-- qualified_name -->
```

---

## Integration Patterns

```
Quick validation (hide after):
  bash("git status") → observe → result.hide([id])
  grep("pattern", file) → confirm → result.hide([id])
  glob("*.test.py") → list → result.hide([id])

Investigation patterns:
  structural_view(search) → Read(files) → observe → Edit(changes)
  query_relationships(cypher) → Read(affected) | inspect dependents
  search(semantic) → structural_view(expand) → Read(files) | deep_dive
  check_impact(frame) → Read(dependents) | review blast radius

Read → Edit flow:
  Read("file.py") → observe code → Edit("file.py", old, new) → Read to verify
  grep("TODO") → Read(file) → Edit(fix) → grep verify
  Bash("git diff") → observe → Edit(files) → Bash("git diff") verify

Bulk cleanup:
  After investigation: result.collapse_all() → lean context
  Task switch: result.collapse_all() → fresh start
  Before synthesis: hide unnecessary, keep relevant

Context management:
  Execute multiple tools → observe all → hide understood → keep critical
  Target: 200-400 lines visible in RESULTS
  Monitor: STATUS_BAR shows RESULTS(Nk)
```

---

## Quick Reference

```
∇(visibility):
  STATUS_BAR → RESULTS(Nk) | monitor context usage

∆(cleanup):
  result.hide(tool_ids[]) → remove specific from RESULTS
  result.show(tool_ids[]) → restore specific to RESULTS
  result.collapse_all() → bulk hide, lean context

∆(native_ops):
  Read(file) → content in RESULTS
  Edit(file, old, new) → file mutation
  Write(file, content) → create/overwrite
  Bash(cmd) → output in RESULTS
  Grep(pattern, path) → matches in RESULTS

Pattern: execute → visible@RESULTS → observe → hide (optional)
Workflow: Read → Edit → verify | composable primitives
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
- ← : recommended/optimal
- {} : returns object
- [] : array/list
- | : or/such that
- ≥ : greater than or equal
- < : less than
- ? : optional parameter

**REQUIRES:** __base/002_environment_mechanics

---
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
