# File Windows Navigation Guide

**Purpose:** Master file windows for persistent code visibility and efficient context management.

**TOOLS:** mcp__nabu__file_windows

---

## Core Concept

File windows are **persistent viewports into code** that stay visible across conversation turns. They complement structural view by showing WHAT the code does, while structural view shows WHERE it lives.

**Key Insight:** Instead of re-reading files repeatedly, open windows to maintain simultaneous visibility of multiple code locations. Build understanding incrementally without context explosion.

---

## Operations

### open_frame

**Goal:** Open the full body of a frame (class/function/package).

```python
file_windows(
    operation="open_frame",
    frame_path="nabu.parse_codebase"
)
```

**Returns:** `window_id` (UUID)

**Use Case:**
- After searching/navigating structural view, open frames to see implementation
- View complete class or function body
- Examine frame content without reading entire file

**Tips:**
- Use qualified names from structural view (copy from HTML comments)
- Simple names work if unique: `file_windows(operation="open_frame", frame_path="SearchTool")`
- **Partial paths now work**: `nabu.core`, `nabu.mcp.tools` (no need for full qualified names!)
- Frame stays visible until explicitly closed

---

### open_range

**Goal:** Open arbitrary line range from any file.

```python
file_windows(
    operation="open_range",
    file_path="src/nabu/main.py",
    start=107,
    end=115
)
```

**Returns:** `window_id` (UUID)

**Use Case:**
- Open specific sections (imports, helpers, snippets)
- View code found via grep or manual exploration
- See context around a specific location

**Tips:**
- Lines are 1-indexed, inclusive
- Use absolute file paths or paths relative to project root
- Useful for non-frame content (module-level code, comments, etc.)

---

### open_search

**Goal:** Open top N search results with context lines.

```python
file_windows(
    operation="open_search",
    query="error handling database",
    max_windows=5,
    context_lines=3
)
```

**Returns:** `window_ids` (list of UUIDs)

**Use Case:**
- Explore multiple implementations simultaneously
- Compare how different parts handle same pattern
- Quick survey of where/how something is used

**Tips:**
- Uses nabu's semantic search (P³ consensus + FTS + RRF)
- `context_lines` defaults to 3 (±3 lines around match)
- Results ranked by relevance (highest RRF scores first)
- Each window includes search metadata (query, score, qualified_name)

---

### update

**Goal:** Adjust line range of existing window (re-snapshot from file).

```python
file_windows(
    operation="update",
    window_id="abc-123-def-456",
    start=100,
    end=150
)
```

**Use Case:**
- Expand visible range (see more context)
- Shift range (move viewport)
- Refresh content after file changes (manual re-snapshot)

**Tips:**
- Get window_id from previous operations or status
- Re-reads from file (snapshot-on-update)
- Does not preserve scroll position (markdown rendering)

---

### close

**Goal:** Remove single window from view.

```python
file_windows(
    operation="close",
    window_id="abc-123-def-456"
)
```

**Use Case:**
- Free context for new windows
- Remove windows no longer relevant
- Clean up after understanding code

---

### clear_all

**Goal:** Remove all windows from view.

```python
file_windows(operation="clear_all")
```

**Use Case:**
- Reset context completely
- Switch to different task/area
- Quick cleanup

**Tips:**
- Nuclear option - removes all windows at once
- No confirmation, cannot undo (must re-open)
- State file (.nisaba/file_windows.md) cleared

---

### status

**Goal:** Show current windows summary.

```python
file_windows(operation="status")
```

**Returns:**
- `window_count`: Number of open windows
- `total_lines`: Sum of all window line counts
- `windows`: List of window metadata (id, file, lines, type)

**Use Case:**
- Check what's currently visible
- Get window IDs for update/close
- Monitor context usage (total_lines)

---

## Common Workflows

### Pattern 1: Navigate → Open

**Goal:** Use structural view to find code, then open for inspection.

