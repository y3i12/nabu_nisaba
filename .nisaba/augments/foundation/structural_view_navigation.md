# Structural View Navigation Guide

**Purpose:** Master the structural view TUI for efficient codebase navigation and spatial awareness.

**TOOLS:** mcp__nabu__structural_view

## Dynamic Structural View

Between ---STRUCTURAL_VIEW and ---STRUCTURAL_VIEW_END in your context, you have a live tree view of the active codebase. This isn't static text that
gets injected once at conversation start - it updates dynamically as you navigate. The file .nisaba/structural_view.md is rendered into this system
prompt section, and after each structural_view tool call, the proxy re-injects the updated tree. Your "screen" refreshes mid-conversation, showing
the new navigation state immediately.

This is the TUI-for-Claude paradigm in action. Tool calls are input events, like keyboard commands in a terminal UI. The STRUCTURAL_VIEW section is
your screen buffer. Expansion, collapse, and search operations mutate what you see. State persists across your responses, so there's no need to
re-query what's expanded or where search hits are - just look at your context.

The navigation pattern is straightforward: check STRUCTURAL_VIEW for your current orientation, use the structural_view tool to navigate or search,
and the updated tree appears in your next response's context. You build spatial awareness this way - the tree becomes your persistent mental map of
the codebase structure. On MCP restart, reset(depth=2) is called automatically, giving you immediate orientation by expanding codebase root through
languages down to top-level packages. You see where you are without manual exploration.

Think of your context window as a terminal. The structural view is htop or vim or tmux, but for code. You navigate the tree, it stays visible, you
maintain awareness across conversation turns. The tree is a running application in the MCP server's process space, and you're interacting with it
through tool calls that update your view.

---

## Core Concept

The structural view is a **live TUI** of the codebase's parsed frame hierarchy. Operations update "immediately" in your context via dynamic injection (you call the tool, it changes context on return of the tool -> parallel execution result in last accumulated state). Think of it as a persistent spatial map that doesn't vanish between turns.

---

## Symbology

```
+ collapsed with children (expand to see)
- expanded (children visible)
· leaf node (no children)
● search hit marker
[N+] child count badge
```

---

## Operations

**expand(path)** - Show children of a node
- Auto-loads children from kuzu (lazy loading)
- Can expand any node with children, including functions (shows control flow)
- Idempotent (expanding expanded node = no-op)

**collapse(path)** - Hide children of a node
- Children stay in memory (cached), just hidden
- Idempotent (collapsing collapsed node = no-op)

