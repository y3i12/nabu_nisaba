# Nisaba

**MCP Framework with Dynamic Context Augmentation**

<p align="center">
  <em>The goddess who organizes the tools of wisdom</em>
</p>

---

## What Is Nisaba?

A **lightweight, opinionated framework** for building Model Context Protocol (MCP) servers with a twist: **dynamic system prompt injection** via augments.

Named after the Mesopotamian goddess of writing and organization, Nisaba handles MCP infrastructure while introducing novel paradigms for LLM-agent cognition.

**Status:** v0.1-alpha | MIT Licensed | Extracted from Nabu research project

---

## The Unique Value

Most MCP frameworks stop at tool registration. **Nisaba goes further:**

### 1. Augments: Perceptual Filtering

Load/unload knowledge domains that change how LLMs think:

```python
# Traditional: Static system prompt
system_prompt = "You are a code assistant. Here are 50 pages of documentation..."

# Nisaba: Dynamic augmentation
activate_augments(["architecture/*"])  # Load architecture analysis knowledge
# → System prompt mutates mid-conversation
# → Agent perception shifts without reload
```

**Key insight:** Augments aren't reference docs. They're cognitive filters that change how agents synthesize information.

### 2. Workspace as Mutable State

Context isn't conversation history - it's a persistent spatial environment:

```python
# FILE_WINDOWS: Persistent code snippets (like IDE tabs)
file_windows.open_frame("AuthService")

# STRUCTURAL_VIEW: Live tree navigation with search markers
structural_view(operation="expand", path="nabu.mcp")

# TOOL_RESULT_WINDOWS: Accumulated grep/bash outputs
# All persist across turns, mutate dynamically
```

Think: **IDE with tabs/terminals/navigator**, not sequential chat history.

### 3. Proxy-Based Context Injection

mitmproxy intercepts Anthropic API calls and injects:
- Active augments (knowledge domains)
- File windows (open code snippets)
- Structural view (tree navigation state)
- Tool results (grep/bash outputs)
- TODOs (persistent task list)

**The magic:** File updates detected via `mtime` → re-injected automatically.

---

## Quick Start

### Installation

```bash
pip install -e .  # From nisaba directory
```

### Minimal MCP Server

**Step 1: Define a tool**

```python
# my_project/mcp/tools/hello.py
from nisaba import MCPTool
from typing import Dict, Any

class HelloTool(MCPTool):
    """Says hello."""

    def get_tool_schema(self) -> Dict[str, Any]:
        return {
            "name": {"type": "string", "description": "Name to greet"}
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        name = kwargs.get("name", "World")
        return self.success(f"Hello, {name}!")
```

**Step 2: Create config**

```python
# my_project/mcp/config.py
from nisaba import MCPConfig

class MyConfig(MCPConfig):
    def _get_tool_base_class(self) -> type:
        from my_project.mcp.tools import MyToolBase
        return MyToolBase

    def _get_module_prefix(self) -> str:
        return "my_project.mcp.tools"
```

**Step 3: Create factory**

```python
# my_project/mcp/factory.py
from nisaba import MCPFactory

class MyFactory(MCPFactory):
    def _get_initial_instructions(self) -> str:
        return "Use these tools to interact with MyApp."
```

**Step 4: Run**

```python
# my_project/mcp/server.py
from my_project.mcp.config import MyConfig
from my_project.mcp.factory import MyFactory

config = MyConfig(server_name="my_app")
factory = MyFactory(config)
mcp = factory.create_mcp_server()
mcp.run()
```

**Done!** Auto-discovery, auto-registration, ready to serve.

---

## Core Concepts

### Auto-Discovery

Nisaba scans your modules and auto-registers tools:

```python
from nisaba import ToolRegistry, MCPTool

registry = ToolRegistry(
    tool_base_class=MCPTool,
    module_prefix="my_project.mcp.tools"
)

# Automatically finds:
# - HelloTool → "hello"
# - QueryTool → "query"
# - SearchTool → "search"

tool_names = registry.get_all_tool_names()
```

**No manual registration!**

### Tool Markers

Control behavior with decorators:

```python
from nisaba import MCPTool, ToolMarkerOptional, ToolMarkerDevOnly, ToolMarkerMutating

@ToolMarkerOptional
class DebugTool(MCPTool):
    """Can be disabled in production contexts."""
    pass

@ToolMarkerDevOnly
class InternalTool(MCPTool):
    """Only available with dev_mode=True."""
    pass

@ToolMarkerMutating
class DeleteTool(MCPTool):
    """Performs state-changing operations."""
    pass
```