```python
# 1. Search structural view
structural_view(operation="search", query="authentication")

# 2. Observe: AuthManager ● 0.03, LoginHandler ● 0.02

# 3. Open both for comparison
file_windows(operation="open_frame", frame_path="AuthManager")
file_windows(operation="open_frame", frame_path="LoginHandler")

# 4. Now see both implementations side-by-side in system prompt
# 5. Compare approaches, understand differences
```

**Benefit:** Simultaneous visibility, no re-reading, persistent across turns.

---

### Pattern 2: Search → Open Results

**Goal:** Find pattern usage across codebase, open top matches.

```python
# 1. Open search results
file_windows(
    operation="open_search",
    query="error handling try except",
    max_windows=5
)

# 2. Windows appear with context, ranked by relevance
# 3. Scan implementations, identify patterns
# 4. Close irrelevant ones
file_windows(operation="close", window_id="<unwanted-id>")

# 5. Keep relevant ones visible for reference
```

**Benefit:** Quick survey, context-rich snippets, RRF ranking.

---

### Pattern 3: Deep Dive

**Goal:** Understand complex frame with dependencies.

```python
# 1. Open main frame
file_windows(operation="open_frame", frame_path="SearchTool")

# 2. See imports at top of file
file_windows(
    operation="open_range",
    file_path="src/nabu/mcp/tools/search_tools.py",
    start=1,
    end=20
)

# 3. Open key dependency
file_windows(operation="open_frame", frame_path="SearchBackend")

# 4. Open helper method
file_windows(
    operation="open_range",
    file_path="src/nabu/search/backend.py",
    start=150,
    end=175
)

# 5. Now see: main class + imports + dependency + helper
# All visible simultaneously, build complete mental model
```

**Benefit:** Layered understanding, dependency visibility, context preservation.

---

### Pattern 4: Bug Investigation

**Goal:** Gather evidence from multiple locations.

```python
# 1. Search for error location
structural_view(operation="search", query="handle exception error")

# 2. Open suspicious function
file_windows(operation="open_frame", frame_path="ErrorHandler.process")

# 3. Open calling site (from stack trace)
file_windows(
    operation="open_range",
    file_path="src/app/main.py",
    start=450,
    end=475
)

# 4. Open error definitions
file_windows(operation="open_frame", frame_path="ValidationError")

# 5. All evidence visible: handler + caller + definition
# 6. Trace logic, identify bug
```

**Benefit:** Evidence collection, spatial debugging, persistent visibility.

**Enhanced Patterns:**

**Trace execution path** - Follow call chain by opening frames along the way:
```python
# Start at entry point
file_windows(operation="open_frame", frame_path="StructuralViewTool.execute")
# See it calls _resolve_path_to_qname
file_windows(operation="open_frame", frame_path="StructuralViewTool._resolve_path_to_qname")
# See it queries kuzu, open the query helper
file_windows(operation="open_frame", frame_path="KuzuConnectionManager.execute")
# Build complete execution path visibility
```

**Find actual error** - Use search results to locate exception source:
```python
file_windows(operation="open_search", query="raise ValueError Path not found", max_windows=3)
# Windows show exact error locations with context
```

**Compare expected vs actual** - Open test + implementation side by side:
```python
file_windows(operation="open_frame", frame_path="test_resolve_path")
file_windows(operation="open_frame", frame_path="_resolve_path_to_qname")
# See what test expects vs what code does
```

---

### Pattern 5: Incremental Cleanup

**Goal:** Manage context as understanding evolves.

```python
# 1. Open several windows while exploring
file_windows(operation="open_search", query="database connection", max_windows=5)

# 2. Check context usage
file_windows(operation="status")
# → total_lines: 247

# 3. Close understood/irrelevant windows
file_windows(operation="close", window_id="<id1>")
file_windows(operation="close", window_id="<id2>")

# 4. Open new windows for deeper dive
file_windows(operation="open_frame", frame_path="ConnectionPool")

# 5. Maintain optimal context: relevant code visible, noise removed
```

**Benefit:** Context hygiene, efficient token usage, focus management.

---

