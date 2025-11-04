# Code Quality
## Complexity Hotspots
Path: code_quality/complexity_hotspots

Finding overly complex code that needs refactoring - high control flow complexity, deep nesting, long methods.

### Method 1: High Control Flow Complexity

Find functions with many control flow structures (if/for/while/try):

```python
# Find functions with >= 5 control structures
query_relationships(
    cypher_query="""
    MATCH (f:Frame)-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
    WHERE f.type = 'CALLABLE'
      AND cf.type IN ['IF_BLOCK', 'FOR_LOOP', 'WHILE_LOOP', 'TRY_BLOCK', 'SWITCH_BLOCK']
    WITH f.qualified_name AS func, f.file_path AS path, count(cf) AS complexity
    WHERE complexity >= 5
    RETURN func, path, complexity
    ORDER BY complexity DESC
    LIMIT 30
    """
)

# Examine complex functions in detail
show_structure(
    target="complex_function",
    detail_level="structure",
    structure_detail_depth=2
)
```

### Method 2: Deep Nesting Detection

Find deeply nested control structures (>3 levels):

```python
# Find nesting depth of 3-8 levels
query_relationships(
    cypher_query="""
    MATCH path = (f:Frame)-[:Edge {type: 'CONTAINS'}*3..8]->(nested:Frame)
    WHERE f.type = 'CALLABLE'
      AND ALL(node IN nodes(path)[1..] WHERE node.type IN ['IF_BLOCK', 'FOR_LOOP', 'WHILE_LOOP', 'TRY_BLOCK'])
    WITH f.qualified_name AS func, length(path) AS nesting_depth
    RETURN func, nesting_depth
    ORDER BY nesting_depth DESC
    LIMIT 20
    """
)
```

### Method 3: Long Method Detection

Find very long methods (heuristic: many children frames):

```python
# Functions with >= 20 statement-level children
query_relationships(
    cypher_query="""
    MATCH (f:Frame)-[:Edge {type: 'CONTAINS'}]->(:Frame)
    WHERE f.type = 'CALLABLE'
    WITH f.qualified_name AS func, f.file_path AS path, count(*) AS statement_count
    WHERE statement_count >= 20
    RETURN func, path, statement_count
    ORDER BY statement_count DESC
    LIMIT 30
    """
)
```

### Method 4: Exception Complexity

Find functions with complex exception handling:

```python
# Functions with >= 3 exception blocks
query_relationships(
    cypher_query="""
    MATCH (f:Frame)-[:Edge {type: 'CONTAINS'}]->(exc:Frame)
    WHERE f.type = 'CALLABLE'
      AND exc.type IN ['TRY_BLOCK', 'EXCEPT_BLOCK', 'FINALLY_BLOCK']
    WITH f.qualified_name AS func, count(exc) AS exception_blocks
    WHERE exception_blocks >= 3
    RETURN func, exception_blocks
    ORDER BY exception_blocks DESC
    LIMIT 30
    """
)
```

### Method 5: Combine with Metrics

Use show_structure() with metrics for comprehensive analysis:

```python
# Get complexity metrics for a class
show_structure(
    target="ComplexClass",
    detail_level="minimal",
    include_metrics=True
)
```

**Refactoring Priorities:**
- **High nesting + high complexity** → Immediate refactoring candidate
- **Long methods** → Extract smaller methods
- **Complex exception handling** → Simplify error handling strategy

## TOOLS
- query_relationships()
- show_structure()
