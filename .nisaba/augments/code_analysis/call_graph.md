# Code Analysis
## Call Graph
Path: code_analysis/call_graph

Understanding execution flow via CALLS edges.

Trace function calls to understand code execution paths:

```cypher
# Find all callers of a method
query_relationships(
    cypher_query="""
    MATCH (caller)-[e:Edge {type: "CALLS"}]->(target:Frame {qualified_name: "pkg.Class.method"})
    WHERE e.confidence >= 0.7
    RETURN caller.qualified_name, caller.file_path, e.confidence
    LIMIT 50
    """
)
```

After finding call relationships, use `show_structure()` to examine the structure of callers or targets.

## TOOLS
- query_relationships()
- show_structure()
- check_impact()
