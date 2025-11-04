# Code Quality
## Dead Code Detection
Path: code_quality/dead_code_detection

Finding functions, classes, and methods that are never called or used.

### Method 1: Find Unreferenced Callables

```python
# Find CALLABLE frames with no incoming CALLS edges
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.frame_type = 'CALLABLE'
      AND NOT EXISTS {
        MATCH ()-[:Edge {type: 'CALLS'}]->(f)
      }
      AND f.provenance = 'local'
    RETURN f.qualified_name, f.file_path, f.frame_type
    ORDER BY f.file_path
    LIMIT 100
    """
)
```

### Method 2: Find Unreferenced Classes

```python
# Find CLASS frames with no INHERITS, IMPLEMENTS, or CALLS edges pointing to them
query_relationships(
    cypher_query="""
    MATCH (c:Frame)
    WHERE c.frame_type = 'CLASS'
      AND NOT EXISTS {
        MATCH ()-[e:Edge]->(c)
        WHERE e.type IN ['INHERITS', 'IMPLEMENTS', 'CALLS']
      }
      AND c.provenance = 'local'
    RETURN c.qualified_name, c.file_path
    ORDER BY c.file_path
    LIMIT 50
    """
)
```

### Method 3: Trace From Entry Points (Inverse)

```python
# Step 1: Find main entry points
search(query="if __name__ == '__main__'", is_regex_input=True, k=20)

# Step 2: Check impact from entry points
check_impact(target="main", max_depth=5)

# Step 3: Find what's NOT in the impact tree
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.frame_type IN ['CALLABLE', 'CLASS']
      AND f.provenance = 'local'
      AND NOT EXISTS {
        MATCH path = (entry:Frame)-[:Edge {type: 'CALLS'}*]->(f)
        WHERE entry.name IN ['main', '__init__', 'setup']
      }
    RETURN f.qualified_name, f.file_path
    LIMIT 100
    """
)
```

### Method 4: Find Orphaned Modules

```python
# Find PACKAGE frames that are never imported
query_relationships(
    cypher_query="""
    MATCH (p:Frame)
    WHERE p.frame_type = 'PACKAGE'
      AND NOT EXISTS {
        MATCH ()-[:Edge {type: 'IMPORTS'}]->(p)
      }
      AND p.provenance = 'local'
    RETURN p.qualified_name, p.file_path
    ORDER BY p.qualified_name
    LIMIT 50
    """
)
```

### Validation Strategy

**Important considerations when identifying dead code:**

1. **Exclude test files** - May not be in main call graph but are still needed
2. **Exclude public API methods** - May be called externally (not visible in graph)
3. **Check provenance** - Don't flag external dependencies as dead code
4. **Verify with search()** - If suspicious, search for string references

```python
# Double-check with semantic search before deleting
search(query="suspected_dead_function", k=20, context_lines=5)
```

**Best Practice:** Always manually verify dead code candidates before deletion. False positives can occur for:
- Dynamically called functions (getattr, eval)
- External API endpoints
- Plugin systems
- Reflection/metaprogramming

## TOOLS
- query_relationships()
- search()
- check_impact()

## REQUIRES
- foundation/call_graph_analysis
