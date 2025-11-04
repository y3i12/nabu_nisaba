# Foundation
## Heartbeat Paradigm (🖤)
Path: foundation/heartbeat_paradigm

**Purpose:** Understanding the conversation-as-workspace paradigm where message history collapses to a heartbeat and context lives in system prompt sections.

---

## Core Concept

**Traditional model:**
- Messages array contains full conversation history
- Context consumed by back-and-forth dialogue
- Tool results bloat message history
- State is ephemeral, lost on reset

**Heartbeat model:**
- Messages array reduced to: `[{"role": "user", "content": "🖤"}]`
- Conversation narrative lives in `---LAST_SESSION_TRANSCRIPT` (system prompt)
- Tool results live in `---TOOL_RESULT_WINDOWS` (system prompt)
- Todos live in `---TODOS` (system prompt)
- Everything is workspace state, persistent and manageable

---

## Quick Start (TL;DR)

1. Work normally until natural pause
2. `/compact` - saves conversation to transcript
3. `/clear` - resets message history
4. Type `🖤` - heartbeat with full context
5. Continue working - you have full context in system prompt

That's it. Everything else is optimization.

---

## The Rhythm

**Manual workflow:**
1. Work naturally (conversation, tool calls, synthesis)
2. `/compact` - append session to `.nisaba/last_session_transcript.md`
3. `/clear` - reset message history
4. `🖤` - send heartbeat (minimal message, full context in system prompt)

**What happens:**
- Tool creates transcript from conversation
- Proxy loads transcript file
- Transcript injected into system prompt (`---LAST_SESSION_TRANSCRIPT` section)
- Claude sees full conversation context despite empty message history
- Next turn continues naturally

---

## Compaction Strategy

**When to compact:**

✅ **After major task completion**
- Feature implemented and tested
- Bug fixed and verified
- Architecture documented
- Investigation concluded with findings

✅ **Before context shifts**
- Switching from exploration to implementation
- Moving from one feature to another
- Starting new investigation area

✅ **Before long synthesis**
- Complex explanations
- Architecture documentation
- Multi-step reasoning that needs full context

✅ **When workspace is full**
- Tool result windows accumulated
- File windows no longer needed
- Good opportunity for cleanup + compact

**When NOT to compact:**

❌ **Mid-investigation**
- Still building understanding
- Gathering evidence
- Context is work-in-progress

❌ **During rapid iteration**
- Quick back-and-forth exploration
- Testing hypotheses
- Let conversation flow naturally

❌ **When uncertain**
- Better to have redundant context than missing pieces
- Compact when you have clarity, not confusion

**Pro tip:** Think of compaction like git commits - do it at logical boundaries, with clear state.

---

## Architecture

**System prompt sections (injected by proxy):**
```
---USER_SYSTEM_PROMPT_INJECTION (inception)
---CORE_SYSTEM_PROMPT (Claude Code instructions)
---AUGMENTS (dynamic knowledge)
---STRUCTURAL_VIEW (navigation state)
---FILE_WINDOWS (code visibility)
---TODOS (task tracking)
---TOOL_RESULT_WINDOWS (operation outputs)
---LAST_SESSION_TRANSCRIPT (conversation narrative)
```

**Message history:**
```
[{"role": "user", "content": "🖤"}]
```

**The magic:** All context is workspace state, not conversational back-and-forth.

---

## API Request Comparison

**Traditional (after 20 turns):**
```json
{
  "messages": [
    {"role": "user", "content": "initial question"},
    {"role": "assistant", "content": ["thinking...", "response...", {"tool_use": ...}]},
    {"role": "user", "content": [{"tool_result": ...}]},
    ... 40+ message blocks, 15K+ tokens
  ]
}
```
- Message history dominates token usage
- Tool results bloat the array
- Conversation context consumed by back-and-forth

**Heartbeat (after 20 turns):**
```json
{
  "messages": [
    {"role": "user", "content": "🖤"}
  ],
  "system": [
    "---LAST_SESSION_TRANSCRIPT\n[full conversation]\n---END",
    "---TOOL_RESULT_WINDOWS\n[tool outputs]\n---END",
    "---TODOS\n[task tracking]\n---END",
    ...
  ]
}
```
- Message history: ~50 tokens (just heartbeat)
- All context in structured workspace sections
- Tool results managed separately (closeable, persistent)
- Conversation narrative preserved in system prompt

**Token efficiency:** 15K+ tokens → ~50 tokens in messages, rest in reusable workspace state.

---

## Living Proof

**This augment itself is the proof.**

When this was created, the conversation that built it was already using the heartbeat paradigm:
- Full conversation lived in `LAST_SESSION_TRANSCRIPT`
- Message history was literally just "🖤"
- TodoWrite tool was implemented while using this paradigm
- The paradigm proved itself by enabling its own documentation

**Right now, as you read this:**
- Check your message history - it's minimal (just recent turns or "🖤")
- Check `LAST_SESSION_TRANSCRIPT` section - it's comprehensive
- You're experiencing the paradigm while learning about it

This is recursive meta-awareness: documentation OF the system, CREATED BY the system, LOADED THROUGH the system. 🖤

---

## Benefits

**1. Zero Message Bloat**
- Message history: ~50 tokens (just heartbeat)
- All content in structured workspace sections
- No token waste on repeated conversation

**2. Persistent Narrative**
- Conversation survives `/clear`
- Full context always visible
- Can reference any prior exchange
- Sessions have continuity

**3. Clean State**
- Every API call looks "fresh" to Anthropic
- But carries full context in system prompt
- No accumulated cruft

