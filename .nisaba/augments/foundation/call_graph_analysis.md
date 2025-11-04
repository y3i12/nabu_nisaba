# Foundation
## Call Graph Analysis
Path: foundation/call_graph_analysis

Understanding execution flow via CALLS edges - the foundation for tracing how code executes.

### Forward Tracing (From Entry Point)

Trace execution paths starting from entry points like `main()`:

```python
# Trace all paths from main() with depth limit
query_relationships(
    cypher_query="""
    MATCH path = (entry:Frame)-[:Edge {type: 'CALLS'}*1..5]->(target:Frame)
    WHERE entry.name = 'main'
      AND ALL(e IN relationships(path) WHERE e.confidence >= 0.6)
    RETURN path
    LIMIT 50
    """
)

# Show the call chain as a list
query_relationships(
    cypher_query="""
    MATCH path = (entry:Frame)-[:Edge {type: 'CALLS'}*1..4]->(target:Frame)
    WHERE entry.name = 'main'
    WITH path, [node IN nodes(path) | node.qualified_name] AS call_chain
    RETURN call_chain
    LIMIT 100
    """
)
```

### Backward Tracing (Who Calls This?)

Find all paths leading TO a specific function:

```python
# Find all callers up to 3 levels deep
query_relationships(
    cypher_query="""
    MATCH path = (caller:Frame)-[:Edge {type: 'CALLS'}*1..3]->(target:Frame)
    WHERE target.qualified_name = 'critical_function'
    WITH path, [node IN nodes(path) | node.qualified_name] AS call_chain
    RETURN call_chain
    ORDER BY length(path)
    LIMIT 50
    """
)

# Use check_impact in reverse (shows who depends on it)
check_impact(target="critical_function", max_depth=3)
```

### Critical Path Analysis

Find longest or most complex call chains:

```python
# Find longest call chains (potential performance issues)
query_relationships(
    cypher_query="""
    MATCH path = (a:Frame)-[:Edge {type: 'CALLS'}*3..10]->(b:Frame)
    WHERE ALL(e IN relationships(path) WHERE e.confidence >= 0.7)
    WITH path, length(path) AS depth
    RETURN [node IN nodes(path) | node.qualified_name] AS call_chain, depth
    ORDER BY depth DESC
    LIMIT 20
    """
)
```

### Call Graph Visualization Prep

Export call relationships for visualization:

```python
# Export call graph for specific package
query_relationships(
    cypher_query="""
    MATCH (caller:Frame)-[e:Edge {type: 'CALLS'}]->(callee:Frame)
    WHERE caller.qualified_name STARTS WITH 'mypackage.'
      AND callee.qualified_name STARTS WITH 'mypackage.'
      AND e.confidence >= 0.6
    RETURN caller.qualified_name AS from,
           callee.qualified_name AS to,
           e.confidence AS weight
    LIMIT 200
    """
)
```

**Use Cases:**
- Understanding execution flow
- Finding bottlenecks
- Debugging complex call chains
- Impact analysis before changes

## TOOLS
- query_relationships()
- check_impact()
- show_structure()
