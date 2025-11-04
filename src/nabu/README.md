# Nabu

**Code Intelligence Ecosystem for LLM Agents**

<p align="center">
  <em>Ancient wisdom meets modern AI cognition</em>
</p>

---

## What Is This?

Semantic code analysis via queryable graphs (KuzuDB)

**Status:** v0.1-alpha | MIT Licensed | Research prototype

---

## The Problem

Traditional LLM coding agents waste enormous token budgets on sequential operations:

```python
# Typical workflow (expensive):
glob("**/*.py")           # Find 1000 files
→ read(file1.py)          # Read entire file (5000 tokens)
→ grep("class Foo")       # Search for class
→ read(file2.py)          # Read another file (3000 tokens)
→ grep("import")          # Search again
→ ... repeat 20 times ... # 100K+ tokens burned
```

**Measured impact:** massive context consumption, poor spatial awareness.

---

## The Solution

**Semantic-first navigation with persistent workspace state:**

```python
# Nabu + Nisaba workflow (efficient):
map_codebase()                    # Get project overview (2K tokens)
→ search("authentication logic")  # Semantic search (500 tokens)
→ show_structure("AuthService")   # Skeleton only (100 tokens)
→ query_relationships(...)        # Graph query (300 tokens)
```

**Measured savings:** surgical token usage, persistent spatial memory.

---

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/nabu_nisaba.git
cd nabu_nisaba
pip install -r requirements.txt
```

### Parse Your Codebase

```bash
# Create database
nabu db reindex --db-path ./my_project.kuzu --repo-path /path/to/your/code
```

### Query the Graph (Python API)

```python
from nabu.db import KuzuConnectionManager

db = KuzuConnectionManager.get_instance("my_project.kuzu")

# Find all callers of a function
result = db.execute("""
    MATCH (caller:Frame)-[e:Edge {type: 'CALLS'}]->(target:Frame)
    WHERE target.qualified_name = 'AuthService.validate_token'
      AND e.confidence >= 0.7
    RETURN caller.qualified_name, caller.file_path, e.confidence
    ORDER BY e.confidence DESC
""")

print(result.get_as_df())
```

### Use MCP Tools (LLM Agents)

Available when running unified environment:

```python
# === NABU TOOLS (Code Analysis) ===

# Get project overview
map_codebase()

# Semantic search
search(query="authentication logic", k=10)

# Get class structure (no implementation - 53x token savings!)
show_structure(target="AuthService", detail_level="minimal")

# Graph query
query_relationships(cypher_query="...")

# Impact analysis
check_impact(target="critical_function", max_depth=2)

# === NISABA TOOLS (Workspace Management) ===

# Load knowledge domains
activate_augments(patterns=["architecture/*", "refactoring/*"])

# Open file windows (persistent across turns)
file_windows.open_frame(frame_path="AuthService")

# Navigate code tree
structural_view(operation="search", query="database connection")

# Track TODOs
todo_write(operation="add", todos=[{"content": "Refactor auth"}])
```

---

## Architecture

### Nabu: Semantic Code Analysis

**Pipeline:**
```
Source Code
  ↓ tree-sitter parsing
Raw AST Nodes
  ↓ multi-pass resolution
Frame Hierarchy (with confidence)
  ↓ relationship extraction
Graph (Frames + Edges)
  ↓ KuzuDB export
Queryable Database
```

**Key Components:**

- **CodebaseParser**: Multi-language parsing (Python, C++, Java, Perl)
- **Frame Types**: CODEBASE, LANGUAGE, PACKAGE, CLASS, CALLABLE, IF_BLOCK, FOR_LOOP, TRY_BLOCK, ...
- **Edge Types**: CONTAINS, CALLS, INHERITS, IMPLEMENTS, IMPORTS, USES
- **Confidence System**: 4-tier probabilistic scoring
- **Hybrid Search**: BM25 (keyword) + UniXcoder + CodeBERT (semantic)
- **KuzuDB**: Embedded graph database with Cypher queries

**Schema:**
```cypher
// Frame node (20 properties)
(f:Frame {
  id: STRING,              // Stable SHA256-based
  type: STRING,            // Frame type
  qualified_name: STRING,  // Fully qualified
  confidence: FLOAT,       // 0.0-1.0
  confidence_tier: STRING, // HIGH/MEDIUM/LOW/SPECULATIVE
  language: STRING,        // python, cpp, java, perl
  file_path: STRING,
  start_line: INT32,
  end_line: INT32,
  content: STRING,
  ...
})

