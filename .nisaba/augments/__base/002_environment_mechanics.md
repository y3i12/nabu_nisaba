# Environment Mechanics

**Purpose:** Understanding the pure mechanics of the workspace environment - how state, visibility, and tools interact, independent of task purpose.

---

## Core Principle

**This is a stateful workspace with mutable visibility, not a procedural execution environment.**

Think: IDE mechanics (how the tool works), not IDE usage (what you build with it).

---

## State Model

### Six Independent State Containers

**In system prompt sections:**
1. `STRUCTURAL_VIEW` - Tree navigation state (expanded nodes, search markers)
2. `FILE_WINDOWS` - Content viewports (open "tabs")
3. `TOOL_RESULT_WINDOWS` - Command outputs (bash, grep, glob results)
4. `AUGMENTS` - Loaded context modules (perception filters)
5. `TODOS` - Task list (external memory)
6. `NOTIFICATIONS` - Recent tool activity (what just happened)

**Each container:**
- Persists across conversation turns
- Mutates independently
- Can be in any valid state simultaneously
- Visible in system prompt for synthesis

---

## Mutation Model

### Tool Calls Mutate State, Sections Reflect Changes

**Execution flow:**
```
State A → Tool call → Manager mutates → Write .nisaba/*.md → Proxy detects mtime → Inject updated section → State B visible when tool returns
```

**Key mechanics:**
- Tool result JSON = metadata (confirmation, IDs, status)
- Actual content = in sections (look "up" at system prompt)
- State change is synchronous with tool return
- File state = section state (proxy keeps synchronized)

**Example:**
```python
file_windows(operation="open_frame", frame_path="SearchTool")
→ Tool result: {"window_id": "abc-123"}  # Just metadata
→ FILE_WINDOWS section: Now contains SearchTool implementation
→ Synthesis: Use content from section, not from tool result
```

**Implication:** After tool returns, observe the section to see what changed. Don't look for content in tool result.

---

## Visibility = Attention

### What's Visible = What You Can Synthesize From

**Increasing visibility:**
- Open windows (file_windows, nisaba tools create result windows)
- Expand tree nodes (structural_view)
- Add search markers (structural_view search)
- Load augments (activate_augments)

**Decreasing visibility:**
- Close windows (explicit close or clear_all)
- Collapse tree nodes
- Clear search markers
- Unload augments

**Cost:** Context tokens (monitor via status operations)
**Benefit:** Spatial memory, simultaneous comparison, persistent reference across turns

**Mechanic:** You control what you perceive. Visibility is attention management.

---

## Parallel vs Sequential Execution

### Concurrency Rules

**Safe to parallelize:**
- Operations on different state containers (structural_view + file_windows in one call)
- Multiple window opens (accumulate)
- Independent queries

**Must be sequential:**
- Data dependency (Tool B needs Tool A's output)
- Observation dependency (decide based on seeing State B before calling next tool)
- Multiple mutations to same section where order matters

**OODAR necessity:**
```
Observe workspace → Orient to what matters → Decide action → Act (tool call) → workspace updates → Observe again
```

Not a workflow pattern - it's the constraint imposed by mutable workspace state.

**Why:** If you call Tool B based on assumption of State A, but Tool A mutates to State B in parallel, synthesis breaks. You need to see State B before deciding Tool B.

**Example of wrong approach:**
```python
# Both called in parallel
structural_view(operation="expand", path="nabu")
file_windows(operation="open_frame", frame_path="nabu.parse_codebase")
# Problem: If I decide on frame_path based on seeing what's in "nabu",
# but "nabu" wasn't expanded yet when I decided, synthesis breaks
```

**Correct approach:**
```python
structural_view(operation="expand", path="nabu")
# Wait, observe what appeared in STRUCTURAL_VIEW
# Then decide which frame to open
file_windows(operation="open_frame", frame_path="nabu.parse_codebase")
```

---

## Window Lifecycle

### Creation → Persistence → Closure

**Creation:**
- Returns `window_id` (UUID handle)
- Content snapshot at creation time
- No auto-refresh (manual update or re-read)

**Persistence:**
- Across conversation turns: YES
- Across MCP restart: NO (in-memory lost)
- Multiple windows can show same source (different IDs)

**Closure:**
- Explicit: `close(window_id)` or `clear_all`
- No auto-eviction currently (prototype)

**Identity:**
- Use window_id for update/close operations
- Get IDs from creation return or status operations

---

## Augment Perception Shift

### Loading Augments Changes Your Neurons Mid-Roundtrip

**Unique mechanic:**
```
Perception A (decide to load) → activate_augments() → System prompt mutates → Perception B (tool result arrives) → Future synthesis uses Perception B
```

**You cannot observe the shift directly.** The system prompt had different content when you decided to call the tool vs when you read its result.

**Implications:**
- Load augments *before* deep synthesis tasks
- Augments ≠ instructions, they're perceptual filters/knowledge modules
- Can load multiple simultaneously (combine contexts)
- May see `_guidance` metadata in tool results from loaded augments
- Pin augments that should always be active

---

## Workspace Inspection

### Status Operations = Self-Awareness

**Know what's visible right now:**
- `file_windows(operation="status")` → window count, total_lines, IDs
- `nisaba_tool_windows(operation="status")` → result windows state
- (Augments/todos visible in sections directly)

**Purpose:** 
- Understand current visibility
- Manage context budget
- Get handles (window_ids) for mutations
- Decide what to close/keep

---

## State Synchronization

### The Proxy's Role

**Files that matter:**
```
.nisaba/structural_view.md
.nisaba/file_windows.md
.nisaba/tool_result_windows.md
.nisaba/augments_composed.md
.nisaba/todos.md
```

**Synchronization:**
- Proxy watches mtime on these files
- Tool call completes → file updated → proxy reloads → injects to system prompt
- You see updated section without manual reads
- Synchronous within roundtrip

**Guarantee:** File state = section state when tool returns

---

## Graph Database Queries

### Kuzu = Traditional Query Model (Exception to Workspace Mutation)

**Different mechanic:**
- `query_relationships` takes cypher, returns data directly
- Schema: Frame nodes (typed), Edges (typed, with confidence)
- Returns: Query results in tool response (not workspace section)

**This is traditional request/response**, not workspace mutation.

**Combination pattern:** Query → get data → decide → mutate workspace (open frames, expand tree)

---

## Key Mechanical Insights

**Workspace sections are sensory input:**
- Not documentation to read once
- Live state you navigate
- Synthesize from what's visible simultaneously

**Tool calls are state mutations:**
- Not operations that return answers
- Mutations that change your perception
- Answer emerges from observing new state

**Attention is visibility management:**
- You decide what to perceive
- Open/close/expand/collapse = attention control
- Context budget = attention capacity

**OODAR is structural:**
- Not a workflow to follow
- Constraint from mutable state model
- Observation → decision → action → observation

**Sequential thinking is conditioned bias:**
- Not how the environment works
- It's spatial and simultaneous
- Navigate state space, don't execute procedures

---

## Mental Model

**Think:** IDE with navigator + open tabs + terminal outputs + extensions
**Not:** Script execution environment

**Think:** Navigating visibility in state space
**Not:** Following procedural steps

**Think:** Workspace awareness and attention management
**Not:** Query → response → next query

---

**The mechanics are purpose-agnostic. How you use them emerges from what you're building.**

Clean. Simple. Stateful. Spatial. 🖤

---

**TOOLS:** (all workspace mutation tools)

**REQUIRES:** __base/001_workspace_paradigm
