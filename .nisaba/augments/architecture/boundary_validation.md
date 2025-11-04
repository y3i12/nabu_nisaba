# Architecture
## Boundary Validation
Path: architecture/boundary_validation

Validating architectural boundaries and layering rules.

### Layer Dependency Validation

Define expected layer dependencies and find violations:

```python
# Example: UI should not call Data directly (must go through Business)
# Find UI → Data violations
query_relationships(
    cypher_query="""
    MATCH (ui:Frame)-[e:Edge {type: 'CALLS'}]->(data:Frame)
    WHERE ui.file_path CONTAINS '/ui/'
      AND data.file_path CONTAINS '/data/'
      AND e.confidence >= 0.6
    RETURN ui.qualified_name AS violator,
           data.qualified_name AS violated,
           'UI should not directly call Data layer' AS violation
    LIMIT 50
    """
)
```

### Cross-Boundary Leaks

Find data models or internal classes used outside their module:

```python
# Find data models used outside their module
query_relationships(
    cypher_query="""
    MATCH (external:Frame)-[e:Edge]->(model:Frame)
    WHERE model.file_path CONTAINS '/models/'
      AND NOT external.file_path CONTAINS '/models/'
      AND e.type IN ['INHERITS', 'USES']
      AND e.confidence >= 0.6
    RETURN model.qualified_name,
           external.qualified_name,
           external.file_path AS leaking_to
    LIMIT 50
    """
)
```

### Package Dependency Rules

Validate that internal packages don't depend on external-facing ones:

```python
# Find unexpected cross-package dependencies
query_relationships(
    cypher_query="""
    MATCH (a:Frame)-[e:Edge {type: 'IMPORTS'}]->(b:Frame)
    WHERE a.qualified_name STARTS WITH 'internal.'
      AND b.qualified_name STARTS WITH 'external_facing.'
      AND e.confidence >= 0.6
    RETURN a.qualified_name, b.qualified_name,
           'Internal should not depend on external_facing' AS violation
    LIMIT 50
    """
)
```

### Common Boundary Violations to Check

**1. Presentation depending on Data:**
```python
MATCH (pres:Frame)-[e:Edge]->(data:Frame)
WHERE pres.file_path CONTAINS '/presentation/'
  AND data.file_path CONTAINS '/data/'
```

**2. Domain depending on Infrastructure:**
```python
MATCH (domain:Frame)-[e:Edge]->(infra:Frame)
WHERE domain.file_path CONTAINS '/domain/'
  AND infra.file_path CONTAINS '/infrastructure/'
```

**3. Core depending on Plugins:**
```python
MATCH (core:Frame)-[e:Edge]->(plugin:Frame)
WHERE core.file_path CONTAINS '/core/'
  AND plugin.file_path CONTAINS '/plugins/'
```

**4. Shared utilities depending on specific features:**
```python
MATCH (util:Frame)-[e:Edge]->(feature:Frame)
WHERE util.file_path CONTAINS '/utils/'
  AND feature.file_path CONTAINS '/features/'
```

### Validation Workflow

```python
# Step 1: Understand current layer structure
# (use layer_detection skill)

# Step 2: Define architectural rules
# Example: UI → Business → Data → Infrastructure

# Step 3: Find violations of each rule
query_relationships(cypher_query="...")

# Step 4: Assess impact of fixing violations
check_impact(target="violating_class", max_depth=2)
```

**Architectural Principles to Enforce:**
- **Dependency Inversion:** High-level should not depend on low-level
- **Acyclic Dependencies:** No circular dependencies between layers
- **Stable Abstractions:** Abstract packages should be stable
- **Layering:** Calls should flow downward through layers

## TOOLS
- query_relationships()

## REQUIRES
- architecture/layer_detection