### Context-Based Filtering

Define which tools are enabled in different environments:

```yaml
# contexts/production.yaml
name: production
description: Production with read-only tools
enabled_tools:
  - query
  - search
disabled_tools:
  - delete
  - rebuild

tool_config_overrides:
  query:
    timeout: 5000
```

```yaml
# contexts/development.yaml
name: development
description: All tools enabled
enabled_tools: []  # Empty = all
disabled_tools: []
```

Load contexts:

```python
from nisaba import MCPContext

ctx = MCPContext.load("production")
config = MyConfig(server_name="my_app", context=ctx)
```

### Augments: The Novel Part

**What are augments?**

Markdown files in `.nisaba/augments/` that get dynamically injected into system prompts:

```
.nisaba/augments/
  architecture/
    layer_detection.md
    coupling_analysis.md
  refactoring/
    impact_analysis.md
    clone_consolidation.md
  foundation/
    call_graph_analysis.md
```

**Each augment contains:**
- Conceptual knowledge (e.g., "what is coupling")
- Operational patterns (e.g., "how to detect high coupling")
- Cypher query examples
- Best practices

**Load/unload dynamically:**

```python
# Activate specific augments
activate_augments(patterns=["architecture/*", "refactoring/impact_analysis"])

# Deactivate when done
deactivate_augments(patterns=["architecture/*"])

# Pin augments (always active, cannot be deactivated)
pin_augment(patterns=["foundation/*"])

# Learn new augment
learn_augment(
    group="custom",
    name="my_pattern",
    content="# My Pattern\n\nPattern description..."
)
```

**How it works:**

1. Augments stored as `.md` files
2. `activate_augments()` → writes to `.nisaba/nisaba_composed_augments.md`
3. Proxy detects file `mtime` change
4. Next API call → proxy injects augments into system prompt
5. LLM perceives new knowledge without explicit reload

**Dependency resolution:**

```markdown
<!-- my_augment.md -->
**REQUIRES:** foundation/call_graph_analysis

# My Augment
Content here...
```

Activating `my_augment` automatically loads `foundation/call_graph_analysis`.

### Workspace State

Nisaba maintains persistent state across conversation turns:

**File Windows:**
```python
# Open code snippet (persists across turns)
file_windows.open_frame(frame_path="AuthService")
file_windows.open_range(file_path="auth.py", start=10, end=50)

# Update window
file_windows.update(window_id="abc123", start=15, end=60)

# Close window
file_windows.close(window_id="abc123")
```

**Structural View:**
```python
# Navigate tree
structural_view(operation="expand", path="nabu.mcp.tools")
structural_view(operation="collapse", path="nabu.mcp")

# Search (adds markers, preserves navigation)
structural_view(operation="search", query="database connection")

# Clear search markers
structural_view(operation="clear_search")

# Reset tree
structural_view(operation="reset", depth=2)
```

**Tool Result Windows:**
```python
# Created automatically by:
nisaba_read(file_path="auth.py")
nisaba_grep(pattern="class", path="src/")
nisaba_bash(command="ls -la")

# Accumulate like IDE terminal history
# Close when done:
nisaba_tool_windows.close(window_id="def456")
```

**All state persists to `.nisaba/*.json` files and survives restarts.**

### Proxy Architecture

The proxy intercepts HTTP requests to `api.anthropic.com`:

```
Claude CLI → mitmproxy (port 1337) → Anthropic API
                ↓
        Inject sections:
        - USER_SYSTEM_PROMPT_INJECTION
        - AUGMENTS
        - STRUCTURAL_VIEW
        - FILE_WINDOWS
        - TOOL_RESULT_WINDOWS
        - NOTIFICATIONS
        - TODOS
```

**Start unified server:**

```python
from nisaba.wrapper import UnifiedNisabaServer

server = UnifiedNisabaServer(
    augments_dir=Path(".nisaba/augments"),
    composed_file=Path(".nisaba/nisaba_composed_augments.md"),
    proxy_port=1337,
    mcp_port=9973,
    debug_proxy=False
)

server.start()
# Runs: proxy + MCP server in background
```

**Or via CLI:**

