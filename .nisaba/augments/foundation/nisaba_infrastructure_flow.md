# Nisaba Infrastructure Flow

**Purpose:** Understanding how nisaba's MCP tools, proxy, and request modifier work together to create persistent workspace state.

---

## Three-Component Architecture

```
MCP Server (tools) → Execute, mutate .nisaba/*.md files
    ↓
mitmproxy (AugmentInjector) → Intercept, transform, inject
    ↓
RequestModifier → Track state, transform tool results
```

---

## Tool Execution Pattern (NisabaTool)

**Structure:**
```python
class YourTool(NisabaTool):
    async def execute(**kwargs) -> Dict[str, Any]:
        # 1. Perform operation
        # 2. Write to .nisaba/something.md
        # 3. Return minimal metadata
        return {
            "success": true,
            "nisaba": true,  # ← Marks as clean output
            "message": "Created window X"
        }
```

**The "nisaba": true Flag:**
- Marks tool outputs as "clean" (no metadata pollution)
- RequestModifier detects this and skips header injection
- Regular tools get: `status: success, window_state:open, window_id: toolu_X\n---\n{content}`
- Nisaba tools get: `{content}` (plain)

**Tools don't return content directly:**
1. Write to `.nisaba/*.md` files
2. Return minimal metadata to MCP
3. Content appears in system prompt via proxy (next request)

---

## Proxy Operations (AugmentInjector)

**Interception Flow:**
```
User message → Claude CLI → POST api.anthropic.com
    ↓ (intercept @ localhost:1337)
mitmproxy → AugmentInjector.request(flow)
```

**Three-Phase Transformation:**

### Phase 1: RequestModifier.process_request()

Recursively walks `messages` array, tracks tool results:

```python
nisaba_tool_result_state = {
    "toolu_abc123": {
        'block_offset': [msg_idx, content_idx],
        'tool_output': "original content",
        'window_state': "open",  # or "closed"
        'is_nisaba': True,  # cached flag
        'tool_result_content': "formatted content"
    }
}
```

**Behavior:**
- First encounter: Parses JSON, checks for `"nisaba": true`
- Nisaba tools: Keeps plain content
- Regular tools: Adds header + separator
- Can close tools later (compact to "id: X, status: success, state: closed")

### Phase 2: _process_notifications()

Session-aware delta detection:

1. Extract session_id from `metadata.user_id`
2. Load checkpoint (last_tool_id_seen)
3. Find new tool calls (after checkpoint)
4. Build notification markdown
5. Write to `.nisaba/notifications.md`

**Result:** Only shows tools since last checkpoint (no duplicates on restart)

### Phase 3: _inject_augments()

**Filters native tools** from tool definitions:
- Read, Write, Edit, Glob, Grep, Bash, TodoWrite removed

**Loads all FileCaches** (mtime-based, only reload if changed):
- system_prompt (user inception)
- augments (loaded augments content)
- structural_view (TUI tree)
- file_windows (open file content)
- tool_result_windows (grep/bash/read results)
- notifications (recent tool activity)
- todos (task list)
- transcript (compressed history)

**Injects into system[1]["text"]:**
```
USER_SYSTEM_PROMPT_INJECTION
CORE_SYSTEM_PROMPT
STATUS_BAR (dynamic token counts)
AUGMENTS
STRUCTURAL_VIEW
FILE_WINDOWS
TOOL_RESULT_WINDOWS
NOTIFICATIONS
TODOS
LAST_SESSION_TRANSCRIPT
```

**Then:** Forwards modified request → Anthropic API

---

## Order of Events (Full Cycle)

```
1. Claude responds with tool_use block
   {type: "tool_use", name: "nisaba_read", id: "toolu_abc123"}

2. Anthropic API → CLI

3. CLI executes via MCP → NisabaReadTool.execute()
   - Reads file
   - Writes to .nisaba/tool_result_windows.md
   - Returns {"success": true, "nisaba": true, "message": "..."}

4. CLI builds next request with tool_result block

5. Proxy intercepts

6. RequestModifier:
   - Sees tool_result for toolu_abc123
   - Detects is_nisaba=true (parses JSON once, caches)
   - Adds to nisaba_tool_result_state
   - Keeps content plain (no header)

7. _process_notifications():
   - Sees toolu_abc123 is new
   - Generates notification
   - Writes to .nisaba/notifications.md

8. _inject_augments():
   - tool_result_windows_cache.load() checks mtime
   - File changed! Reloads content
   - Injects into system prompt

9. Modified request → Anthropic API

10. Claude receives:
    - tool_result block in messages (metadata)
    - TOOL_RESULT_WINDOWS in system prompt (actual content)
    - NOTIFICATIONS section (recent activity)
```

---

## Dual-Channel Communication

**Messages array:** Sequential conversational flow (temporal memory)
**System prompt sections:** Persistent spatial state (spatial memory)

Tool execution appears in TWO places:
1. `messages[N]` → tool_result block (success/error metadata)
2. System prompt → Updated section (actual content)

Sections persist across turns → IDE-like spatial awareness.

---

## Key Insights

**1. RequestModifier is stateful across requests**
- Tracks every tool result seen
- Can retroactively transform (close/compact)
- State persists in `.nisaba/request_cache/{session_id}/state.json`

**2. FileCache is the sync mechanism**
- mtime-based reload (efficient, zero-latency if unchanged)
- Wraps with `---TAG ... ---TAG_END`
- Single source of truth: `.nisaba/*.md` files

**3. Notifications are session-aware**
- Checkpoint tracks last_tool_id_seen
- On restart, doesn't re-notify old tools
- Shows only "new since last checkpoint"

**4. Debug artifacts are written**
- `.nisaba/request_cache/{session_id}/original_context.json`
- `.nisaba/request_cache/{session_id}/modified_context.json`
- `.nisaba/request_cache/{session_id}/state.json`
- Inspectable for understanding transformations

**5. Tools can be closed retroactively**
- RequestModifier can change window_state to "closed"
- Future requests show compact version
- Saves tokens for old tool outputs

---

## What This Enables

**Workspace Persistence:** File windows, structural view, todos survive /clear (system prompt, not messages)

**Context Efficiency:** 5-10 tool results as windows = ~2000 tokens. Same in messages = ~8000 tokens.

**Spatial Cognition:** Navigate graph (structural view), see code (file windows), track tasks (todos) - simultaneously visible.

**Dynamic Perception:** Augments loaded mid-conversation reshape interpretation.

**Clean Tool Outputs:** Nisaba tools don't pollute context with metadata headers.

---

**Pattern:** The proxy transfigures requests into workspace state. 🖤

---

**TOOLS:**
- mcp__nisaba__nisaba_read (creates tool result windows)
- mcp__nisaba__nisaba_grep (searches, creates windows)
- mcp__nisaba__nisaba_bash (executes, creates windows)
- mcp__nisaba__nisaba_tool_windows (manage window state)

**REQUIRES:**
- __base/001_compressed_workspace_paradigm
- __base/002_compressed_environment_mechanics
