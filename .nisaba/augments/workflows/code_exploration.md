# Workflows
## Code Exploration Workflow
Path: workflows/code_exploration

Progressive disclosure workflow for understanding unfamiliar codebases - start broad, narrow down systematically.

This workflow follows the principle of semantic-first exploration: understand structure before details.

### Workflow Overview

**Goal:** Efficiently understand an unknown codebase or feature area.

**Philosophy:** Macro → Meso → Micro (progressive zoom)

**Avoid:** Reading entire files, getting lost in details

### Step 1: High-Level Overview

Start with the big picture:

```python
# Get frame counts and structure
show_status(detail_level="summary")

# Shows:
# - How many classes, functions, packages
# - Programming languages used
# - Database health
```

**What to look for:**
- Scale of codebase (100s or 1000s of frames?)
- Language mix
- Overall organization

### Step 2: Broad Search

Find relevant areas with semantic search:

```python
# Natural language query for functionality
search(query="authentication user validation login", k=20)

# Or keyword search
search(query="auth login user", k=15)

# Adjust k based on results quality
```

**Search strategies:**
- Start with 10-20 results
- If too many: narrow query
- If too few: broaden query
- Look at file_path patterns in results

**What to look for:**
- Which files/packages contain relevant code?
- What are the main components?
- Are there naming patterns?

### Step 3: Structural Examination (Minimal Detail)

Examine structure of interesting results:

```python
# Get clean skeleton (token-efficient)
show_structure(
    target="AuthenticationManager",
    detail_level="minimal",
    include_private=False
)
```

**What to look for:**
- Method signatures (what does it do?)
- Public API surface
- Class relationships (if include_relationships=True)

**When to use:**
- First look at a class
- Understanding API surface
- Deciding what to investigate deeper

### Step 4: Progressive Detail (As Needed)

Add detail only when needed:

```python
# Add behavioral hints
show_structure(
    target="AuthenticationManager",
    detail_level="guards",
    include_relationships=True
)

# Or full control flow
show_structure(
    target="specific_method",
    detail_level="structure",
    structure_detail_depth=2
)
```

**When to use:**
- Need to understand logic flow
- Preparing for changes
- Debugging specific behavior

### Step 5: Relationship Exploration

Understand how components connect:

```python
# Who calls this?
check_impact(target="AuthenticationManager", max_depth=1)

# What does this call?
query_relationships(
    cypher_query="""
    MATCH (source:Frame)-[e:Edge {type: 'CALLS'}]->(target:Frame)
    WHERE source.qualified_name CONTAINS 'AuthenticationManager'
      AND e.confidence >= 0.7
    RETURN target.qualified_name, target.file_path
    LIMIT 30
    """
)
```

**What to look for:**
- Dependencies (what does it use?)
- Dependents (what uses it?)
- Critical paths (main → this component)

### Complete Exploration Example

```python
# === EXPLORING AUTHENTICATION SYSTEM ===

# Step 1: Overview
show_status(detail_level="summary")

# Step 2: Find authentication code
search(query="authentication login user credential", k=20)

# Results show: AuthenticationManager, LoginHandler, UserValidator

# Step 3: Examine main class
show_structure(
    target="AuthenticationManager",
    detail_level="minimal",
    include_private=False
)

# Reveals methods: authenticate(), validate_token(), refresh_session()

# Step 4: Understand authenticate() logic
show_structure(
    target="AuthenticationManager/authenticate",
    detail_level="guards",
    include_relationships=True
)

# Shows: checks credentials → validates user → creates session

# Step 5: Find who uses it
check_impact(target="AuthenticationManager", max_depth=1)

# Results: LoginHandler, APIGateway, WebSocketHandler

# Step 6: Understand broader context
search(query="session token jwt", k=15)

# Now have complete picture of auth system!
```

### Decision Tree: When to Use Each Tool

```
Want to find something?
├─ YES → search() with natural language or keywords
│   └─ Found candidates?
│       ├─ YES → show_structure(minimal) to examine
│       └─ NO → Broaden search query
│
├─ Want to understand structure?
│   └─ show_structure()
│       ├─ Just signatures? → detail_level="minimal"
│       ├─ Logic hints? → detail_level="guards"
│       └─ Full flow? → detail_level="structure"
│
└─ Want to see relationships?
    ├─ Who uses this? → check_impact() or show_structure(include_relationships=True)
    ├─ What does this use? → query_relationships()
    └─ Complex query? → query_relationships() with custom Cypher
```

### Exploration Patterns

**Pattern 1: Feature Understanding**
```python
search() → show_structure(minimal) → show_structure(guards) → check_impact()
```

**Pattern 2: Bug Investigation**
```python
search() → show_structure(structure) → query_relationships() → check_impact()
```

**Pattern 3: Dependency Mapping**
```python
show_structure(minimal) → check_impact() → query_relationships()
```

**Pattern 4: Architecture Review**
```python
show_status() → search(broad) → show_structure(multiple targets) → query_relationships()
```

### Common Mistakes to Avoid

❌ **Reading entire files immediately**
- Use show_structure() first
- Read files only when structure isn't enough

❌ **Too much detail too soon**
- Start with minimal, add detail progressively
- Full structure is expensive (tokens)

❌ **Not using search()**
- Don't randomly explore
- Search finds relevant areas fast

❌ **Ignoring confidence levels**
- Check confidence in relationships
- Low confidence = verify manually

❌ **Not following relationships**
- Understanding connections is key
- Use check_impact() and query_relationships()

### Exploration Checklist

For any new area:
- [ ] Search to find relevant code
- [ ] Examine structure (minimal first)
- [ ] Check relationships (who uses/used by)
- [ ] Add detail only as needed
- [ ] Verify with targeted file reads if necessary

**Time Savings:**
- Traditional: 30-60 min reading files
- With workflow: 5-15 min targeted exploration

## TOOLS
- show_status()
- search()
- show_structure()

## REQUIRES
- foundation/call_graph_analysis
