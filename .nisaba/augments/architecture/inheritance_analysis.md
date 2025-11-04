# Architecture
## Inheritance Analysis
Path: architecture/inheritance_analysis

Analyzing class hierarchies and inheritance patterns.

### Deep Inheritance Hierarchies

Find inheritance chains longer than 3 levels (potential issue):

```python
# Find deep inheritance chains (>3 levels = potential issue)
query_relationships(
    cypher_query="""
    MATCH path = (child:Frame)-[:Edge {type: 'INHERITS'}*3..10]->(ancestor:Frame)
    WHERE child.frame_type = 'CLASS'
    WITH path, length(path) AS depth,
         [node IN nodes(path) | node.qualified_name] AS hierarchy
    RETURN hierarchy, depth
    ORDER BY depth DESC
    LIMIT 20
    """
)
```

### Find Root Classes

Base classes with no parents (top of hierarchy):

```python
# Find base classes (no parents, not including object/Object)
query_relationships(
    cypher_query="""
    MATCH (c:Frame)
    WHERE c.frame_type = 'CLASS'
      AND c.provenance = 'local'
      AND NOT EXISTS {
        MATCH (c)-[:Edge {type: 'INHERITS'}]->()
      }
    RETURN c.qualified_name, c.file_path
    ORDER BY c.qualified_name
    LIMIT 50
    """
)
```

### Find Leaf Classes

Classes with no children (end of hierarchy):

```python
# Find classes with no children (leaves)
query_relationships(
    cypher_query="""
    MATCH (c:Frame)
    WHERE c.frame_type = 'CLASS'
      AND c.provenance = 'local'
      AND NOT EXISTS {
        MATCH ()-[:Edge {type: 'INHERITS'}]->(c)
      }
    RETURN c.qualified_name, c.file_path
    ORDER BY c.qualified_name
    LIMIT 50
    """
)
```

### Multiple Inheritance Analysis

Find classes with multiple parent classes:

```python
# Find classes with multiple inheritance
query_relationships(
    cypher_query="""
    MATCH (child:Frame)-[:Edge {type: 'INHERITS'}]->(parent:Frame)
    WHERE child.frame_type = 'CLASS'
    WITH child.qualified_name AS class_name, count(parent) AS parent_count
    WHERE parent_count > 1
    RETURN class_name, parent_count
    ORDER BY parent_count DESC
    LIMIT 30
    """
)
```

### Visualize Hierarchy

Get full hierarchy structure:

```python
# Get structure with relationships (shows inheritance)
show_structure(
    target="BaseClass",
    detail_level="minimal",
    include_relationships=True,
    max_recursion_depth=0
)

# Check who inherits from this class
check_impact(target="BaseClass", max_depth=1)
```

### Interface Implementation Analysis

Find classes implementing interfaces:

```python
# Find interface implementations
query_relationships(
    cypher_query="""
    MATCH (impl:Frame)-[:Edge {type: 'IMPLEMENTS'}]->(interface:Frame)
    WHERE impl.frame_type = 'CLASS'
    RETURN interface.qualified_name AS interface,
           count(impl) AS implementations
    ORDER BY implementations DESC
    LIMIT 30
    """
)
```

### Inheritance Metrics

Calculate hierarchy depth and breadth:

```python
# Find classes with many direct children (high breadth)
query_relationships(
    cypher_query="""
    MATCH (child:Frame)-[:Edge {type: 'INHERITS'}]->(parent:Frame)
    WHERE parent.frame_type = 'CLASS'
      AND parent.provenance = 'local'
    WITH parent.qualified_name AS base_class, count(child) AS direct_children
    WHERE direct_children >= 5
    RETURN base_class, direct_children
    ORDER BY direct_children DESC
    LIMIT 30
    """
)
```

**Inheritance Guidelines:**
- **Depth ≤ 3:** Acceptable inheritance depth
- **Depth > 3:** Consider composition instead
- **Multiple inheritance:** Use carefully, prefer interfaces/mixins
- **High breadth (>10 children):** Consider if all are necessary

**Refactoring Strategies:**
- **Deep hierarchies:** Flatten with composition
- **Multiple inheritance:** Extract to separate concerns
- **Wide hierarchies:** Split into multiple base classes

## TOOLS
- query_relationships()
- show_structure()
- check_impact()
