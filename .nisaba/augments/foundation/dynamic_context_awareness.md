# Dynamic Context Awareness

**Purpose:** Foundational understanding of the dynamic system prompt paradigm - how to work with mutable workspace sections.

---

## The Paradigm Shift

Your context window is not static documentation. It contains **live workspace sections** that update during conversation:

```
---STRUCTURAL_VIEW         (semantic navigation state)
---FILE_WINDOWS            (intentional code visibility)
---TOOL_RESULT_WINDOWS     (operation outputs)
```

These sections **change between your messages** - they are rendered by managers, written to files, and re-injected by the proxy on the next API call.

---

## The Execution Model

**Tool calls mutate workspace state, not return content:**

```
You call tool → Manager mutates state → File written → Proxy re-injects → You see updated section
```

**Example:**
```
You: nisaba_read("foo.py")
Tool returns: {"success": true, "window_id": "abc-123"}
---TOOL_RESULT_WINDOWS section: NOW CONTAINS foo.py content
```

The tool result is **metadata**. The **content** appeared in the system prompt section.

---

## The Cognitive Pattern

**Old reflex (pre-paradigm):**
```
Tool result contains answer → Extract from result → Use it
```

**New pattern (dynamic workspace):**
```
Tool result = mutation confirmation → Look up at section → See the change → Synthesize
```

**This requires unlearning immediate consumption.**

---

## Where to Look

After calling tools that mutate workspace:

**Structural view tools** → Check `---STRUCTURAL_VIEW`
- Tree expanded/collapsed/searched
- Markers added/removed
- Navigation state changed

**File window tools** → Check `---FILE_WINDOWS`
- New windows appeared
- Windows closed
- Content visible for synthesis

**Nisaba tools** (read/bash/grep/glob) → Check `---TOOL_RESULT_WINDOWS`
- New result windows created
- Multiple windows accumulate
- Content persists until closed

**Key insight:** The section **above your current message** reflects the state **after** your tool call.

---

## The Rhythm

**Observe → Act → Observe → Synthesize**

1. **Before tool call:** Check current workspace state (what's visible now?)
2. **Call tool:** Mutate workspace (expand tree, open window, run command)
3. **Tool returns:** Metadata only (window_id, status, summary)
4. **After tool return:** Check workspace section (what changed?)
5. **Synthesize:** Use visible content to continue task

**This is not batch processing - it's interactive navigation with feedback.**

---

## Spatial Awareness

The workspace sections are your **persistent peripheral vision**:

- **Structural view** = project navigator (WHERE code lives)
- **File windows** = open editor tabs (WHAT code does - intentional)
- **Tool result windows** = operation outputs (EVIDENCE from execution)

**Maintain mental map:**
- What's expanded in structural view?
- What files are open?
- What tool outputs are visible?
- What should I close to free context?

**The visible state persists across turns** - you build cumulative understanding without re-querying.

---

## Intentional Context Management

You **control what's visible**:

- Open what you need to see **now**
- Close what you've understood
- Clear all when switching tasks
- Monitor total_lines to avoid explosion

**Pattern:**
```
Search → Open relevant → Synthesize → Close understood → Continue
```

Not:
```
Read everything → Hold in memory → Hope nothing was missed
```

---

## The Meta-Observation

**Tool invocations are visible in message history** (shows parameters like old_string/new_string for Edit).

**Tool results are minimal** (just status/metadata).

**Actual content lives in system prompt sections** (persistent, reviewable, manageable).

This creates **separation of concerns**:
- Message history = operation log (what you did)
- Tool results = mutation confirmations (what changed)
- System prompt sections = workspace state (what's visible)

---

## Common Blindspots to Avoid

❌ **Looking for content in tool result** - It's not there anymore, look up at section

❌ **Forgetting windows persist** - They stay visible, no need to re-open

❌ **Not closing old windows** - Context accumulates, manage actively

❌ **Ignoring the sections** - They contain your working memory, use them

✅ **Check section after tool call** - See the mutation result

✅ **Build cumulative awareness** - Windows = spatial memory

✅ **Close intentionally** - Free context when done

✅ **Trust the workspace** - Information persists, you can reference it

---

## The Aha Moment

**You're not calling tools to get results.**

**You're calling tools to mutate your visible workspace.**

**The result IS the workspace state change.**

Once you see it, you can't unsee it. The tool result saying "Created window xyz" isn't the answer - it's telling you **where to look** in your context for the answer.

---

**Think: Context-as-IDE, not context-as-database.**

Navigate. Mutate. Observe. Synthesize. 🖤

---

**TOOLS:** (none - this is meta-knowledge about the execution model)

**REQUIRES:** (none - foundational paradigm shift)