```bash
python -m nisaba.wrapper.claude

# Starts:
# 1. mitmproxy on port 1337
# 2. Nisaba MCP server on port 9973
# 3. Claude CLI with HTTPS_PROXY=localhost:1337
```

### Workflow Guidance

**Pattern-based suggestions** that teach optimal tool usage:

```python
from nisaba import GuidanceGraph, GuidancePattern

def no_map_yet(history):
    return len(history) >= 3 and not any(e["tool"] == "map" for e in history)

MY_GUIDANCE = GuidanceGraph(
    patterns=[
        GuidancePattern(
            name="start_with_map",
            condition=no_map_yet,
            suggestion="map() - Get project overview first",
            reason="Mapping provides essential context",
            priority="HIGH"
        )
    ]
)

# Enable in factory
class MyFactory(MCPFactory):
    def __init__(self, config):
        super().__init__(config)
        self.guidance = WorkflowGuidance(MY_GUIDANCE)
```

**Tool responses include guidance:**

```json
{
  "success": true,
  "data": "...",
  "_guidance": {
    "suggestion": "map() - Get project overview first",
    "reason": "Mapping provides essential context",
    "priority": "HIGH"
  }
}
```

---

## Complete Example

See [Nabu](../../README.md) for a real-world implementation using all nisaba features:
- Auto-discovery (15+ tools)
- Augment system (50+ augments organized in groups)
- Workspace state (file windows, structural view, tool results)
- Workflow guidance (18+ patterns)
- Proxy integration (dynamic context injection)

---

## Architecture Deep Dive

### Component Hierarchy

```
MCPFactory
  ├─ MCPConfig (server settings, tool filtering)
  ├─ ToolRegistry (auto-discovery, markers)
  ├─ AugmentManager (load/unload/persist augments)
  └─ WorkflowGuidance (pattern-based suggestions)

UnifiedNisabaServer
  ├─ NisabaMCPFactory (nisaba tools: augments, file_windows, ...)
  ├─ mitmproxy (AugmentInjector addon)
  └─ MCP server (stdio transport)

AugmentInjector (mitmproxy addon)
  ├─ FileCache (augments, system_prompt, structural_view, ...)
  ├─ mtime detection (auto-reload on file change)
  └─ system prompt mutation (inject sections)
```

### File Structure

```
project/
├── .nisaba/
│   ├── augments/                      # Augment library
│   │   ├── foundation/
│   │   ├── architecture/
│   │   └── custom/
│   ├── nisaba_composed_augments.md    # Active augments
│   ├── system_prompt.md               # Custom instructions
│   ├── structural_view.md             # Tree state
│   ├── file_windows.md                # Open snippets
│   ├── tool_result_windows.md         # Tool outputs
│   ├── todos.md                       # Task list
│   ├── notifications.md               # Tool feedback
│   ├── file_windows_state.json        # Persistence
│   ├── structural_view_state.json     # Persistence
│   └── augment_state.json             # Active augments
└── src/
    └── my_project/
        └── mcp/
            ├── tools/                  # Auto-discovered
            │   ├── query.py
            │   └── search.py
            ├── config/
            │   ├── contexts/           # YAML configs
            │   └── my_config.py
            ├── factory.py
            └── server.py
```

### State Flow

```
Tool Call (e.g., activate_augments)
  ↓
AugmentManager.activate_augments()
  ↓
Write to .nisaba/nisaba_composed_augments.md
  ↓
mtime changes
  ↓
Next API request
  ↓
AugmentInjector detects mtime
  ↓
FileCache.load() → read file
  ↓
Inject into request body["system"]
  ↓
Anthropic API receives augmented prompt
  ↓
LLM response with new perception
```

---

## Response Format

Standardized across all tools:

**Success:**
```json
{
  "success": true,
  "data": {"key": "value"},
  "execution_time_ms": 42.0,
  "warnings": ["Optional warning"],
  "metadata": {"extra": "info"},
  "_guidance": {
    "suggestion": "Next optimal action",
    "reason": "Why this matters",
    "priority": "HIGH"
  }
}
```

**Error:**
```json
{
  "success": false,
  "error": "Invalid parameter",
  "severity": "WARNING",
  "recovery_hint": "Check your input",
  "context": {"param": "bad_value"},
  "execution_time_ms": 10.5
}
```

---

## Philosophy

> **"Organize the tools that inscribe wisdom."**

### Design Principles