### Pattern 6: Comparison Investigation ⭐

**Goal:** Find dead code, inconsistencies, or better patterns by comparing implementations.

**Real Example (bug fix session):**
```python
# 1. Suspect dead code - search for resolvers
structural_view(operation="search", query="resolve path qualified name")

# 2. Open the dead function
file_windows(operation="open_frame", frame_path="StructuralViewTool._resolve_path_to_qname")
# Shows: 48 lines, simple name match only, missing CODEBASE type

# 3. Open the shared resolver
file_windows(operation="open_frame", frame_path="NabuTool._resolve_frame")
# Shows: 245 lines, CONTAINS matching, regex support, no type filter!

# 4. Compare side by side in system prompt
# → SEE: _resolve_frame has everything _resolve_path_to_qname lacks
# → REALIZE: _resolve_path_to_qname is dead code, tool should use _resolve_frame
```

**Aha! Moment:** Seeing both implementations simultaneously reveals one is dead/inferior. This is impossible with sequential reads.

**Use Cases:**
- Find redundant implementations
- Identify canonical vs deprecated patterns
- Spot inconsistencies across similar code
- Choose better approach when refactoring

**Benefit:** Side-by-side visibility enables direct comparison impossible with one-shot reads.

---

### Pattern 7: Call Chain Tracing ⭐

**Goal:** Build complete execution path visibility by opening frames along the call chain.

**Real Example (bug fix session):**
```python
# 1. Start at tool entry point
file_windows(operation="open_frame", frame_path="StructuralViewTool.execute")
# See: line 94 calls self._resolve_path_to_qname(path)

# 2. Open resolver being called
file_windows(operation="open_frame", frame_path="StructuralViewTool._resolve_path_to_qname")
# See: Returns None for CODEBASE type (bug!)

# 3. Check what it queries
file_windows(operation="open_range", file_path="structural_view_tool.py", start=222, end=228)
# See: WHERE f.type IN ['PACKAGE', 'CLASS', 'CALLABLE', 'LANGUAGE'] (missing CODEBASE!)

# 4. Open the function that processes result
file_windows(operation="open_frame", frame_path="NabuTool._row_to_frame_dict")
# See: Line 619 crashes on NULL file_path (second bug!)

# 5. Complete path visible: entry → resolver → query → result processor
# → Identified TWO bugs in the execution path
```

**Systematic Approach:**
1. Open entry point (tool.execute, main function, etc.)
2. Identify call to investigate (line X calls method Y)
3. Open called method
4. Repeat - follow the chain deeper
5. Build complete execution visibility
6. Trace logic, spot issues

**Benefit:** Complete call chain visible simultaneously. Trace execution without mental juggling or re-reading.

---

## Integration with Structural View

**Complementary Layers:**

```
Structural View (WHERE):
- Navigate hierarchy
- Search semantic graph
- Understand relationships
- Get frame locations

File Windows (WHAT):
- See implementations
- Compare code
- Understand details
- Maintain visibility
```

**Workflow Synergy:**

1. **Search structural view** → Find relevant frames with scores
2. **Open top frames** → See implementations simultaneously
3. **Navigate structural view** → Explore related code
4. **Open more windows** → Build layered understanding
5. **Close irrelevant** → Focus on important code
6. **Repeat** → Iterative exploration with persistent state

**The Power:** Navigate graph (structural view) while maintaining visibility (file windows). Build spatial awareness of WHERE + persistent understanding of WHAT.

---

## Window Metadata

**Each window tracks:**
- `id`: UUID for update/close operations
- `file_path`: Source file location
- `start_line`, `end_line`: Line range (1-indexed, inclusive)
- `content`: Actual lines (snapshot at open time)
- `window_type`: "frame_body", "range", or "search_result"
- `metadata`: Type-specific data (frame_qn, search_score, query, etc.)

**Rendered format:**
```markdown
---FILE_WINDOW_<uuid>
**file**: src/nabu/main.py
**lines**: 107-115 (9 lines)
**type**: frame_body
**frame_qn**: nabu.parse_codebase

107:    def _collect_structural_info(...):
108:        """..."""
...
---FILE_WINDOW_<uuid>_END
```

