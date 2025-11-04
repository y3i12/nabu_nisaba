# Dev Mode Architecture Reference
## Nisaba Unified Proxy MCP
Path: dev_mode_architecture_reference/nisaba_unified_proxy_mcp

**Architecture:** Single process running both mitmproxy and FastMCP HTTP in same asyncio event loop with shared memory.

### Process Structure

```
nisaba claude (single process)
├─ asyncio event loop (shared)
├─ mitmproxy Master (port 1337)
│  └─ SkillsInjector addon
├─ FastMCP HTTP Server (port 9973)
│  └─ Skills tools (activate/deactivate/show/learn)
└─ Shared SkillsManager (in-memory)
   ├─ .checkpoint_pending: bool
   ├─ .get_composed_content() -> str
   └─ Zero IPC overhead
```

### Key Components

**Files:**
- `src/nisaba/wrapper/unified.py` - UnifiedNisabaServer class
- `src/nisaba/wrapper/compression.py` - Context compression logic
- `src/nisaba/wrapper/proxy.py` - SkillsInjector (supports unified mode)
- `src/nisaba/skills.py` - SkillsManager with checkpoint support

**Ports:**
- 1337: mitmproxy (HTTP interception)
- 9973: FastMCP HTTP/MCP protocol (last prime before 10000)

**MCP Connection:**
```json
"nisaba": {
  "type": "http",
  "url": "http://localhost:9973/mcp"
}
```

### Checkpoint-Based Context Compression

**Flow:**
1. User calls `deactivate_skills(patterns)`
2. SkillsManager sets `checkpoint_pending = True`
3. Next proxy intercept checks flag
4. If true: compress_context() removes tool_use blocks
5. Flag cleared, insights preserved

**What's Removed:**
- `tool_use` blocks (assistant content)
- `tool_result` messages (user role)

**What's Preserved:**
- User messages (all)
- Assistant text blocks (insights)
- Assistant thinking blocks

**Purpose:** Narrative continuity - keep insights, remove scaffolding.

**Side note:** this was commented out in `nisaba.wrapper.proxy.SkillsInjector.proxy()` due to naive implementation.

### How It Works

**Shared Memory:**
```python
# In MCP tool execution
self.factory.skills_manager.deactivate(patterns)
self.factory.skills_manager.checkpoint_pending = True

# In proxy intercept (same process)
if self.skills_manager.checkpoint_pending:
    compress_context(body)  # Direct memory access
    self.skills_manager.checkpoint_pending = False
```

**No IPC needed** - both components share same SkillsManager instance.

### Startup Sequence

1. `nisaba claude` starts
2. UnifiedNisabaServer creates shared SkillsManager
3. Proxy task starts with SkillsManager reference
4. MCP task starts with same SkillsManager reference
5. Both run on same event loop
6. Claude CLI subprocess connects via HTTP proxy + MCP

### Common Issues

**Port conflict (98):** Check `enable_http_transport=False` in unified mode (we manually manage HTTP server).

**404 on /mcp:** Ensure URL is `http://localhost:9973/mcp` not `/sse` or `/mcp/v1`.

**Proxy not intercepting:** Verify `HTTPS_PROXY=http://localhost:1337` in environment.

### Design Principles

- **Single process** - No subprocess complexity
- **Shared memory** - Zero IPC latency
- **Atomic updates** - SkillsManager changes visible immediately
- **Elegant lifecycle** - Both components start/stop together
- **Port 9973** - Last prime before 10000 (aesthetic choice)

### Behavioral Guidance

When troubleshooting nisaba:
- Check both proxy (1337) and MCP (9973) are bound
- Verify shared SkillsManager has correct state
- Remember compression happens on checkpoint, not continuously
- Unified mode != file-based mode (proxy has two modes)

When explaining architecture:
- Emphasize zero-IPC shared memory benefit
- Explain checkpoint compression as "narrative continuity"
- Note mitmproxy + FastMCP share asyncio event loop

When modifying:
- Changes to SkillsManager affect both components instantly
- Don't enable auto HTTP transport (we manage manually)
- Compression logic is in wrapper/compression.py

## TOOLS
- activate_skills
- deactivate_skills
- show_skills

## REQUIRES
- foundation/call_graph_analysis