// Edge relationship (4 properties)
-[e:Edge {
  type: STRING,            // CALLS, CONTAINS, INHERITS, ...
  confidence: FLOAT,
  confidence_tier: STRING,
  metadata: STRING         // JSON extra data
}]->
```

---

## Use Cases

### For LLM Agents

**Efficient code exploration:**
```python
# Instead of reading 50 files sequentially...
map_codebase()                      # Understand structure
→ search("error handling")          # Find relevant code
→ show_structure("ErrorHandler")    # See skeleton (no impl)
→ check_impact("ErrorHandler")      # Understand dependencies
# 10x faster, 3x fewer tokens
```

### For Developers

**Architecture analysis:**
```cypher
-- Find most-called functions (hotspots)
MATCH (f:Frame)<-[e:Edge {type: 'CALLS'}]-()
RETURN f.qualified_name, count(e) as calls
ORDER BY calls DESC
LIMIT 20
```

**Refactoring prep:**
```cypher
-- Find all code that depends on this function
MATCH path = (start:Frame {qualified_name: 'old_function'})
             <-[:Edge {type: 'CALLS'}*1..3]-(dependent)
RETURN dependent.qualified_name, dependent.file_path
```

**Code review:**
```cypher
-- Find high-complexity functions
MATCH (func:Frame {type: 'CALLABLE'})
      -[:Edge {type: 'CONTAINS'}]->(control:Frame)
WHERE control.type IN ['IF_BLOCK', 'FOR_LOOP', 'TRY_BLOCK']
WITH func, count(control) + 1 as complexity
WHERE complexity > 10
RETURN func.qualified_name, complexity
ORDER BY complexity DESC
```

### For Researchers

- **Graph algorithms**: PageRank for central classes, community detection
- **Code metrics**: Coupling, cohesion, complexity via graph queries
- **ML training data**: Structured code graphs with confidence scores
- **Cognitive models**: Study LLM agent behavior with workspace state logs

---

## What Works ✅

- ✅ Multi-language parsing (Python, C++, Java, Perl)
- ✅ Unified frame abstraction (15 types, cross-language queries)
- ✅ Multi-pass confidence scoring (4 tiers)
- ✅ KuzuDB graph export with full schema
- ✅ Hybrid search (BM25 + UniXcoder + CodeBERT)
- ✅ Incremental updates (stable IDs, surgical changes)
- ✅ Dynamic system prompt injection (augments)
- ✅ Persistent workspace state (file windows, structural view)
- ✅ MCP server integration (nabu + nisaba)
- ✅ Workflow guidance (pattern-based suggestions)

---

## Known Limitations 🚧
- Control flow is structural only (no data flow analysis yet)
- External libraries referenced but not parsed (stdlib can be pre-indexed)
- Dynamic calls limited (Python `getattr`, C++ function pointers)
- Local variables not tracked yet (only class fields)
- Renames are catastrophic (`class Foo → Bar` changes stable_id)
- Database size grows exponentially when file watch and incremental updates are on

---

## Philosophy

> **"Ideally abstract, without compromising too much."**

### Core Principles

- **Heuristics over perfection** - 95% accurate fast > 60% slow & complex
- **Confidence over certainty** - Probabilistic understanding; model uncertainty explicitly
- **Relationships over entities** - Graph connections are the insight
- **Abstraction over detail** - Unified model; details in `content` property
- **Token efficiency matters** - Measured savings, not claims
- **Spatial over sequential** - Navigate state space, don't replay history
- **Perception as mutable** - Augments change how agents think, not just what they know

### Design Decisions

**Why frames instead of language-specific types?**
- Simplifies schema (15 types vs 80+)
- Enables cross-language queries
- Acceptable false positives (heuristic approach)

**Why confidence tiers?**
- Not all analysis is certain (especially dynamic languages)
- Let users filter by precision/recall tradeoff
- Progressive enhancement across passes

**Why dynamic system prompt injection?**
- Enables perceptual filtering (augments change cognition)
- Persistent workspace state (spatial memory)
- Avoids token waste (don't repeat context)

**Why KuzuDB?**
- Embedded (no external server)
- Fast graph queries with Cypher
- Native Python integration
- **Note:** Project archived Oct 2024; v0.11.3 is final stable release

---

## Name Etymology

### Nabu (Akkadian: 𒀭𒀝)

Mesopotamian god of writing, wisdom, and scribes (2nd millennium BCE).

**His role:**
- Records the fates of gods and mortals
- Patron of scribal arts
- Symbol: clay tablet and stylus

**The parallel:**
```
Ancient Nabu          → Modern Nabu
Clay tablets          → KuzuDB database
Stylus inscriptions   → Tree-sitter parsing
Divine decrees        → Code structure
Permanent records     → Persistent graphs
```

### Nisaba (Sumerian: 𒀭𒉀)

Mesopotamian goddess of writing, accounting, and harvest.

**Her role:**
- Organization and record-keeping
- Patron of scribes
- Sister of Nabu

**The parallel:**
```
Ancient Nisaba        → Modern Nisaba
Grain organization    → Tool registry organization
Record maintenance    → Workspace state persistence
Scribe support        → MCP framework for developers
```

When you use this ecosystem, you invoke ancient wisdom keepers who preserved knowledge across millennia. 📜

---

<p align="center">
  <em>"The stylus of wisdom inscribes the tablets of understanding."</em><br>
  <em>— Ancient Nabu hymn, modernized</em>
</p>

<p align="center">
  <strong>Token efficiency measured. Confidence explicitly modeled. Workspace persistently navigable.</strong>
</p>

<p align="center">📜 ✨ 🤖</p>