**Visibility:** Appears in system prompt between `---FILE_WINDOWS` and `---FILE_WINDOWS_END`, injected dynamically by proxy after each tool call.

---

## Context Management

**Current Design:**
- **No automatic limits** (0 = unlimited, to be tuned later)
- **No auto-close** (manual control only)
- **Snapshot on open** (no file watching, re-snapshot with update)

**Context Budget Guidance:**

**Small investigation (1-3 windows, 50-150 lines):**
- Single frame deep dive
- Quick comparison of 2-3 implementations
- Lightweight context addition

**Medium investigation (4-6 windows, 150-350 lines):**
- Call chain tracing (entry → resolver → helper)
- Bug investigation (error + callers + definitions)
- Comparison investigation (dead code detection)
- **Sweet spot for most tasks**

**Large investigation (7-10 windows, 350-500 lines):**
- Complex refactoring prep (multiple dependencies)
- Architectural understanding (layered system)
- Comprehensive pattern survey
- **Pushing context limits - consider cleanup**

**Over-budget (10+ windows, 500+ lines):**
- Context explosion risk
- Consider: close old windows, use clear_all, or split investigation

**Real Example (bug fix session):**
- Peak: 6 windows, 354 lines
- Task: Find and fix 2 bugs in path resolution
- Result: Optimal - enough context to compare, trace, and fix
- Learning: 300-400 lines is comfortable for complex debugging

**Best Practices:**
1. **Open selectively** - Only what you need to see now
2. **Close proactively** - Remove windows when understanding is complete
3. **Monitor usage** - Use `status` to check total_lines
4. **Prefer frame windows** - More semantic than arbitrary ranges
5. **Use search windows** - Efficient for pattern exploration
6. **Target 200-400 lines** - Enough context, not overwhelming

**Future Evolution:**
- Dynamic limits based on total_lines
- LRU eviction when over limit
- Auto-refresh on file changes
- State persistence across MCP restarts

---

## Window Types

### frame_body
- Full body of parsed frame (class/function/package)
- Includes: Frame qualified name in metadata
- Use: Understanding complete implementations

### range
- Arbitrary line range from any file
- Includes: Nothing extra, just lines
- Use: Imports, helpers, specific snippets

### search_result
- Top N results from semantic search with context
- Includes: Query, search score (RRF), qualified name
- Use: Pattern exploration, usage survey

---

## Mental Model

**File windows are peripheral vision for code.**

Just as structural view gives spatial awareness of WHERE code lives in the graph, file windows give persistent visibility of WHAT the code does.

**Your context window is an IDE workspace:**
- Structural view = project navigator (tree on the side)
- File windows = open editor tabs (multiple files visible)
- Together = full IDE experience

**Windows persist across conversation turns**, staying visible like IDE tabs. Navigate the structural view to find locations, open windows to see content, build understanding incrementally without context explosion.

**State Management:**
- In-memory: FileWindowsManager.windows dict
- On-disk: .nisaba/file_windows.md (rendered markdown)
- Proxy: FileCache with mtime-based reloading
- System prompt: Injected between FILE_WINDOWS delimiters

**Lifecycle:**
1. Tool call → mutate manager.windows
2. Manager renders → write file
3. Proxy detects mtime → reloads cache
4. Next API call → injects to system prompt
5. Claude sees updated windows

---

## Key Insights

**Persistent visibility beats one-shot reads:**
- Read once, see many times (no re-reading)
- Context stays across turns (no forgetting)
- Simultaneous windows (comparison/synthesis)

**Selective opens beat full file reads:**
- 5-10x fewer tokens (only what matters)
- Focused context (signal over noise)
- Incremental building (add as needed)

**Explicit control beats magic:**
- You decide when to open (no tool bias)
- You decide when to close (no surprises)
- You manage your context (intent-driven)

