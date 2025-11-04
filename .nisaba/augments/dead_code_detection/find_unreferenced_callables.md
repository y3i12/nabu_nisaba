# Dead Code Detection
## Find Unreferenced Callables
Path: dead_code_detection/find_unreferenced_callables

Find CALLABLE frames with no incoming CALLS edges:

```cypher
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.type = 'CALLABLE'
      AND NOT EXISTS {
        MATCH ()-[:Edge {type: 'CALLS'}]->(f)
      }
      AND f.provenance = 'parsed'
    RETURN f.qualified_name, f.file_path, f.type
    ORDER BY f.file_path
    LIMIT 100
    """
)
```

## TOOLS
- query_relationships()

## REQUIRES
- code_analysis/call_graph