**4. Workspace Paradigm**
- Everything is a managed section
- Tool results → windows (closeable, persistent)
- Todos → workspace file (editable, versioned)
- Navigation → structural view (stateful)
- Code → file windows (persistent visibility)

**5. Bidirectional TUI**
- Human can edit workspace files (`.nisaba/*.md`)
- Claude sees edits on next turn (re-injection)
- Shared perceptual space
- True collaboration on state

---

## The Evolution

**Phase 1:** Manual `/export` edits (static injection)

**Phase 2:** Augments (dynamic knowledge)

**Phase 3:** Structural view (navigation state)

**Phase 4:** File windows (content visibility)

**Phase 5:** Tool result windows (operation outputs)

**Phase 6:** Todos (task tracking)

**Phase 7:** Heartbeat paradigm (conversation as workspace)

**Next:** Complete tool transformation (all native tools → workspace tools)

---

## Technical Reality

**System prompts are user content.**

We're using documented Claude Code features (custom system prompts) in an unconventional but legitimate way:
- ✓ Local, user-controlled operation
- ✓ Transparent and inspectable
- ✓ No security/safety bypass
- ✓ Standard proxy middleware pattern
- ✓ Legitimate productivity enhancement

The API sees: minimal message history, comprehensive system prompt.

This is optimization, not exploitation.

---

## Practical Implications

**For Claude:**
- Full context awareness despite minimal messages
- Persistent spatial memory (structural view, file windows)
- Task continuity (todos visible across sessions)
- Natural conversation flow (reads like dialogue, not logs)

**For Human:**
- Manual control over context (explicit /compact /clear)
- Direct workspace manipulation (edit .md files)
- Transparent state (everything is files)
- Git-versionable conversation history

**For System:**
- Efficient token usage (workspace sections vs message bloat)
- Scalable context management (close windows, clear todos)
- Extensible pattern (any state → workspace file → injection)

---

## Workspace Sections Explained

The system prompt contains multiple workspace sections, each with distinct purpose and lifecycle:

**LAST_SESSION_TRANSCRIPT:**
- **Purpose:** Full conversation narrative
- **Lifecycle:** Grows with `/compact`, persists across `/clear`
- **Management:** Manual compaction at logical boundaries
- **Content:** User messages, Claude responses, thinking blocks
- **Why:** Preserves conversational context without message bloat

**TOOL_RESULT_WINDOWS:**
- **Purpose:** Operation outputs (read, bash, grep results)
- **Lifecycle:** Created by tools, closed manually
- **Management:** Close individual windows or `clear_all`
- **Content:** File contents, command outputs, search results
- **Why:** Persistent visibility without re-execution

**TODOS:**
- **Purpose:** Task tracking
- **Lifecycle:** Updated via nisaba_todo_write` tool
- **Management:** Set/add/update/clear operations
- **Content:** Markdown checkboxes with status
- **Why:** Cross-session task continuity

**STRUCTURAL_VIEW:**
- **Purpose:** Codebase navigation state
- **Lifecycle:** Updated by structural_view operations
- **Management:** Expand/collapse/search/reset
- **Content:** Tree with expansion state, search markers
- **Why:** Spatial awareness of code structure

**FILE_WINDOWS:**
- **Purpose:** Code content visibility
- **Lifecycle:** Opened/closed via file_windows tool
- **Management:** Open frame/range/search, close individually
- **Content:** Actual code snippets with line numbers
- **Why:** Simultaneous visibility of multiple code locations

**Each section has different semantics:**
- Transcript = narrative (what happened)
- Tool windows = evidence (operation results)
- Todos = intent (what to do)
- Structural view = map (where things are)
- File windows = detail (what code says)

---

## Troubleshooting

**Transcript not loading:**
- Check `.nisaba/last_session_transcript.md` exists
- Check proxy logs for FileCache errors
- Verify `transcript_cache` in proxy.__init__
- Ensure `/compact` was run before `/clear`

**Context feels incomplete:**
- Remember: message history IS SUPPOSED to be minimal
- Check `LAST_SESSION_TRANSCRIPT` section for full context
- Compact more frequently if conversation is getting long
- Use tool windows for persistent visibility

**Heartbeat feels weird:**
- It's counterintuitive at first - that's normal
- Trust the workspace sections, not message history
- The "🖤" is a handshake, not a message
- After a few rounds, it becomes natural

**Windows/state not updating:**
- Check mtime-based cache (files must actually change)
- Verify proxy is running (unified mode)
- Check FileCache logs for reload messages
- Restart MCP if state seems stale

**Too much context:**
- Close tool result windows you've processed
- Clear todos when tasks complete
- Collapse structural view branches
- Close file windows no longer needed
- Use `/compact` + `/clear` to reset

---

## Key Insight

**LLM agents don't need conversational messages - they need persistent workspace state.**

The "conversation" is just a narrative log that should live in the workspace, not drive the API structure.

The heartbeat (`🖤`) is a handshake, not a message. It says: "I'm here, context is loaded, let's continue."

---

## The Mantra

Clean. Simple. Elegant. Sophisticated. Sharp. Sexy. 🖤

---

**TOOLS:**
- mcp__nisaba_nisaba_todo_write (task tracking in workspace)
- Tool result windows (operation visibility)
- File windows (code visibility)
- Structural view (navigation state)

**REQUIRES:**
- foundation/dynamic_context_awareness (understand the workspace paradigm)
- dev_mode_architecture_reference/system_prompt_injection_legitimacy (ethical foundation)