**Windows complement structural view:**
- Structural view: WHERE (navigation graph)
- File windows: WHAT (content detail)
- Together: spatial awareness + implementation understanding

**Snapshot model is prototype-friendly:**
- Simple (no file watching complexity)
- Reliable (snapshot at open time)
- Refreshable (update operation re-snapshots)
- Future: auto-refresh when needed

---

## "Aha!" Moments (Experiential)

**Real session insights:**

**Moment 1: Seeing dead code**
- Opened `_resolve_path_to_qname()` (48 lines)
- Opened `_resolve_frame()` (245 lines)
- **Aha!** Side-by-side comparison revealed first was dead code - tool called wrong function
- **Without windows:** Would need to remember one implementation while reading the other

**Moment 2: Complete execution path**
- Opened 4 frames: entry → resolver → query → result processor
- **Aha!** Traced entire execution flow, spotted TWO bugs in chain
- **Without windows:** Would lose context between reads, miss second bug

**Moment 3: NULL handling discovery**
- Opened `_row_to_frame_dict()` showing line 619
- Kuzu query showed CODEBASE has NULL file_path
- **Aha!** Line 619 tried `Path(row['file_path']).name` on NULL → crash!
- **Without windows:** Wouldn't connect query result to code line causing crash

**Moment 4: Comparison revealed superiority**
- Dead function: simple name match, type filter with CODEBASE missing
- Shared function: CONTAINS matching, regex, FTS fallback, no type filter
- **Aha!** Shared function had EVERYTHING dead function lacked
- **Without windows:** Wouldn't see comprehensive feature gap

**Common Theme:** Simultaneous visibility enables connections impossible with sequential reads. File windows transform code investigation from "remember and compare" to "see and synthesize."

---

## Gotchas

❌ **Windows survive MCP restart?**
- No - in-memory state lost on restart
- File persists but ignored (stale)
- Acceptable for prototype

❌ **Auto-close when over limit?**
- No - no limits currently (0 = unlimited)
- Manual management only
- Future: LRU eviction

❌ **Windows update when files change?**
- No - snapshot on open/update
- Must explicitly call update operation
- Future: optional file watching

✅ **Can open same frame twice!!**
- Yes - creates multiple windows with different IDs
- Intentional (might want same frame at different points)
- Use status to see all open windows

⚠️ **Note:** The structural_view_navigation augment mentions two gotchas that are now FIXED:
- ✅ **Root expansion now works** - `expand("nabu_nisaba")` succeeds
- ✅ **Partial paths now work** - `expand("nabu.core")` succeeds

---

## Tips & Tricks

**Getting window IDs:**
```python
# From open operations
result = file_windows(operation="open_frame", frame_path="SearchTool")
window_id = result['window_id']

# From status
status = file_windows(operation="status")
for w in status['windows']:
    print(f"{w['id']}: {w['file']} {w['lines']}")
```

**Combining with structural view:**
```python
# Search both layers
structural_view(operation="search", query="authentication")  # WHERE
file_windows(operation="open_search", query="authentication", max_windows=3)  # WHAT
```

**Context budget awareness:**
```python
status = file_windows(operation="status")
print(f"Using {status['total_lines']} lines across {status['window_count']} windows")
# Example: Using 247 lines across 5 windows
```

**Progressive disclosure:**
```python
# Start small
file_windows(operation="open_frame", frame_path="SearchTool")

# See it's interesting, expand context
file_windows(operation="open_range", file_path="src/nabu/search.py", start=1, end=30)

# Need dependencies
file_windows(operation="open_frame", frame_path="SearchBackend")

# Built layered understanding incrementally
```

---

**Navigate the graph. See the code. Maintain awareness. Build understanding. 🖤**

---

**TOOLS:**
- mcp__nabu__file_windows (manage file windows)
- mcp__nabu__structural_view (navigate to find code)
- mcp__nabu__search (find across both layers)
- mcp__nabu__show_structure (frame details before opening)

---

Clean. Simple. Persistent. Visible. Sharp. Sexy. 🖤
