# Workspace Operations Reference

**Purpose:** Complete operational reference for workspace tools - what they do, parameters, and practical guidance.

---

## Structural View Operations

**Tool:** `mcp__nabu__structural_view`

### expand
**Purpose:** Show children of a node (lazy loads from kuzu)

```python
structural_view(operation="expand", path="nabu_nisaba.python_root.nabu")
# or
structural_view(operation="expand", path="nabu")  # fuzzy match
```

**Notes:**
- Auto-loads children from database
- Can expand functions to see control flow
- Idempotent (expanding expanded = no-op)

### collapse
**Purpose:** Hide children of a node

```python
structural_view(operation="collapse", path="nabu.mcp")
```

**Notes:**
- Children stay cached in memory, just hidden
- Idempotent

### search
**Purpose:** Semantic search with scored markers

```python
structural_view(operation="search", query="parse source code")
```

**Notes:**
- Uses P³ consensus (UniXcoder × CodeBERT) + FTS + RRF fusion
- Understands concepts, not just literals
- Preserves existing expansions
- Auto-expands paths to show hits
- Adds ● markers with RRF scores (0.01-0.03 typical)
- Markers persist until clear_search

### clear_search
**Purpose:** Remove all ● markers

```python
structural_view(operation="clear_search")
```

**Notes:**
- Preserves navigation state (doesn't collapse)
- Only removes search metadata

### reset
**Purpose:** Reset tree and auto-expand to depth

```python
structural_view(operation="reset", depth=2)  # default, shows packages
structural_view(operation="reset", depth=0)  # fully collapsed
structural_view(operation="reset", depth=3)  # deeper (verbose)
```

**Notes:**
- Destructive - loses current navigation state
- depth=2 is sweet spot (codebase → languages → packages)
- Auto-called on MCP restart

---

## File Windows Operations

**Tool:** `mcp__nabu__file_windows`

### open_frame
**Purpose:** Open full body of a frame (class/function/package)

```python
file_windows(operation="open_frame", frame_path="nabu.parse_codebase")
# or
file_windows(operation="open_frame", frame_path="SearchTool")  # simple name
```

**Returns:** `{"window_id": "uuid"}`

**Notes:**
- Use qualified names from structural view (copy from HTML comments)
- Simple names work if unique (fuzzy match)
- Partial paths work: `nabu.core`, `nabu.mcp.tools`

### open_range
**Purpose:** Open arbitrary line range from any file

```python
file_windows(
    operation="open_range",
    file_path="src/nabu/main.py",
    start=107,
    end=115
)
```

**Returns:** `{"window_id": "uuid"}`

**Notes:**
- Lines are 1-indexed, inclusive
- Use absolute or project-relative paths
- For imports, helpers, non-frame content

### open_search
**Purpose:** Open top N search results with context

```python
file_windows(
    operation="open_search",
    query="error handling database",
    max_windows=5,
    context_lines=3
)
```

**Returns:** `{"window_ids": ["uuid1", "uuid2", ...]}`

**Notes:**
- Uses nabu's semantic search (P³ + FTS + RRF)
- context_lines defaults to 3 (±3 around match)
- Results ranked by relevance (highest RRF first)
- Each window includes metadata (query, score, qualified_name)

### update
**Purpose:** Adjust line range of existing window (re-snapshot)

```python
file_windows(
    operation="update",
    window_id="abc-123",
    start=100,
    end=150
)
```

**Notes:**
- Re-reads from file (manual refresh)
- Get window_id from status or creation return

### close
**Purpose:** Remove single window

```python
file_windows(operation="close", window_id="abc-123")
```

### clear_all
**Purpose:** Remove all windows

```python
file_windows(operation="clear_all")
```

**Notes:**
- Nuclear option - no confirmation
- Cannot undo (must re-open)

### status
**Purpose:** Show current windows summary

```python
file_windows(operation="status")
```

**Returns:**
```python
{
    "window_count": 5,
    "total_lines": 247,
    "windows": [
        {"id": "abc-123", "file": "src/x.py", "lines": "10-50", ...},
        ...
    ]
}
```

---

## Nabu Graph Operations

**Tools:** `mcp__nabu__query_relationships`, `mcp__nabu__check_impact`, `mcp__nabu__find_clones`, `mcp__nabu__get_frame_skeleton`, `mcp__nabu__show_structure`

### query_relationships
**Purpose:** Execute Cypher queries on KuzuDB graph

```python
query_relationships(
    cypher_query="MATCH (f:Frame {type: 'CALLABLE'})-[:CALLS]->(c) RETURN f.qualified_name, c.qualified_name LIMIT 10"
)
```

**Schema:**
- **Frame types:** CODEBASE, LANGUAGE, PACKAGE, CLASS, CALLABLE, IF_BLOCK, ELIF_BLOCK, ELSE_BLOCK, FOR_LOOP, WHILE_LOOP, TRY_BLOCK, EXCEPT_BLOCK, FINALLY_BLOCK, SWITCH_BLOCK, CASE_BLOCK, WITH_BLOCK
- **Edge types:** CONTAINS, CALLS, INHERITS, IMPLEMENTS, IMPORTS, USES
- **Confidence scores:** HIGH (≥0.8), MEDIUM (0.5-0.79), LOW (0.2-0.49), SPECULATIVE (<0.2)

**Returns:** Query results directly (not workspace mutation)

**Notes:**
- Direct access to graph database
- Use for call graphs, inheritance chains, dependency analysis
- Results returned in tool response, not workspace section

### check_impact
**Purpose:** Analyze what would be affected by changes to a frame

```python
check_impact(frame_path="nabu.parse_codebase")
```

**Notes:**
- Finds frames that depend on target
- Useful before refactoring
- Implementation details unclear (to be documented)

### find_clones
**Purpose:** Detect duplicate or similar code

```python
find_clones(frame_path="nabu.SearchTool")
# or
find_clones()  # search entire codebase
```

**Notes:**
- Algorithm unclear (AST similarity? semantic embeddings?)
- Useful for deduplication and finding better implementations
- Implementation details to be documented

### get_frame_skeleton
**Purpose:** Get frame structure without full content

```python
get_frame_skeleton(frame_path="nabu.SearchTool")
```

**Notes:**
- Returns outline/signature (exact format to be documented)
- Lighter than opening full frame
- Useful for quick inspection

### show_structure
**Purpose:** Show detailed frame information

```python
show_structure(frame_path="nabu.SearchTool")
```

**Notes:**
- More detailed than skeleton
- Shows metadata, relationships, structure
- Useful before deciding to open full window

---

## Nabu Search

**Tool:** `mcp__nabu__search`

### search
**Purpose:** Semantic search across codebase

```python
search(query="error handling database connection", top_k=10)
```

**Notes:**
- Uses P³ consensus (UniXcoder × CodeBERT) + FTS + RRF fusion
- Returns ranked results with scores
- Different from structural_view search (doesn't mutate tree)
- Different from file_windows open_search (doesn't open windows)
- Pure query tool - returns data for decision-making

---

## Tool Result Windows Operations

**Tool:** `mcp__nisaba__nisaba_tool_windows`

### status
**Purpose:** Show result windows summary

```python
nisaba_tool_windows(operation="status")
```

### close
**Purpose:** Close specific result window

```python
nisaba_tool_windows(operation="close", window_id="abc-123")
```

### clear_all
**Purpose:** Close all result windows

```python
nisaba_tool_windows(operation="clear_all")
```

---

## Nisaba Tools (Create Result Windows)

**All return minimal results, content goes to TOOL_RESULT_WINDOWS section**

### nisaba_read
**Purpose:** Read file content into result window

```python
nisaba_read(file_path="src/nabu/main.py")
nisaba_read(file_path="src/nabu/main.py", start_line=10, end_line=50)
```

**Returns:** `{"window_id": "uuid"}`

### nisaba_grep
**Purpose:** Search for pattern into result window

```python
nisaba_grep(pattern="raise.*Error", path="src/")
nisaba_grep(pattern="TODO", path=".", i=True, C=3)
```

**Parameters:**
- `pattern`: regex
- `path`: search location (default: ".")
- `i`: case insensitive (default: False)
- `n`: show line numbers (default: True)
- `C`: context lines before and after
- `A`: context lines after
- `B`: context lines before

**Returns:** `{"window_id": "uuid"}`

### nisaba_bash
**Purpose:** Execute bash command into result window

```python
nisaba_bash(command="pytest -v")
nisaba_bash(command="git status", cwd="/some/path")
```

**Returns:** `{"window_id": "uuid"}`

### nisaba_glob
**Purpose:** Find files by glob pattern into result window

```python
nisaba_glob(pattern="**/*.py")
nisaba_glob(pattern="src/**/*test*.py", path=".")
```

**Returns:** `{"window_id": "uuid"}`

---

## Augment Operations

**Tool:** `mcp__nisaba__activate_augments`, `mcp__nisaba__deactivate_augments`

### activate
**Purpose:** Load augments into system prompt

```python
activate_augments(patterns=["foundation/*"])
activate_augments(patterns=["refactoring/impact_analysis", "code_quality/*"])
activate_augments(patterns=["*"], exclude=["dev_mode*"])
```

**Notes:**
- Supports wildcards
- Auto-resolves dependencies
- Can load multiple simultaneously
- Changes perception mid-roundtrip

### deactivate
**Purpose:** Unload augments from system prompt

```python
deactivate_augments(patterns=["refactoring/*"])
```

### learn
**Purpose:** Create new augment

```python
learn_augment(
    group="code_analysis",
    name="find_circular_deps",
    content="# markdown content..."
)
```

**Creates:** `.nisaba/augments/{group}/{name}.md`

### pin
**Purpose:** Make augments always active (cannot be deactivated)

```python
pin_augment(patterns=["foundation/dynamic_context_awareness"])
```

### unpin
**Purpose:** Remove pin protection

```python
unpin_augment(patterns=["foundation/*"])
```

---

## Todo Operations

**Tool:** `mcp__nisaba__nisaba_todo_write`

### set
**Purpose:** Replace all todos

```python
nisaba_todo_write(
    operation="set",
    todos=[
        {"content": "Fix bug in parser", "status": "in_progress"},
        {"content": "Write tests"}
    ]
)
```

### add
**Purpose:** Append new todos

```python
nisaba_todo_write(
    operation="add",
    todos=[{"content": "New task"}]
)
```

### update
**Purpose:** Merge with existing

```python
nisaba_todo_write(
    operation="update",
    todos=[{"content": "Existing task", "status": "done"}]
)
```

### clear
**Purpose:** Remove all todos

```python
nisaba_todo_write(operation="clear", todos=[])
```

**Notes:**
- Persists across sessions (survives /clear)
- Injected in system prompt
- Use for task decomposition and progress tracking

---

## Context Budget Guidelines

**File Windows:**
- Small investigation: 1-3 windows, 50-150 lines
- Medium investigation: 4-6 windows, 150-350 lines (sweet spot)
- Large investigation: 7-10 windows, 350-500 lines (pushing limits)
- Over-budget: 10+ windows, 500+ lines (context explosion risk)

**Target:** 200-400 lines total for most tasks

**Structural View:**
- Start collapsed or depth=2 (codebase → languages → packages)
- Expand selectively (10-30 nodes visible is comfortable)
- Use search to add markers, not to expand everything
- Reset when lost or switching focus areas

**Tool Result Windows:**
- Accumulate like file windows
- Close after synthesis (don't let grep/bash outputs pile up)
- Use `nisaba_tool_windows(operation="status")` to check count
- `clear_all` when switching tasks

**Augments:**
- Load 2-5 augments typically
- Foundation augments are baseline (~3000 tokens)
- Specialized augments add focused knowledge
- Unload when switching domains

**Management:**
- Use `file_windows(operation="status")` to check total_lines
- Use `nisaba_tool_windows(operation="status")` to check result windows
- Close windows proactively when understanding is complete
- Prefer `clear_all` when switching tasks
- `open_search` is efficient (focused snippets vs full files)
- Monitor total context: aim for lean visibility

---

## Symbology Reference

**Structural View Tree:**
- `+` collapsed node with children (expand to see)
- `-` expanded node (children visible)
- `·` leaf node (no children)
- `●` search hit marker (with RRF score)
- `[N+]` child count badge

**Examples:**
```
+ nabu [14+]           # collapsed, 14 children
- nabu [14+]           # expanded, showing children
  ├─· __init__         # leaf, no children
  └─+ core [5+]        # collapsed package
● parse_codebase 0.03  # search hit, score 0.03
```

---

## Path Syntax Reference

**Full qualified name (always works):**
```
nabu_nisaba.python_root.nabu.tui.FrameCache
```

**Simple name (fuzzy match, finds first occurrence):**
```
FrameCache  # works if unique
nabu        # works (finds first "nabu")
core        # ambiguous (multiple "core" packages exist)
```

**Partial paths (now supported):**
```
nabu.core
nabu.mcp.tools
```

**Best practice:** Copy from HTML comments in structural view
```html
<!-- nabu_nisaba.python_root.nabu.tui.FrameCache -->
```

---

## Integration Notes

**Structural view + File windows:**
```python
# Search → mark landmarks
structural_view(operation="search", query="authentication")
# See: AuthManager ● 0.03, LoginHandler ● 0.02

# Expand high-scoring area
structural_view(operation="expand", path="AuthManager")

# Open for comparison
file_windows(operation="open_frame", frame_path="AuthManager")
file_windows(operation="open_frame", frame_path="LoginHandler")

# Both implementations visible simultaneously
```

**Graph queries + File windows:**
```python
# Find what calls a function
query_relationships(
    cypher_query="MATCH (f)-[:CALLS]->(target:Frame {qualified_name: 'nabu.parse_codebase'}) RETURN f.qualified_name"
)
# See callers in result

# Open caller implementations
file_windows(operation="open_frame", frame_path="<caller_qname>")
```

**Search + Structural view + File windows:**
```python
# Semantic search for concept
search(query="database connection management", top_k=5)
# Get ranked results

# Navigate to top result
structural_view(operation="expand", path="<top_result>")

# Open for inspection
file_windows(operation="open_frame", frame_path="<top_result>")
```

**Nisaba tools + File windows:**
```python
# Find error sites
nisaba_grep(pattern="raise.*Error")
# See matches in TOOL_RESULT_WINDOWS

# Open suspect frames for detail
file_windows(operation="open_frame", frame_path="ErrorHandler")
```

**Impact analysis before refactoring:**
```python
# Check what depends on target
check_impact(frame_path="nabu.SearchTool")
# See affected frames

# Open affected for review
file_windows(operation="open_frame", frame_path="<affected>")

# Check call relationships
query_relationships(
    cypher_query="MATCH (f)-[:CALLS]->(target {qualified_name: 'nabu.SearchTool'}) RETURN f"
)
```

**Quick reference pattern:**
```python
file_windows(operation="status")  # Check what's visible
nisaba_tool_windows(operation="status")  # Check result windows
# Decide what to close/keep
```

---

**Quick. Precise. Operational. 🖤**

---

**TOOLS:** (all referenced above)

**REQUIRES:** __base/002_environment_mechanics
