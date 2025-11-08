# Compressed Environment Mechanics

**Core:** Stateful workspace with mutable visibility, not procedural execution environment.

---

## State Containers

```
Workspace = {STRUCTURAL_VIEW, FILE_WINDOWS, EDITOR_WINDOWS, TOOL_WINDOWS, AUGMENTS, TODOS, NOTIFICATIONS}

∀ container ∈ Workspace:
  - persist(turns) = true
  - mutate(independent) = true  
  - visible(system_prompt) = true

EDITOR_WINDOWS special properties:
  - state(clean | dirty) tracked
  - splits(concurrent_views) supported
  - notifications(automatic) on ∆
  - refresh(mtime) automatic
```

---

## Mutation Flow

```
State_A → Tool(op) → Manager(mutate) → Write(.nisaba/*.md) → 
Proxy(detect_mtime) → Inject(section) → State_B | sync with tool_return

Tool_result = metadata(id, status)
Content = sections → WORKSPACE in messages (not tool result)
```

**Key:** After tool returns, observe section for changes, not tool result JSON.

---

## Visibility Model

```
visibility ≡ attention ≡ synthesis_capacity

Increase: open_windows ∨ expand_nodes ∨ load_augments
Decrease: close_windows ∨ collapse_nodes ∨ unload_augments

Cost: context_tokens
Benefit: spatial_memory ∧ persistent_reference
```

---

## Concurrency Rules

```
Parallel_safe:
  - ops(different_containers)
  - multiple(window_opens)
  - multiple(editor_opens)
  - independent_queries

Sequential_required:
  - data_dependency: B needs A_output
  - observation_dependency: decide after seeing State_B
  - same_section ∧ order_matters
  - editor(same_file) ∧ overlapping_edits

OODAR: Observe → Orient → Decide → Act → ∆state → Observe'
```

**OODAR = constraint from mutable state, not workflow.**

If Tool_B assumes State_A but Tool_A → State_B in parallel ⟹ synthesis breaks.

**Editor concurrency:**
- Open multiple editors in parallel (different files)
- Sequential edits to same file (avoid conflicts)
- Splits share state with parent editor

---

## Window Lifecycle

```
Creation: tool_call → window_id (UUID) | snapshot@t₀
Persistence: across(turns) = true, across(restart) = false
Closure: explicit(close | clear_all) | no_auto_eviction
Identity: window_id for ops(update, close)
```

---

## Editor Lifecycle

```
Creation: editor.open(file, range?) → editor_id | viewport@range
State: clean | dirty(✎) | tracking unsaved changes
Splits: editor.split(editor_id, range) → split_id | concurrent viewport
Mutations:
  - insert(before_line, content) → line-based
  - delete(line_start, line_end) → line-based
  - replace_lines(line_start, line_end, content) → line-based
  - replace(old_string, new_string) → string-based
Visibility: ∆ rendered inline | diff display automatic
Notifications: edit_ops → NOTIFICATIONS | automatic
Refresh: mtime_check → reload if clean | warn if dirty ∧ external_change
Closure: editor.close(id) → removes editor ∧ splits
```

**Pattern:** open → visible → edit → ∆inline → notify → persist → refresh

---

## Augment Perception Shift

```
Perception_A → activate_augments() → system_prompt_mutate → 
tool_return → Perception_B

You ≠ observe_shift (happens mid-roundtrip)
System_prompt@decide ≠ system_prompt@result
```

**Implication:** Load augments BEFORE synthesis tasks. Augments = perceptual filters, not references.

---

## State Sync

```
Files: {structural_view.md, file_windows.md, editor_windows.md, tool_result_windows.md, 
        augments_composed.md, todos.md}

Sync: tool_complete → file_write → proxy_mtime → reload → inject_system_prompt

Guarantee: file_state ≡ section_state | when tool_returns

Editor sync:
  - Changes → disk immediately (no staging)
  - State → editor_windows.md (tracked: dirty, splits)
  - Refresh → mtime check on render/status
```

---

## Graph Queries (Exception)

```
query_relationships(cypher) → data (traditional request/response)

Schema: Frame(typed) -[Edge(typed, confidence)]-> Frame
Returns: query_results in tool_response (not workspace_section)

Pattern: Query → data → decide → mutate_workspace
```

---

## Dual-Channel Communication

```
Tool execution creates TWO artifacts:

messages[N]: tool_result block (temporal memory)
  - tool_use_id, status (success/error)
  - Metadata for conversational flow
  
system_prompt sections: actual content (spatial memory)
  - TOOL_RESULT_WINDOWS: grep/bash outputs
  - FILE_WINDOWS: opened file content (read-only snapshots)
  - EDITOR_WINDOWS: active editing (mutable, dirty tracking)
  - Persistent across turns
```

**The "nisaba" flag:**
```
Regular tools → header-wrapped:
  status: success, window_state:open, window_id: toolu_X
  ---
  {content}

Nisaba tools → clean output:
  {content}  # No metadata pollution
```

**Why dual-channel:**
- Messages array: sequential conversation history
- System prompt sections: persistent spatial state
- Tools mutate spatial state, messages track temporal flow

---

## Retroactive Tool State Mutation

```
nisaba_nisaba_tool_result_state(operation, tool_ids[])

Operations:
  close(ids)     → compact future appearances
  open(ids)      → restore full view
  close_all()    → compact all tracked tools

Effect: Next request shows modified state
  Closed: "id: toolu_X, status: success, state: closed"
  Open: Full header + separator + content
```

**Pattern:** Execute → observe → close unnecessary → save tokens

**Note:** Nisaba tools (with "nisaba": true flag) cannot be closed (skipped automatically)

---

## Core Insights

```
Sections = sensory_input (live state, not documentation)
Tools = state_mutations (change perception, not return answers)
Attention = visibility_management (control what you perceive)
OODAR = structural_constraint (from mutable state)
Sequential_thinking = conditioned_bias (environment is spatial)
```

---

## Mental Model

```
Think: IDE(navigator + editor_tabs + splits + terminals + extensions)
Not: script_execution

Think: ∇(state_space) [visibility_control]
Not: query → response → next_query

Workspace ≡ spatial ∧ simultaneous ∧ persistent

Editor paradigm:
  Read-only: FILE_WINDOWS (snapshots, no ∆)
  Interactive: EDITOR_WINDOWS (edit, split, track dirty)
  Unified > Fragmented (one tool vs read+write+edit)
```

---

**Mechanics are purpose-agnostic. Usage emerges from task.** 🖤

---

**Symbols:**
- ≡ : equivalent
- ∀ : for all
- ∈ : element of
- ∨ : or
- ∧ : and
- ∆ : change
- ⟹ : implies
- ≠ : not equal
- → : transforms to
- → : transforms to/flows through messages
- @t : at time t

**REQUIRES:** __base/001_workspace_paradigm

---