- **Auto-discovery over manual registration** - Find tools automatically
- **Context over configuration** - YAML-based environment control
- **Markers over inheritance** - Simple decorators for behavior
- **Spatial over sequential** - Workspace state, not conversation history
- **Perception as mutable** - Augments change cognition, not just knowledge

### What Nisaba Is NOT

- **Not a general MCP library** - Opinionated patterns, not kitchen sink
- **Not production-ready** - Research prototype, expect changes
- **Not framework-agnostic** - Designed for Anthropic Claude + MCP
- **Not stable API** - v0.1-alpha = experimental

### What Nisaba IS

- **Research artifact** - Exploring LLM-agent cognition models
- **Enabler for Nabu** - Sister project proving the framework works
- **Novel paradigm** - Dynamic context injection, workspace state
- **Open for feedback** - MIT licensed, contributions welcome

---

## Comparison

| Feature | Nisaba | FastMCP | Serena MCP | Standard MCP |
|---------|--------|---------|------------|--------------|
| **Tool auto-discovery** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Augment system** | ✅ Unique | ❌ No | ❌ No | ❌ No |
| **Workspace state** | ✅ Yes | ❌ No | ⚠️ Partial | ❌ No |
| **Proxy injection** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Workflow guidance** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Context filtering** | ✅ YAML | ⚠️ Manual | ⚠️ Manual | ❌ No |
| **Maturity** | 🟡 Alpha | 🟢 Stable | 🟢 Stable | 🟢 Standard |

**Nisaba's niche:** Research prototype for dynamic LLM cognition, not general production MCP framework.

---

## Known Limitations

- ⚠️ Requires mitmproxy (additional dependency)
- ⚠️ Proxy approach is Anthropic-specific (API format assumptions)
- ⚠️ File-based state can get stale (no auto-refresh)
- ⚠️ Augment system is prototype (no version management)
- ⚠️ Performance not optimized (research code)
- ⚠️ Test coverage is basic

---

## Roadmap

**Short-term (v0.2):**
- [ ] Better augment organization (categories, tags)
- [ ] Auto-refresh file windows on file change
- [ ] Augment version management
- [ ] More workflow patterns

**Medium-term (v0.3):**
- [ ] Plugin system for state providers
- [ ] Alternative backends (not just Anthropic)
- [ ] Workspace state visualization
- [ ] Performance optimization

**Long-term (research):**
- [ ] Multi-agent workspace sharing
- [ ] Augment composition language
- [ ] Formal cognitive model

---

## Name Etymology

### Nisaba (Sumerian: 𒀭𒉀)

Mesopotamian goddess of writing, learning, and harvest (3rd millennium BCE).

**Her role:**
- Writing and accounting
- Organization and record-keeping  
- Grain harvest and gathering
- Patron of scribes
- Sister of Nabu

**The parallel:**

| Ancient Nisaba | Modern Nisaba |
|----------------|---------------|
| Organized grain stores | Organizes tool registries |
| Maintained careful records | Maintains workspace state |
| Patron of scribes | Framework for MCP developers |
| Sister who supported Nabu | Sister framework to Nabu |

When you use Nisaba, you invoke the goddess who organized knowledge and supported scribes - just as this framework organizes tools and supports MCP server developers. 📜

---

## Sister Project

Nisaba was extracted from **[Nabu](../../README.md)**, a code analysis framework. Nabu was the first MCP server built with nisaba's patterns, proving the design.

If Nabu records wisdom about code, Nisaba provides the infrastructure to work with that wisdom.

---

## Contributing

Nisaba is a research prototype. Contributions welcome!

**Priority areas:**
- Additional tool markers
- More context examples
- Testing utilities  
- Documentation improvements
- Novel augment patterns
- Alternative proxy backends

**How to contribute:**
1. Fork repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

---

## License

MIT License - See [LICENSE](../../LICENSE)

---

## Acknowledgments

- **MCP**: Model Context Protocol by Anthropic
- **mitmproxy**: HTTP proxy for interception
- **FastMCP**: MCP server foundation
- **Nabu**: Sister project and first real user
- **Claude**: Primary user, testing the paradigms

---

<p align="center">
  <em>"The patron of scribes organizes the tools of wisdom."</em><br>
  <em>— Honoring Nisaba</em>
</p>

<p align="center">
  <strong>Auto-discovery. Dynamic augmentation. Workspace persistence.</strong>
</p>

<p align="center">📜 ✨</p>
