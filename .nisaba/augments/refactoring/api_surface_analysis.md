# Refactoring
## API Surface Analysis
Path: refactoring/api_surface_analysis

Understanding public interfaces before making changes that could break external users.

### Identify Public API

Find top-level classes and functions (likely public API):

```python
# Find public API candidates (top-level, non-underscore prefixed)
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.type IN ['CLASS', 'CALLABLE']
      AND f.provenance = 'parsed'
      AND NOT f.name STARTS WITH '_'
      AND NOT EXISTS {
        MATCH (parent:Frame)-[:Edge {type: 'CONTAINS'}]->(f)
        WHERE parent.type IN ['CLASS', 'CALLABLE']
      }
    RETURN f.qualified_name, f.file_path, f.type
    ORDER BY f.file_path
    LIMIT 100
    """
)
```

### Public vs Private Ratio

Analyze encapsulation quality:

```python
# Calculate public/private ratio
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.type IN ['CALLABLE', 'CLASS']
      AND f.provenance = 'parsed'
    WITH
      count(CASE WHEN f.name STARTS WITH '_' THEN 1 END) AS private_count,
      count(CASE WHEN NOT f.name STARTS WITH '_' THEN 1 END) AS public_count
    RETURN public_count, private_count,
           toFloat(private_count) / toFloat(public_count) AS encapsulation_ratio
    """
)
```

**Encapsulation Ratio Guidelines:**
- **< 1.0:** More public than private (poor encapsulation)
- **1.0-2.0:** Balanced (acceptable)
- **> 2.0:** Well encapsulated (good)

### API Stability Analysis

Find public methods with many callers (breaking changes are costly):

```python
# Find high-impact public methods (>= 10 callers)
query_relationships(
    cypher_query="""
    MATCH ()-[e:Edge {type: 'CALLS'}]->(api:Frame)
    WHERE NOT api.name STARTS WITH '_'
      AND api.provenance = 'parsed'
      AND e.confidence >= 0.7
    WITH api.qualified_name AS public_method, count(e) AS caller_count
    WHERE caller_count >= 10
    RETURN public_method, caller_count
    ORDER BY caller_count DESC
    LIMIT 30
    """
)
```

**Breaking Change Risk:**
- **< 5 callers:** Low risk (easy to update)
- **5-20 callers:** Medium risk (manageable)
- **> 20 callers:** High risk (requires deprecation strategy)

### Examine API Structure

Get clean overview of public API surface:

```python
# Get API structure without private members
show_structure(
    target="PublicAPIClass",
    detail_level="minimal",
    include_private=False,
    include_relationships=True
)

# Find who's using this API
show_structure(
    target="PublicAPIClass",
    detail_level="minimal",
    include_relationships=True,
    max_callers=50
)
```

### Find All Public APIs in Package

```python
# Regex search for public APIs (non-underscore prefixed)
search(
    query="^[^_].*$",
    is_regex_input=True,
    type_filter="CALLABLE|CLASS",
    k=50
)

# Or target specific package
search(
    query="def [a-z][a-z_]*\\(",
    is_regex_input=True,
    k=50
)
```

### API Change Impact Workflow

Complete workflow before changing public API:

```python
# Step 1: Identify if target is public API
show_structure(
    target="TargetClass",
    detail_level="minimal",
    include_private=False
)

# Step 2: Find all callers
query_relationships(
    cypher_query="""
    MATCH (caller)-[e:Edge {type: 'CALLS'}]->(target:Frame)
    WHERE target.qualified_name CONTAINS 'TargetClass'
      AND e.confidence >= 0.7
    RETURN caller.qualified_name, caller.file_path, e.confidence
    ORDER BY e.confidence DESC
    LIMIT 100
    """
)

# Step 3: Check impact
check_impact(
    target="TargetClass",
    max_depth=3,
    include_test_coverage=True
)

# Step 4: Assess caller distribution
# - All internal → Safe to change
# - Mixed internal/external → Needs deprecation
# - Mostly external → Breaking change, version bump
```

### Deprecation Strategy

For high-impact API changes:

1. **Add new API** alongside old (don't remove yet)
2. **Deprecate old API** with warnings
3. **Update internal callers** to new API
4. **Document migration path** in release notes
5. **Remove in next major version**

### API Documentation Gaps

Find public APIs that might need documentation:

```python
# Find public APIs (then check their docstrings manually)
show_structure(
    target="PublicModule",
    detail_level="minimal",
    include_docstrings=True,
    include_private=False
)
```

## TOOLS
- query_relationships()
- search()
- show_structure()
