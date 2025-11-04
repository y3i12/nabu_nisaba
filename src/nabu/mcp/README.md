# Nabu MCP Server

**Version:** Prototype → Production-Ready  
**Purpose:** Enable LLM agents to query codebases as structured knowledge graphs

---

## Table of Contents

1. [Overview](#overview)
2. [Philosophy & Design Goals](#philosophy--design-goals)
3. [Architecture](#architecture)
4. [The Frame Abstraction](#the-frame-abstraction)
5. [Database Schema](#database-schema)
6. [Configuration & Contexts](#configuration--contexts)
7. [Available Tools](#available-tools)
8. [Creating Custom Tools](#creating-custom-tools)
9. [Dynamic Instructions System](#dynamic-instructions-system)
10. [Tool Base Class Features](#tool-base-class-features)
11. [Best Practices](#best-practices)
12. [Migration Guide](#migration-guide)
13. [Testing](#testing)

---

## Overview

The nabu MCP server exposes nabu's code graph database through the Model Context Protocol (MCP), allowing LLM agents to:

- **Query code structure** using Cypher graph queries
- **Search code semantically** using full-text search with BM25 ranking
- **Update incrementally** when files change (no full re-parse needed)
- **Analyze relationships** across multiple languages in a unified way

This directory contains a **production-ready refactor** using modern software patterns:
- Factory pattern for lifecycle management
- Tool abstraction with auto-discovery
- Context-based configuration
- Zero global state

### What Makes This Special

Unlike traditional code analysis tools, nabu MCP provides:

1. **Language-agnostic abstraction** - Python functions, Java methods, Perl subroutines are all `CALLABLE`
2. **Graph-based queries** - Find not just "what" but "how things relate"
3. **Confidence system** - Explicitly models uncertainty in code analysis
4. **Incremental updates** - Fast updates when code changes (rare in AST tools)
5. **LLM-first design** - Built specifically for AI agents, not humans

---

## Philosophy & Design Goals

Nabu bridges the gap between **raw AST parsing** (too detailed) and **high-level semantic understanding** (too abstract). The design philosophy:

### "Ideally Abstract, Without Compromising Too Much"

- **Abstract enough** for language-agnostic queries
- **Concrete enough** to preserve essential details in `content` and `metadata`
- **Heuristics over perfection** - Accept some false positives for broad applicability
- **Relationships over entities** - Graph thinking first

### End Goals

1. **Queryable code representation** - Enable questions like "What calls this?" or "Where is this used?"
2. **Common language concepts** - Packages, classes, methods, scopes, control flow
3. **Semantic relationships** - CALLS, INHERITS, CONTAINS, IMPORTS edges
4. **LLM agent workflows** - Fast context gathering for code modifications

### Key Insight

> **"Very few queries of [`Glob`, `Read`, `Grep`] can be replaced by semantic queries working as a project-wide 'outline on steroids'"**

Traditional LLM coding agents spend enormous token budgets reading files sequentially. Nabu enables:
```
Instead of:  Glob *.py → Read 50 files → Grep for pattern
Use:         find_code "database connection" → query_relationships CALLS
```

**Token savings: 60-90%** for code understanding tasks.

---

## Architecture

### Directory Structure

```
src/nabu/mcp/
├── __init__.py                  # Package exports
├── server.py                    # CLI entry point (python -m nabu.mcp.server)
├── cli.py                       # Argument parsing
├── factory.py                   # Abstract NabuMCPFactory (interface)
├── factory_impl.py              # Concrete NabuMCPFactorySingleProcess
│
├── config/
│   ├── nabu_config.py           # Configuration dataclasses
│   └── contexts/                # YAML context files
│       ├── default.yml          # Production: all tools
│       ├── development.yml      # Dev: + observability tools
│       └── readonly.yml         # Safe: query-only tools
│
├── tools/
│   ├── base.py                  # NabuTool abstract base class
│   ├── markers.py               # Tool behavior markers
│   ├── registry.py              # Auto-discovery registry
│   ├── query_tool.py            # Cypher query execution
│   ├── fts_tools.py             # Full-text search (2 variants)
│   ├── reindex_tool.py          # Full database rebuild
│   ├── incremental_tool.py      # File-level updates
│   └── observability_tools.py   # show_stats, check_status
│
├── utils/
│   ├── snippet_extractor.py    # Token-efficient code snippets
│   └── response_helpers.py     # Standardized responses
│
└── resources/
    └── instructions_template.md # Dynamic AI assistant instructions
```

### Core Design Principles

#### 1. **No Global State**

**Problem:** Global variables make testing hard and create hidden dependencies.

**Solution:** All state lives in `NabuMCPFactory` instance:

```python
class NabuTool(ABC):
    def __init__(self, factory: NabuMCPFactory):
        self.factory = factory
        self.config = factory.config          # Access to configuration
        self.db_manager = factory.db_manager  # Access to database
```

**Benefits:**
- Easy testing (inject mock factory)
- No initialization order issues
- Clear dependency graph

#### 2. **Tool Abstraction**

**Pattern:** Each tool is a class inheriting from `NabuTool`

```python
class QueryTool(NabuTool):
    async def execute(self, cypher_query: str) -> Dict[str, Any]:
        """Execute Cypher queries against KuzuDB."""
        # Tool logic here
```

**Benefits:**
- Centralized error handling in base class
- Auto-generated JSON schema from type hints
- Consistent response format
- Easy to add new tools (just create a class)

#### 3. **Factory Pattern**

**Responsibilities:**
- Database lifecycle management (startup/shutdown)
- Tool instantiation and registration
- Configuration loading
- Dynamic instruction generation

```python
async with factory.server_lifespan(mcp):
    # Database initialized
    # Tools registered
    # Server running
    pass
# Database closed, resources cleaned up
```

#### 4. **Context-Based Configuration**

**Problem:** Different use cases need different tool sets

**Solution:** YAML contexts specify enabled/disabled tools:

```yaml
# contexts/readonly.yml
name: readonly
enabled_tools: [query_relationships, find_code, fts_raw_query]
disabled_tools: [rebuild_database, incremental_update]
```

**Benefits:**
- Production safety (disable dangerous tools)
- Development productivity (enable debug tools)
- Clear separation of concerns

#### 5. **Auto-Discovery Registry**

**Magic:** Tool classes auto-register themselves

```python
# Just create the class - no manual registration needed!
class MyNewTool(NabuTool):
    async def execute(self, param: str):
        pass
```

The registry finds all `NabuTool` subclasses automatically using Python introspection.

---

## The Frame Abstraction

### Why "Frames" Instead of Language-Specific Entities?

**Traditional approach (doesn't scale):**
- Python: `Function`, `Class`, `Method`, `Module`
- Java: `Method`, `Class`, `Package`, `Interface`
- C++: `Function`, `Class`, `Namespace`, `Struct`
- Result: 4 languages × 20 entity types = 80 node types 😱

**Nabu approach (scales beautifully):**
- All languages: `CALLABLE`, `CLASS`, `PACKAGE`
- Result: 3 core types for all languages ✨

### Frame Type Hierarchy

```
CODEBASE (root)
  └─ LANGUAGE (python_root, cpp_root, java_root, perl_root)
      └─ PACKAGE (module, namespace, package)
          └─ CLASS (class, struct, interface, enum)
              └─ CALLABLE (function, method, lambda)
                  └─ Control Flow (IF_BLOCK, FOR_LOOP, TRY_BLOCK, ...)
```

### Frame Types Explained

#### Structural Frames (Core Hierarchy)

- **`CODEBASE`** - Root node (one per database)
- **`LANGUAGE`** - Language root (e.g., `python_root`)
- **`PACKAGE`** - Organizational unit
  - Python: module
  - Java: package
  - C++: namespace
  - Perl: package
- **`CLASS`** - Type definition
  - Python: class
  - Java: class, interface, enum
  - C++: class, struct, union, enum
- **`CALLABLE`** - Executable code
  - Python: function, method, lambda
  - Java: method, constructor
  - C++: function, method
  - Perl: subroutine

#### Control Flow Frames

- **`IF_BLOCK`**, **`ELIF_BLOCK`**, **`ELSE_BLOCK`** - Conditionals
- **`FOR_LOOP`**, **`WHILE_LOOP`** - Iteration
- **`TRY_BLOCK`**, **`EXCEPT_BLOCK`**, **`FINALLY_BLOCK`** - Exception handling
- **`SWITCH_BLOCK`**, **`CASE_BLOCK`** - Switch statements (includes Python `match`)
- **`WITH_BLOCK`** - Context managers (Python `with`)

### Benefits of Frame Abstraction

1. **Language-agnostic queries**
   ```cypher
   // Find all functions that call logging functions
   // Works for Python, Java, C++, Perl!
   MATCH (caller:Frame {type: 'CALLABLE'})-[:Edge {type: 'CALLS'}]->(callee:Frame)
   WHERE callee.name CONTAINS 'log'
   RETURN caller.qualified_name
   ```

2. **Simpler schema** - 15 frame types vs 80+ language-specific types

3. **Language details preserved** - Check `content` for exact syntax:
   ```python
   # Frame shows: type='CALLABLE', name='parse'
   # Content shows: 'def parse(self, input: str) -> AST:'
   ```

4. **False positives acceptable** - Heuristics over perfection
   - 95% accurate is better than 60% slow & complex

---

## Database Schema

### Tables

#### Frame (NODE)

**20 properties** storing code structure:

| Property | Type | Description |
|----------|------|-------------|
| `id` | STRING | Stable SHA256-based identifier (primary key) |
| `type` | STRING | Frame type (CALLABLE, CLASS, etc.) |
| `name` | STRING | Simple name (e.g., `parse`) |
| `qualified_name` | STRING | Fully qualified (e.g., `Parser.parse`) |
| `confidence` | FLOAT | Numeric confidence (0.0-1.0) |
| `confidence_tier` | STRING | HIGH, MEDIUM, LOW, SPECULATIVE |
| `provenance` | STRING | How frame was created (AST, inference, etc.) |
| `resolution_pass` | INT32 | Which parsing pass created it (1-4+) |
| `language` | STRING | Source language (python, cpp, java, perl) |
| `file_path` | STRING | Absolute path to source file |
| `start_line`, `end_line` | INT32 | Line range in file |
| `start_byte`, `end_byte` | INT32 | Byte range in file |
| `content` | STRING | Source code text |
| `instance_fields` | STRUCT[] | Class instance variables |
| `static_fields` | STRUCT[] | Class static/class variables |
| `parameters` | STRUCT[] | Function/method parameters |
| `return_type` | STRING | Return type annotation |
| `metadata` | STRING | JSON extra data |

#### Edge (REL)

**4 properties** describing relationships:

| Property | Type | Description |
|----------|------|-------------|
| `type` | STRING | Edge type (CALLS, CONTAINS, etc.) |
| `confidence` | FLOAT | Numeric confidence (0.0-1.0) |
| `confidence_tier` | STRING | HIGH, MEDIUM, LOW, SPECULATIVE |
| `metadata` | STRING | JSON extra data |

### Edge Types

- **`CONTAINS`** - Hierarchical parent-child (e.g., class contains method)
- **`CALLS`** - Function/method invocation
- **`INHERITS`** - Class inheritance
- **`IMPORTS`** - Import/include statements
- **`IMPLEMENTS`** - Interface implementation (Java)

### Example Database Statistics

From a typical nabu database (this repository):

```
Total Frames: 2,730
  CALLABLE:     1,012  (37%)  - Functions, methods
  IF_BLOCK:       883  (32%)  - Conditionals
  FOR_LOOP:       242  (9%)   - Loops
  CLASS:          100  (4%)   - Classes
  EXCEPT_BLOCK:    92  (3%)   - Exception handlers
  TRY_BLOCK:       87  (3%)   - Try blocks
  ELSE_BLOCK:      76  (3%)   - Else branches
  PACKAGE:         71  (3%)   - Modules/packages
  WITH_BLOCK:      59  (2%)   - Context managers
  [others]:       108  (4%)

Total Edges: 4,433
  CONTAINS: 2,696  (61%)  - Hierarchy
  CALLS:    1,612  (36%)  - Function calls
  IMPORTS:     87  (2%)   - Import statements
  INHERITS:    38  (1%)   - Class inheritance
```

### Confidence System

Nabu uses a **multi-pass resolution** system with confidence tiers:

#### Pass 1: Direct AST Parsing (HIGH confidence, 1.0)
- Extract functions, classes, imports directly from AST
- No ambiguity, directly observable

#### Pass 2: Cross-Reference Resolution (MEDIUM confidence, 0.6-0.9)
- Resolve import statements
- Match function calls to definitions
- Uses symbol tables

#### Pass 3: Type Inference (LOW confidence, 0.3-0.6)
- Infer types from usage
- Heuristic matching for dynamic languages

#### Pass 4+: Fuzzy Resolution (SPECULATIVE confidence, 0.1-0.3)
- External library references
- Dynamic calls (Python `getattr`, C++ function pointers)

**Why confidence matters:**

Agents can filter results by confidence:
```cypher
// High-confidence calls only
MATCH (a)-[e:Edge {type: 'CALLS'}]->(b)
WHERE e.confidence > 0.8
RETURN a.qualified_name, b.qualified_name
```

---

## Configuration & Contexts

### Context Files

Located in `config/contexts/*.yml`, contexts control which tools are available.

#### `default.yml` (Production)

```yaml
name: default
description: Standard nabu MCP tools

enabled_tools:
  - query_relationships  # Cypher queries
  - find_code           # Full-text search with snippets
  - fts_raw_query       # Full-text search raw results
  - rebuild_database    # Full database rebuild
  - incremental_update  # File-level updates

disabled_tools: []
```

**Use when:** Normal operation, trusted environment

#### `development.yml` (Development)

```yaml
name: development
description: Development mode with observability

enabled_tools:
  - query_relationships
  - find_code
  - fts_raw_query
  - rebuild_database
  - incremental_update
  - show_stats         # Database statistics (dev only)
  - check_status       # Connection diagnostics (dev only)

disabled_tools: []
```

**Use when:** Debugging, performance analysis, development

#### `readonly.yml` (Safe)

```yaml
name: readonly
description: Read-only access (no mutations)

enabled_tools:
  - query_relationships
  - find_code
  - fts_raw_query

disabled_tools:
  - rebuild_database   # No database rebuilds
  - incremental_update # No modifications
```

**Use when:** Untrusted environment, analysis-only, CI/CD

### Usage

```bash
# Production
python -m nabu.mcp.server --db-path ./nabu.kuzu --repo-path ./src/

# Development (with debug logging)
python -m nabu.mcp.server --db-path ./nabu.kuzu --repo-path ./src/ \
  --context development --dev-mode --log-level DEBUG

# Read-only (safe)
python -m nabu.mcp.server --db-path ./nabu.kuzu --repo-path ./src/ \
  --context readonly
```

---

## Available Tools

### Query & Analysis Tools

#### `query` - Cypher Query Execution

Execute graph queries against the KuzuDB database.

**Parameters:**
- `cypher_query` (string, required): Cypher query to execute

**Example:**
```cypher
// Find all classes
MATCH (c:Frame {type: 'CLASS'}) RETURN c.name, c.file_path LIMIT 10

// Find call relationships
MATCH (caller)-[:Edge {type: 'CALLS'}]->(callee)
RETURN caller.qualified_name, callee.qualified_name
```

#### `find_code` - Full-Text Search with Snippets

Search code using BM25 full-text search, returns context snippets around matches.

**Parameters:**
- `keywords` (string, required): Space-separated search terms
- `conjunctive` (boolean, default: false): AND logic if true, OR if false
- `K` (float, default: 1.2): BM25 term frequency saturation (0.1-5.0)
- `B` (float, default: 0.75): BM25 length normalization (0.0-1.0)
- `top` (int, default: 25): Maximum results
- `frame_type_filter` (string, optional): Regex to filter frame types (e.g., "CALLABLE|CLASS")
- `context_lines` (int, default: 3): Lines of context around matches
- `max_snippets` (int, default: 5): Max snippet windows per result
- `compact_metadata` (boolean, default: true): Remove rarely-used fields

**Example:**
```python
# Find database connection code
find_code(keywords="database connection", frame_type_filter="CALLABLE")

# Find error handling
find_code(keywords="try except error", conjunctive=True)
```

**Token efficiency:** 60-70% reduction vs. raw results

#### `fts_raw_query` - Full-Text Search (Raw Results)

Same as `find_code` but returns complete frame data without snippet extraction.

**Use when:** Need full frame content, not just matches

### Database Management Tools

#### `rebuild_database` - Full Database Rebuild

Rebuild entire database from scratch by re-parsing all files.

**Parameters:** None

**Use when:**
- Database corrupted
- Schema changes
- Initial database creation

**Warning:** Slow operation (minutes for large codebases)

#### `incremental_update` - File-Level Update

Update database for a single modified file without full rebuild.

**Parameters:**
- `file_path` (string, required): Absolute or relative path to changed file

**Example:**
```python
# File was edited
incremental_update(file_path="src/nabu/core/frames.py")
```

**Benefits:**
- Fast (seconds vs. minutes)
- Surgical updates
- Automatic edge repair

### Observability Tools (Dev Mode Only)

#### `show_stats` - Database Statistics

Returns connection pool stats, table sizes, index information.

**Parameters:** None

#### `check_status` - Connection Health

Tests database connectivity and basic query execution.

**Parameters:** None

**Returns:** Frame count, connection status, diagnostics

---

## Creating Custom Tools

### Step-by-Step Guide

#### Step 1: Create Tool Class

Create a new file in `tools/` directory:

```python
# tools/complexity_tool.py

from typing import Any, Dict
import time
from .base import NabuTool

class ComplexityTool(NabuTool):
    """Calculate cyclomatic complexity for functions."""
    
    async def execute(
        self,
        qualified_name: str,
        threshold: int = 10
    ) -> Dict[str, Any]:
        """
        Calculate cyclomatic complexity for a function.
        
        Args:
            qualified_name: Fully qualified function name
            threshold: Complexity threshold for warnings
            
        Returns:
            JSON object with complexity score and warnings
        """
        start_time = time.time()
        
        try:
            # Query for function and its control flow children
            query = """
            MATCH (func:Frame {qualified_name: $qname, type: 'CALLABLE'})
            OPTIONAL MATCH (func)-[:Edge {type: 'CONTAINS'}]->(child:Frame)
            WHERE child.type IN ['IF_BLOCK', 'FOR_LOOP', 'WHILE_LOOP', 
                                 'EXCEPT_BLOCK', 'CASE_BLOCK']
            RETURN func.name as name, count(child) + 1 as complexity
            """
            
            result = self.db_manager.execute(
                query,
                {"qname": qualified_name}
            )
            
            df = result.get_as_df()
            
            if df.empty:
                return self._error_response(
                    ValueError(f"Function not found: {qualified_name}"),
                    start_time,
                    recovery_hint="Check qualified_name spelling. Use find_code to find functions."
                )
            
            complexity = int(df.iloc[0]['complexity'])
            warnings = []
            
            if complexity > threshold:
                warnings.append(
                    f"Complexity {complexity} exceeds threshold {threshold}"
                )
            
            return self._success_response(
                data={
                    "qualified_name": qualified_name,
                    "complexity": complexity,
                    "threshold": threshold,
                    "exceeded": complexity > threshold
                },
                start_time=start_time,
                warnings=warnings if warnings else None
            )
        
        except Exception as e:
            return self._error_response(e, start_time)
```

#### Step 2: Export Tool

Add to `tools/__init__.py`:

```python
from .complexity_tool import ComplexityTool

__all__ = [
    # ... existing ...
    "ComplexityTool",
]
```

#### Step 3: Add to Context

Create or modify a context file:

```yaml
# contexts/analysis.yml
name: analysis
description: Code analysis tools

enabled_tools:
  - query_relationships
  - find_code
  - complexity  # Auto-generated from ComplexityTool
```

#### Step 4: Run It

```bash
python -m nabu.mcp.server --db-path ./nabu.kuzu --repo-path ./src/ --context analysis
```

The tool is now available to LLM agents!

### Tool Markers

Modify tool behavior with marker classes (imported from nisaba):

```python
from nisaba import ToolMarkerOptional, ToolMarkerDevOnly, ToolMarkerMutating

# Optional tool (disabled by default)
class MyTool(NabuTool, ToolMarkerOptional):
    pass

# Dev-only tool
class DebugTool(NabuTool, ToolMarkerDevOnly):
    pass

# Mutating tool (modifies database)
class UpdateTool(NabuTool, ToolMarkerMutating):
    pass

# Combine markers
class OptionalDevTool(NabuTool, ToolMarkerOptional, ToolMarkerDevOnly):
    pass
```

**Note:** Markers are provided by the Nisaba framework and should be imported directly from `nisaba`.

---

## Dynamic Instructions System

### Overview

Nabu automatically generates **context-aware instructions** for LLM agents based on:
- Available tools (per context)
- Database statistics
- Language support
- Query examples

### Template System

Located: `resources/instructions_template.md`

**Placeholders:**
- `{{CONTEXT_INFO}}` - Active context name
- `{{DATABASE_STATS}}` - Database path, size
- `{{TOOL_DOCUMENTATION}}` - Auto-generated tool docs
- `{{SCHEMA_DOCUMENTATION}}` - Frame/Edge schema
- `{{TYPE_STATISTICS}}` - Frame type distribution
- `{{QUERY_EXAMPLES}}` - Example Cypher queries
- `{{CONFIDENCE_INFO}}` - Confidence system explanation

### Auto-Generated Tool Documentation

The factory automatically generates markdown documentation for each enabled tool:

```python
def _generate_tool_documentation(self) -> str:
    """Generate markdown documentation for all enabled tools."""
    for tool_name in enabled_tools:
        tool_class = self.registry.get_tool_class(tool_name)
        schema = tool_class.get_tool_schema()  # Auto-generated!
        
        # Format as markdown
        # - Extract description from docstring
        # - Format parameters from type hints
        # - Add defaults, required markers
```

**Example output:**

```markdown
### Query & Analysis Tools

**`query`** - Execute Cypher queries against the KuzuDB graph database.

**Parameters:**
- `cypher_query` (string) *(required)*: The Cypher query string to execute against the database.

**`find_code`** - Execute full text search with compact snippet-based results.

**Parameters:**
- `keywords` (string) *(required)*: Space-separated search keywords.
- `top` (integer) *(optional, default: 25)*: Maximum number of results to return.
```

### Benefits

1. **Always up-to-date** - Instructions reflect actual available tools
2. **Context-aware** - Readonly context won't show mutation tools
3. **Self-documenting** - Docstrings become user-facing documentation
4. **Consistent** - Same format for all tools

---

## Tool Base Class Features

### Auto-Schema Generation

The `NabuTool` base class automatically generates MCP-compatible JSON schemas from Python:

```python
class QueryTool(NabuTool):
    async def execute(self, cypher_query: str) -> Dict[str, Any]:
        """
        Execute Cypher queries against KuzuDB.
        
        Args:
            cypher_query: The Cypher query to execute
            
        Returns:
            JSON object with query results
        """
        pass
```

**Automatically generates:**

```json
{
  "name": "query",
  "description": "Execute Cypher queries against KuzuDB.\n\nReturns: JSON object with query results",
  "parameters": {
    "type": "object",
    "properties": {
      "cypher_query": {
        "type": "string",
        "description": "The Cypher query to execute."
      }
    },
    "required": ["cypher_query"]
  }
}
```

### How It Works

1. **Introspection** - Uses Python's `inspect` and `typing` modules
2. **Docstring parsing** - Extracts descriptions with `docstring_parser` library
3. **Type mapping** - Converts Python types to JSON Schema types:
   - `str` → `"string"`
   - `int` → `"integer"`
   - `float` → `"number"`
   - `bool` → `"boolean"`
   - `List[T]` → `"array"`
   - `Dict[K,V]` → `"object"`
   - `Optional[T]` → type T with no required marker

### Standardized Responses

All tools return consistent response format:

**Success:**
```json
{
  "success": true,
  "data": { /* tool-specific data */ },
  "execution_time_ms": 45.2,
  "warnings": ["Optional warning messages"],
  "metadata": { /* optional metadata */ }
}
```

**Error:**
```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_type": "ValueError",
  "execution_time_ms": 12.1,
  "severity": "ERROR",
  "recovery_hint": "Try doing X instead",
  "context": { /* error context data */ }
}
```

### Error Severity Levels

```python
class ErrorSeverity(Enum):
    WARNING = "WARNING"      # Non-fatal, tool succeeded
    ERROR = "ERROR"          # Tool failed, retry may work
    FATAL = "FATAL"          # Tool failed, system issue
```

**Usage:**

```python
return self._error_response(
    error=e,
    start_time=start_time,
    severity=ErrorSeverity.FATAL,
    recovery_hint="Database connection lost. Restart MCP server.",
    context={"db_path": str(self.config.db_path)}
)
```

### Built-in Timing

All tools automatically track execution time:

```python
async def execute(self, param: str):
    start_time = time.time()
    try:
        # Do work
        return self._success_response(data, start_time)
    except Exception as e:
        return self._error_response(e, start_time)
```

---

## Best Practices

### For Tool Developers

1. **Write good docstrings** - They become user documentation
   ```python
   async def execute(self, param: str) -> Dict[str, Any]:
       """
       One-line summary.
       
       Detailed explanation of what the tool does.
       
       Args:
           param: What this parameter means
           
       Returns:
           What the tool returns
       """
   ```

2. **Use type hints** - They generate the JSON schema
   ```python
   async def execute(
       self,
       keywords: str,          # Required (no default)
       top: int = 25,          # Optional (has default)
       filters: Optional[List[str]] = None  # Optional
   ):
   ```

3. **Provide recovery hints** - Help agents fix errors
   ```python
   return self._error_response(
       error=e,
       recovery_hint="Try using find_code to find the function first"
   )
   ```

4. **Add context to errors** - Include debug info
   ```python
   return self._error_response(
       error=e,
       context={
           "query": cypher_query[:200],
           "db_path": str(self.config.db_path)
       }
   )
   ```

### For MCP Server Operators

1. **Use readonly context** for untrusted environments
2. **Enable dev mode** only in development
3. **Monitor execution times** - Most queries should be <100ms
4. **Set appropriate log levels** - INFO for production, DEBUG for development

### For LLM Agents

1. **Start with FTS** - Use `find_code` for discovery
   ```python
   # Find authentication code
   find_code(keywords="authentication login", frame_type_filter="CALLABLE")
   ```

2. **Follow with Cypher** - Use `query` for relationships
   ```cypher
   // Find what calls the login function
   MATCH (login:Frame {name: 'login'})<-[:Edge {type: 'CALLS'}]-(caller)
   RETURN caller.qualified_name, caller.file_path
   ```

3. **Verify with content** - Check frame `content` for exact code
   ```cypher
   MATCH (f:Frame {qualified_name: 'Parser.parse'})
   RETURN f.content
   ```

4. **Filter by confidence** - Focus on high-confidence relationships
   ```cypher
   MATCH ()-[e:Edge {type: 'CALLS'}]->()
   WHERE e.confidence > 0.8
   RETURN ...
   ```

5. **Use incremental updates** - After code changes
   ```python
   incremental_update(file_path="src/modified_file.py")
   ```

---

## Migration Guide

### From `local_server.py` (Old) to Factory Pattern (New)

#### Old Pattern (Global State)

```python
_db_manager = None  # Global variable

@mcp.tool()
async def my_tool(param: str) -> Dict[str, Any]:
    global _db_manager
    
    if _db_manager is None:
        raise RuntimeError("Not initialized")
    
    try:
        result = _execute_query(f"MATCH (n) WHERE n.name = '{param}' RETURN n")
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def main():
    global _db_manager
    _db_manager = KuzuConnectionManager.get_instance(db_path)
    mcp.run()
```

#### New Pattern (Factory)

```python
class MyTool(NabuTool):
    """My tool description."""
    
    async def execute(self, param: str) -> Dict[str, Any]:
        """
        Execute my tool.
        
        Args:
            param: Parameter description
            
        Returns:
            Success/error response
        """
        start_time = time.time()
        
        try:
            # Access via self.db_manager (no global!)
            result = self.db_manager.execute(
                f"MATCH (n) WHERE n.name = '{param}' RETURN n"
            )
            
            return self._success_response({"result": result}, start_time)
        
        except Exception as e:
            return self._error_response(e, start_time)

# Factory handles initialization automatically
async def main():
    config = NabuConfig(db_path=db_path, repo_path=repo_path)
    factory = NabuMCPFactorySingleProcess(config)
    mcp = factory.create_mcp_server()
    
    async with factory.server_lifespan(mcp):
        # Database initialized automatically
        mcp.run()
```

### Key Differences

| Old | New | Benefit |
|-----|-----|---------|
| Global `_db_manager` | `self.db_manager` | Testable |
| Manual init/cleanup | Factory lifecycle | Reliable |
| `@mcp.tool()` decorator | Class inheritance | Structured |
| Manual error handling | `_error_response()` | Consistent |
| No timing | Automatic timing | Monitoring |
| Manual schema | Auto-generated | DRY principle |

---

## Testing

### Unit Testing Tools

```python
import pytest
from nabu.mcp.config.nabu_config import NabuConfig, NabuContextConfig
from nabu.mcp.factory_impl import NabuMCPFactorySingleProcess

@pytest.mark.asyncio
async def test_query_tool(tmp_path):
    """Test query tool execution."""
    # Setup
    db_path = tmp_path / "test.kuzu"
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    
    # Create config
    context = NabuContextConfig(name="test", enabled_tools=["query"])
    config = NabuConfig(
        db_path=db_path,
        repo_path=repo_path,
        context=context
    )
    
    # Create factory and server
    factory = NabuMCPFactorySingleProcess(config)
    mcp = factory.create_mcp_server()
    
    # Test lifecycle
    async with factory.server_lifespan(mcp):
        # Database should be initialized
        assert factory.db_manager is not None
        
        # Get query tool
        from nabu.mcp.tools.query_tool import QueryTool
        tool = QueryTool(factory)
        
        # Execute query
        result = await tool.execute(cypher_query="MATCH (f:Frame) RETURN count(f)")
        
        # Verify
        assert result["success"] is True
        assert "data" in result
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_incremental_update_workflow(tmp_path):
    """Test full workflow with incremental updates."""
    # Setup database
    config = NabuConfig(db_path=tmp_path / "test.kuzu", repo_path=tmp_path / "repo")
    factory = NabuMCPFactorySingleProcess(config)
    
    # Create initial file
    (tmp_path / "repo").mkdir()
    test_file = tmp_path / "repo" / "test.py"
    test_file.write_text("def foo(): pass")
    
    async with factory.server_lifespan(factory.create_mcp_server()):
        # Reindex
        from nabu.mcp.tools.reindex_tool import RebuildDatabaseTool
        reindex = RebuildDatabaseTool(factory)
        result = await reindex.execute()
        assert result["success"]
        
        # Modify file
        test_file.write_text("def foo(): pass\ndef bar(): pass")
        
        # Incremental update
        from nabu.mcp.tools.incremental_tool import IncrementalUpdateTool
        incremental = IncrementalUpdateTool(factory)
        result = await incremental.execute(file_path=str(test_file))
        assert result["success"]
        
        # Verify changes
        from nabu.mcp.tools.query_tool import QueryTool
        query = QueryTool(factory)
        result = await query.execute(
            cypher_query="MATCH (f:Frame {type: 'CALLABLE'}) RETURN count(f) as cnt"
        )
        assert result["data"]["rows"][0]["cnt"] == 2  # foo and bar
```

### Testing Custom Tools

```python
@pytest.mark.asyncio
async def test_custom_tool(tmp_path):
    """Test custom tool implementation."""
    from nabu.mcp.tools.complexity_tool import ComplexityTool  # Your tool
    
    config = NabuConfig(db_path=tmp_path / "test.kuzu", repo_path=tmp_path / "repo")
    factory = NabuMCPFactorySingleProcess(config)
    
    async with factory.server_lifespan(factory.create_mcp_server()):
        tool = ComplexityTool(factory)
        
        result = await tool.execute(
            qualified_name="MyClass.my_method",
            threshold=10
        )
        
        assert result["success"]
        assert "complexity" in result["data"]
```

---

## Benefits of This Architecture

### 1. Maintainability
- **8 focused files** instead of 1 massive 1000+ line file
- **Clear separation** of concerns (tools, config, factory, utils)
- **Easy navigation** - know exactly where to look

### 2. Testability
- **No global state** - inject mock factory for testing
- **Each tool independent** - test in isolation
- **Lifecycle control** - setup/teardown handled by factory

### 3. Extensibility
- **Add tools easily** - just create a class
- **Auto-discovery** - no manual registration
- **Marker system** - modify tool behavior declaratively

### 4. Configuration
- **YAML-driven** tool selection
- **Context switching** - production, development, readonly
- **Override defaults** - per-deployment customization

### 5. Professional Quality
- **Industry patterns** - factory, dependency injection, abstraction
- **Type safety** - full type hints throughout
- **Error handling** - standardized responses with recovery hints
- **Observability** - timing, logging, health checks
- **Documentation** - auto-generated from code

---

## Comparison to Alternatives

| Feature | Nabu MCP | LSP Servers | Raw AST Tools | Neo4j Code Graphs |
|---------|----------|-------------|---------------|-------------------|
| **Multi-language** | ✅ Abstract frames | ❌ Per-language | ❌ Per-language | ⚠️ Manual |
| **Graph queries** | ✅ Cypher | ❌ No | ❌ No | ✅ Cypher |
| **Incremental updates** | ✅ Stable IDs | ✅ Yes | ❌ Usually not | ❌ Usually not |
| **Confidence system** | ✅ 4-tier | ❌ No | ❌ No | ❌ No |
| **Full-text search** | ✅ BM25 | ⚠️ Limited | ❌ No | ⚠️ Manual |
| **LLM-optimized** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Token efficiency** | ✅ Snippets | ❌ N/A | ❌ N/A | ❌ N/A |
| **Relationships** | ✅ CALLS, INHERITS | ⚠️ Limited | ❌ Tree only | ✅ Flexible |
| **Setup complexity** | 🟢 Low | 🟡 Medium | 🟢 Low | 🔴 High |

**Verdict:** Nabu occupies a unique position - semantic enough for insights, abstract enough for queries, graph-based for relationships.

---

## Future Enhancements

### Planned

1. **Variable tracking** - USES edges from CALLABLE to variables
2. **Performance benchmarks** - Document scaling characteristics
3. **Graph algorithms** - PageRank, betweenness centrality
4. **Code metrics tools** - Complexity, coupling, cohesion
5. **Visualization exports** - GraphViz, D3.js, Mermaid

### Research

1. **Data flow analysis** - Track variable mutations, DEF-USE chains
2. **Type inference** - For dynamic languages (Python, Perl)
3. **Temporal graphs** - Version control integration, change tracking
4. **External library modeling** - Pre-index stdlib, JDK, STL

---

## Related Documentation

- **Core nabu:** `src/nabu/` - Frame abstraction, parsing, incremental updates
- **Database:** `src/nabu/db/` - KuzuDB connection management
- **Language handlers:** `src/nabu/language_handlers/` - Python, C++, Java, Perl
- **MCP specification:** https://modelcontextprotocol.io/

---

## Credits

**Philosophy:** *"The stylus of wisdom inscribes the tablets of understanding."*  
— Nabu, Ancient Mesopotamian God of Writing and Wisdom

Just as ancient Nabu recorded wisdom on tablets, modern Nabu records code structure in queryable graphs. 📜✨

---

**License:** See LICENSE file  
**Issues:** Report at project repository  
**Contributions:** PRs welcome!
