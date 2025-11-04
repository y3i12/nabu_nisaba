# Architecture
## Coupling Analysis
Path: architecture/coupling_analysis

Measuring module coupling using afferent/efferent coupling and instability metrics.

### Afferent Coupling (Fan-In)

**Ca:** Number of classes outside package that depend on classes inside.

```python
# High afferent coupling = many things depend on this (stable)
query_relationships(
    cypher_query="""
    MATCH (external:Frame)-[e:Edge]->(internal:Frame)
    WHERE NOT external.file_path CONTAINS '/target_package/'
      AND internal.file_path CONTAINS '/target_package/'
      AND e.type IN ['CALLS', 'INHERITS', 'USES']
      AND e.confidence >= 0.6
    WITH internal.file_path AS target_package, count(DISTINCT external) AS afferent_coupling
    RETURN target_package, afferent_coupling
    ORDER BY afferent_coupling DESC
    LIMIT 30
    """
)
```

### Efferent Coupling (Fan-Out)

**Ce:** Number of classes inside package that depend on external classes.

```python
# High efferent coupling = depends on many things (unstable)
query_relationships(
    cypher_query="""
    MATCH (internal:Frame)-[e:Edge]->(external:Frame)
    WHERE internal.file_path CONTAINS '/target_package/'
      AND NOT external.file_path CONTAINS '/target_package/'
      AND e.type IN ['CALLS', 'INHERITS', 'USES']
      AND e.confidence >= 0.6
    WITH internal.file_path AS source_package, count(DISTINCT external) AS efferent_coupling
    RETURN source_package, efferent_coupling
    ORDER BY efferent_coupling DESC
    LIMIT 30
    """
)
```

### Instability Metric

**I = Ce / (Ca + Ce)** - ranges from 0 (maximally stable) to 1 (maximally unstable).

```python
# Calculate instability for packages
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.file_path CONTAINS '/target_package/'
    WITH f.file_path AS pkg
    OPTIONAL MATCH (f2:Frame)-[e_in:Edge]->(f)
    WHERE NOT f2.file_path CONTAINS '/target_package/'
      AND e_in.confidence >= 0.6
    WITH pkg, count(DISTINCT f2) AS ca
    OPTIONAL MATCH (f3:Frame)-[e_out:Edge]->(ext:Frame)
    WHERE f3.file_path CONTAINS '/target_package/'
      AND NOT ext.file_path CONTAINS '/target_package/'
      AND e_out.confidence >= 0.6
    WITH pkg, ca, count(DISTINCT ext) AS ce
    RETURN pkg, ca, ce,
           CASE WHEN (ca + ce) > 0
                THEN toFloat(ce) / toFloat(ca + ce)
                ELSE 0
           END AS instability
    ORDER BY instability DESC
    LIMIT 30
    """
)
```

### Dependency Hotspots

```python
# Find most-depended-upon modules (high fan-in)
query_relationships(
    cypher_query="""
    MATCH ()-[e:Edge]->(target:Frame)
    WHERE e.type IN ['IMPORTS', 'CALLS']
      AND target.provenance = 'local'
      AND e.confidence >= 0.6
    WITH target.qualified_name AS name, target.file_path AS path, count(e) AS dependents
    RETURN name, path, dependents
    ORDER BY dependents DESC
    LIMIT 30
    """
)

# Find modules with most dependencies (high fan-out)
query_relationships(
    cypher_query="""
    MATCH (source:Frame)-[e:Edge]->()
    WHERE e.type IN ['IMPORTS', 'CALLS']
      AND source.provenance = 'local'
      AND e.confidence >= 0.6
    WITH source.qualified_name AS name, count(e) AS dependencies
    RETURN name, dependencies
    ORDER BY dependencies DESC
    LIMIT 30
    """
)
```

### Interpreting Results

**Instability Guidelines:**
- **I ≈ 0 (Stable):** Hard to change, many things depend on it
  - Good for: Core libraries, stable APIs
  - Bad for: UI code, experimental features

- **I ≈ 1 (Unstable):** Easy to change, few dependents
  - Good for: UI code, adapters, glue code
  - Bad for: Core domain logic, shared utilities

**Stable Dependencies Principle:** Unstable modules should depend on stable modules, not vice versa.

**Coupling Targets:**
- **High Ca, Low Ce:** Foundation modules (good)
- **Low Ca, High Ce:** Client modules (good)
- **High Ca, High Ce:** Hub modules (potential issue)
- **Low Ca, Low Ce:** Isolated modules (check if needed)

## TOOLS
- query_relationships()
