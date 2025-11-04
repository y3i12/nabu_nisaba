# Code Quality
## Code Smells
Path: code_quality/code_smells

General code smell detection: god classes, high coupling, naming violations.

### God Classes & High Method Count

```python
# Find classes with many methods (>= 15)
query_relationships(
    cypher_query="""
    MATCH (c:Frame)-[:Edge {type: 'CONTAINS'}]->(m:Frame)
    WHERE c.frame_type = 'CLASS'
      AND m.frame_type = 'CALLABLE'
    WITH c.qualified_name AS class_name, c.file_path AS path, count(m) AS method_count
    WHERE method_count >= 15
    RETURN class_name, path, method_count
    ORDER BY method_count DESC
    LIMIT 30
    """
)
```

### High Coupling Indicators

```python
# Find classes with many dependencies (>= 20)
query_relationships(
    cypher_query="""
    MATCH (c:Frame)-[e:Edge]->(:Frame)
    WHERE c.frame_type = 'CLASS'
      AND e.type IN ['CALLS', 'USES', 'INHERITS']
      AND e.confidence >= 0.6
    WITH c.qualified_name AS class_name, count(DISTINCT e) AS dependencies
    WHERE dependencies >= 20
    RETURN class_name, dependencies
    ORDER BY dependencies DESC
    LIMIT 30
    """
)

# Find classes that use many other classes' fields
query_relationships(
    cypher_query="""
    MATCH (c:Frame)-[u:Edge {type: 'USES'}]->(other:Frame)
    WHERE c.frame_type = 'CLASS'
    WITH c.qualified_name AS class_name, count(DISTINCT other) AS used_classes
    WHERE used_classes >= 10
    RETURN class_name, used_classes
    ORDER BY used_classes DESC
    LIMIT 30
    """
)
```

### Naming Convention Violations

```python
# Find classes not in PascalCase
search(
    query="class [a-z_]",
    is_regex_input=True,
    frame_type_filter="CLASS",
    k=30
)

# Find functions not in snake_case
search(
    query="def [A-Z]|def .*[A-Z]",
    is_regex_input=True,
    frame_type_filter="CALLABLE",
    k=30
)
```

### Inconsistent Verb Usage

```python
# Find similar operations with different naming
search(query="get_* fetch_* retrieve_* obtain_*", k=50)
search(query="create_* make_* build_* generate_*", k=50)
search(query="delete_* remove_* destroy_* clear_*", k=50)

# Find abbreviation inconsistencies
search(query="config configuration cfg", k=30)
search(query="msg message mesg", k=30)
search(query="temp temporary tmp", k=30)
```

### Deep Dive into Candidates

For classes identified as potential problems:

```python
# Examine structure with metrics
show_structure(
    target="GodClassCandidate",
    detail_level="minimal",
    include_metrics=True,
    include_relationships=True
)
```

**Common Smells & Fixes:**
- **Many methods** → Split into multiple classes
- **High coupling** → Introduce interfaces/abstractions
- **Inconsistent naming** → Standardize verb usage
- **Long parameter lists** → Introduce parameter objects
- **Feature envy** → Move methods to the class they use most

**Priority Indicators:**
- High methods + High coupling = Critical
- Naming violations = Low priority (style)
- Inconsistent verbs = Medium (maintainability)

## TOOLS
- query_relationships()
- search()
- show_structure()
