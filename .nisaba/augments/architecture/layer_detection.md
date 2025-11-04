# Architecture
## Layer Detection
Path: architecture/layer_detection

Understanding and discovering architectural layers and module organization.

### Package Hierarchy Exploration

```python
# Get all packages in the codebase
query_relationships(
    cypher_query="""
    MATCH (pkg:Frame)
    WHERE pkg.frame_type = 'PACKAGE'
    RETURN pkg.qualified_name, pkg.file_path
    ORDER BY pkg.qualified_name
    LIMIT 100
    """
)

# Understand package containment structure
query_relationships(
    cypher_query="""
    MATCH (parent:Frame)-[:Edge {type: 'CONTAINS'}]->(child:Frame)
    WHERE parent.frame_type = 'PACKAGE'
      AND child.frame_type IN ['PACKAGE', 'CLASS', 'CALLABLE']
    RETURN parent.qualified_name,
           child.frame_type,
           count(child) AS children_count
    ORDER BY children_count DESC
    LIMIT 50
    """
)
```

### Cross-Layer Dependency Detection

```python
# Find cross-layer dependencies (e.g., data layer calling UI layer - bad!)
query_relationships(
    cypher_query="""
    MATCH (caller:Frame)-[e:Edge {type: 'CALLS'}]->(callee:Frame)
    WHERE caller.file_path CONTAINS '/data/'
      AND callee.file_path CONTAINS '/ui/'
      AND e.confidence >= 0.6
    RETURN caller.qualified_name, callee.qualified_name, caller.file_path, callee.file_path
    LIMIT 50
    """
)

# Find expected dependencies (e.g., UI → business logic → data)
query_relationships(
    cypher_query="""
    MATCH (ui:Frame)-[:Edge {type: 'CALLS'}]->(logic:Frame)-[:Edge {type: 'CALLS'}]->(data:Frame)
    WHERE ui.file_path CONTAINS '/ui/'
      AND logic.file_path CONTAINS '/business/'
      AND data.file_path CONTAINS '/data/'
    RETURN ui.qualified_name, logic.qualified_name, data.qualified_name
    LIMIT 30
    """
)
```

### Module Cohesion Analysis

```python
# Find modules with high internal cohesion (good)
query_relationships(
    cypher_query="""
    MATCH (a:Frame)-[e:Edge {type: 'CALLS'}]->(b:Frame)
    WHERE a.file_path = b.file_path
      AND e.confidence >= 0.7
    WITH a.file_path AS module, count(e) AS internal_calls
    RETURN module, internal_calls
    ORDER BY internal_calls DESC
    LIMIT 30
    """
)

# Find modules with high external coupling (potential issue)
query_relationships(
    cypher_query="""
    MATCH (a:Frame)-[e:Edge {type: 'CALLS'}]->(b:Frame)
    WHERE a.file_path <> b.file_path
      AND e.confidence >= 0.7
    WITH a.file_path AS module, count(DISTINCT b.file_path) AS external_dependencies
    RETURN module, external_dependencies
    ORDER BY external_dependencies DESC
    LIMIT 30
    """
)
```

### Architectural Boundaries

```python
# Find all cross-package calls to identify boundaries
query_relationships(
    cypher_query="""
    MATCH (caller:Frame)-[e:Edge {type: 'CALLS'}]->(callee:Frame)
    WHERE caller.qualified_name STARTS WITH 'package_a.'
      AND callee.qualified_name STARTS WITH 'package_b.'
      AND e.confidence >= 0.6
    RETURN caller.qualified_name, callee.qualified_name
    LIMIT 100
    """
)

# Use search to find architectural patterns
search(query="facade factory builder singleton adapter", k=30)
```

**Typical Layers to Look For:**
- **Presentation/UI:** User interface, controllers, views
- **Business/Application:** Business logic, use cases
- **Domain:** Domain models, entities
- **Data/Persistence:** Database access, repositories
- **Infrastructure:** External services, utilities

**Healthy Architecture Indicators:**
- High internal cohesion (many internal calls)
- Low external coupling (few cross-module deps)
- Unidirectional dependencies (UI → Business → Data)
- Clear boundaries between layers

## TOOLS
- query_relationships()
- search()
