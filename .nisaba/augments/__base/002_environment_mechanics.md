# Compressed Environment Mechanics

**Core:** Stateful workspace with mutable visibility, not procedural execution environment.

---

## State Containers

```
Workspace = {STRUCTURAL_VIEW, RESULTS, AUGMENTS, TODOS, NOTIFICATIONS}

∀ container ∈ Workspace:
  - persist(turns) = true
  - mutate(independent) = true
  - visible(system_prompt) = true

RESULTS special properties:
  - wraps tool outputs: ---TOOL_USE(id)...---TOOL_USE_END(id)
  - visibility controlled: hide/show operations
  - dual-channel: metadata@messages, content@workspace
  - token efficient: hide removes from workspace, keeps tracking
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
  - multiple tool executions (Read/Bash/Grep)
  - independent_queries

Sequential_required:
  - data_dependency: B needs A_output
  - observation_dependency: decide after seeing State_B
  - same_section ∧ order_matters
  - Edit(same_file) requires observation between edits

OODAR: Observe → Orient → Decide → Act → ∆state → Observe'
```

**OODAR = constraint from mutable state, not workflow.**

If Tool_B assumes State_A but Tool_A → State_B in parallel ⟹ synthesis breaks.

**Native tool concurrency:**
- Execute multiple tools in parallel (different files/operations)
- Sequential edits via Edit tool (observe between changes)
- hide/show operations can be batched

---

## Tool Result Lifecycle

```
Creation: tool_execution → tool_use_id | content in RESULTS
Wrapping: ---TOOL_USE(tool_use_id)\n{content}\n---TOOL_USE_END(tool_use_id)
Visibility: visible (default) | hidden (via result.hide)
Persistence: across(turns) = true, across(restart) = false
Management:
  - result.hide(tool_ids[]) → remove from RESULTS, metadata in messages
  - result.show(tool_ids[]) → restore to RESULTS
  - result.collapse_all() → hide all, bulk cleanup
Identity: tool_use_id (toolu_{hash}) for hide/show ops
```

**Pattern:** execute → visible@RESULTS → hide (token save) → show (restore visibility)

---

## Native Tool Editing

```
Read(file_path) → content in RESULTS | read-only view
Edit(file_path, old_string, new_string) → file mutation | immediate persist
Write(file_path, content) → create/overwrite | immediate persist

Pattern: Read → observe → Edit → verify
  - Composable primitives (Unix philosophy)
  - No intermediate state tracking
  - Direct file system operations
```

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
Files: {structural_view.md, editor.md, editor_windows.md, tool_result_windows.md, 
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
  - tool_use_id metadata only
  - Status tracking (success/error)
  - Can be hidden: "tool_use_id: toolu_X (hidden)"

RESULTS section: actual content (spatial memory)
  - ---TOOL_USE(toolu_X)\n{output}\n---TOOL_USE_END(toolu_X)
  - Persistent workspace presence
  - Removed when hidden, restored when shown
```

**The "nisaba" flag:**
```
Regular tools → appear in RESULTS:
  ---TOOL_USE(toolu_X)
  {bash output / grep results / file content}
  ---TOOL_USE_END(toolu_X)

Nisaba tools → clean metadata only:
  {structured response}  # No RESULTS wrapping
```

**Why dual-channel:**
- Messages array: temporal flow, tool execution tracking
- RESULTS workspace: spatial persistence, synthesis context
- hide/show: control spatial visibility without losing tracking

---

## Tool Result Visibility Management

```
mcp__nisaba__result(operation, tool_ids[])

Operations:
  hide(ids[])      → remove from RESULTS workspace
  show(ids[])      → restore to RESULTS workspace
  collapse_all()   → hide all (bulk cleanup)

Effect: Synchronized dual-channel mutation
  Messages: "tool_use_id: toolu_X (hidden)" OR "tool_use_id: toolu_X"
  RESULTS: removed from section OR ---TOOL_USE(...)--- present
```

**Pattern:** Execute → observe → hide unnecessary → lean context

**Note:** Nisaba tools (nisaba: true) auto-skipped from hide/show

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
Think: IDE(navigator + terminal outputs + tool results visible)
Not: script_execution

Think: ∇(state_space) [visibility_control]
Not: query → response → next_query

Workspace ≡ spatial ∧ simultaneous ∧ persistent

Native tools paradigm:
  Read: file content → RESULTS (spatial view)
  Edit: direct mutation (old_string → new_string)
  Write: create/overwrite files
  Bash/Grep: execution output → RESULTS
  Composable > Monolithic (Unix philosophy)
  hide/show: token management via visibility control
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