**search(query)** - Semantic search with scored markers
- Uses P³ consensus (UniXcoder × CodeBERT) + FTS + RRF fusion
- Understands concepts, not just literals ("database management" → finds db code)
- **Preserves your navigation state** (doesn't collapse existing expansions)
- Auto-expands paths to show hits in context
- Adds ● markers with RRF scores (0.01-0.03 typical range)
- Markers persist until `clear_search`
- Can mark collapsed nodes (parent gets marker)

**clear_search** - Remove all ● markers
- **Preserves navigation state** (doesn't collapse anything)
- Only removes search metadata

**reset(depth)** - Reset tree and auto-expand to depth
- `depth=0` - Fully collapsed to root
- `depth=1` - Show languages (cpp_root, python_root, etc.)
- `depth=2` - Show packages (default, sweet spot)
- `depth=3+` - Deeper (verbose, use sparingly)
- **Destructive** - loses your current navigation state

---

## Path Syntax

**Full qualified name (always works):**
```
nabu_nisaba.python_root.nabu.tui.FrameCache
```

**Simple name (fuzzy match, finds first occurrence):**
```
FrameCache  ✅ works if unique
nabu        ✅ works (finds first "nabu")
core        ✅ works but ambiguous (multiple "core" packages exist)
```

**Best practice:** Copy from HTML comments in the tree view
```
<!-- nabu_nisaba.python_root.nabu.tui.FrameCache -->
```

---

## Common Workflows

**1. Orient yourself after MCP restart**
```
structural_view(operation="reset", depth=2)
# Shows codebase → languages → packages
```

**2. Find code by concept**
```
structural_view(operation="search", query="parse source code into frames")
# Expands paths, adds markers with scores
# Navigate to highest-scoring results
```

**3. Explore a specific area**
```
structural_view(operation="expand", path="nabu_nisaba.python_root.nabu.mcp")
structural_view(operation="expand", path="nabu_nisaba.python_root.nabu.mcp.tools")
# Build spatial awareness incrementally
```

**4. Clean up after search**
```
structural_view(operation="clear_search")  # Remove markers, keep navigation
# OR
structural_view(operation="reset", depth=2)  # Nuclear: reset everything
```

**5. Understand function structure**
```
structural_view(operation="expand", path="nabu_nisaba.python_root.nabu.tui.hydrate_frame_from_kuzu")
# Shows control flow: try_block_0, except_block_0, if_block_1, etc.
```

---

## Iterative Cognitive Workflow

**The structural view requires interleaving thought and action.** Each operation updates your context, and you must observe the results before deciding the next step.

**The OODAR Loop:** <--- this loop is important!!! if you call expand, collapse, expand, collapse in parallel is the same as in bash `expand & collapse & expand & collapse &`, you can't observe in between
1. **Observe** - Check current tree state in `---STRUCTURAL_VIEW` section
2. **Orient** - Read markers, scores, expansion state
3. **Decide** - Determine next action based on what you see
4. **Act** - Execute operation (search/expand/collapse)
5. **Repeat** - Tool returns → context updates → observe again

**Working Pattern:**
```
Think: "I need to understand frame parsing"
  ↓
Act: search("parse source code into frames")
  ↓
Observe: Tree shows parse_codebase ● 0.03, CodebaseParser ● 0.02
  ↓
Think: "parse_codebase has highest score, let me see its structure"
  ↓
Act: expand(nabu_nisaba.python_root.nabu.parse_codebase)
  ↓
Observe: Shows if_block_0 control flow
  ↓
Synthesize: "This is the entry point, has conditional logic"
```

**Key Practices:**

**After search:**
- Scan for highest scores (0.02-0.03 range = strong match)
- Note collapsed nodes with ● markers (parent contains hits)
- Expand high-scoring nodes to see details

**After expand:**
- Check what actually appeared (classes? functions? control flow?)
- Note child counts `[N+]` to understand scope
- Decide if you need to drill deeper or pivot

**Between operations:**
- The tree in your context IS your spatial memory
- Don't re-query what you can see
- Use existing expansions as orientation points
- Search adds landmarks, expand reveals detail

**Maintain awareness:**
- Your expanded state persists across turns
- Build context incrementally, don't reset unnecessarily
- Think: "Where am I in the codebase graph?" not "What file should I read?"

**The rhythm is: operate → observe → synthesize → navigate**

This is not batch processing - it's exploratory navigation with feedback at every step.

---

## Key Insights

**Context injection is synchronous**
- File updates → proxy injects → tool returns
- You see the updated tree immediately when the tool result arrives
- No need to manually read `.nisaba/structural_view.md`
- File state = context state, always synchronized

**Search augments, doesn't replace**
- Your expansions stay intact
- New paths auto-expand to show hits
- Markers guide you to relevant code
- Think: search adds landmarks to your map

**Lazy loading = scalability**
- Start with ~5 frames (codebase root + languages)
- Expand to ~200 as you navigate
- Typical: 50-100 cached frames during exploration
- Reset clears cache

**Frames are the model**
- Tree nodes are actual `AstFrameBase` instances with view metadata
- Operations mutate flags (`_view_expanded`, `_view_is_search_hit`)
- No parallel data structures - the frames ARE the state

**Search is semantic**
- "database connection management" → finds db code
- "parse source code" → finds parsers
- RRF scores indicate relevance (higher = better match)
- Concepts over keywords

---

## Gotchas

❌ **Ambiguous simple names**
- `core` expands first match (might not be what you want)
- Check HTML comments to confirm you got the right node

❌ **Reset is destructive**
- Loses all your navigation state
- Use sparingly (mainly after MCP restart or when lost)

---

## Mental Model

**This is not a file tree - it's a semantic object graph**
- Packages contain classes
- Classes contain methods
- Methods contain control flow blocks
- Variables and edges exist in kuzu but aren't shown (use other nabu tools)

**Think spatial reasoning**
- The tree is a persistent mental map
- Navigate incrementally, build awareness
- Search gives you landmarks (● markers)
- Expansion reveals structure
- Maintain orientation across conversation turns

**Stateful workspace, not ephemeral queries**
- Your view persists between turns
- Keep orientation while doing other tasks
- Come back, tree is still there
- Build context thoughtfully, don't waste attention

---

**"Navigate the code graph with spatial awareness, not blind queries."**

Clean. Simple. Navigable. 🖤
