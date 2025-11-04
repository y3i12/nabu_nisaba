# Code Analysis
## Complexity Hotspots
Path: code_analysis/complexity_hotspots

Find functions with many control flow structures (high complexity):

```cypher
query_relationships(
    cypher_query="""
    MATCH (f:Frame)-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
    WHERE f.frame_type = 'CALLABLE'
      AND cf.frame_type IN ['IF_BLOCK', 'FOR_LOOP', 'WHILE_LOOP', 'TRY_BLOCK', 'SWITCH_BLOCK']
    WITH f.qualified_name AS func, f.file_path AS path, count(cf) AS complexity
    WHERE complexity >= 5
    RETURN func, path, complexity
    ORDER BY complexity DESC
    LIMIT 30
    """
)
```

Use `show_structure()` with `detail_level="structure"` to examine complex functions.

## TOOLS
- query_relationships()
- show_structure()
