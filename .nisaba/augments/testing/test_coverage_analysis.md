# Testing
## Test Coverage Analysis
Path: testing/test_coverage_analysis

Understanding which code is tested and which isn't.

### Find Untested Code

```python
# Find functions with no calls from test files
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.frame_type = 'CALLABLE'
      AND f.provenance = 'local'
      AND NOT f.file_path CONTAINS 'test'
      AND NOT EXISTS {
        MATCH (test:Frame)-[:Edge {type: 'CALLS'}]->(f)
        WHERE test.file_path CONTAINS 'test'
      }
    RETURN f.qualified_name, f.file_path
    ORDER BY f.file_path
    LIMIT 100
    """
)
```

### Test-to-Code Ratio

Calculate overall test coverage metrics:

```python
# Count test vs production frames
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.frame_type IN ['CALLABLE', 'CLASS']
      AND f.provenance = 'local'
    WITH
      count(CASE WHEN f.file_path CONTAINS 'test' THEN 1 END) AS test_count,
      count(CASE WHEN NOT f.file_path CONTAINS 'test' THEN 1 END) AS prod_count
    RETURN test_count, prod_count,
           toFloat(test_count) / toFloat(prod_count) AS test_ratio
    """
)
```

**Test Ratio Guidelines:**
- **< 0.5:** Poor test coverage
- **0.5-1.0:** Moderate coverage
- **> 1.0:** Good coverage (more test code than production)

### Test Coverage by Module

Find which modules have tests and which don't:

```python
# Find modules and their test coverage
query_relationships(
    cypher_query="""
    MATCH (test:Frame)-[e:Edge {type: 'CALLS'}]->(prod:Frame)
    WHERE test.file_path CONTAINS 'test'
      AND NOT prod.file_path CONTAINS 'test'
      AND e.confidence >= 0.6
    WITH prod.file_path AS module, count(DISTINCT test) AS test_count
    RETURN module, test_count
    ORDER BY test_count
    LIMIT 50
    """
)

# Find production modules with NO tests
query_relationships(
    cypher_query="""
    MATCH (prod:Frame)
    WHERE prod.frame_type IN ['CALLABLE', 'CLASS']
      AND NOT prod.file_path CONTAINS 'test'
      AND prod.provenance = 'local'
      AND NOT EXISTS {
        MATCH (test:Frame)-[:Edge {type: 'CALLS'}]->(prod)
        WHERE test.file_path CONTAINS 'test'
      }
    WITH DISTINCT prod.file_path AS module
    RETURN module
    ORDER BY module
    LIMIT 50
    """
)
```

### Check Impact with Test Coverage

Built-in tool for comprehensive test coverage analysis:

```python
# Analyze with test coverage included
check_impact(
    target="CriticalClass",
    max_depth=2,
    include_test_coverage=True
)

# This shows:
# - Dependencies tree
# - Which dependencies are tested
# - Test coverage percentage
# - Risk assessment
```

### Find Untested Critical Code

Combine complexity and test coverage:

```python
# Step 1: Find complex functions (high risk if untested)
query_relationships(
    cypher_query="""
    MATCH (f:Frame)-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
    WHERE f.frame_type = 'CALLABLE'
      AND NOT f.file_path CONTAINS 'test'
      AND cf.frame_type IN ['IF_BLOCK', 'FOR_LOOP', 'TRY_BLOCK']
    WITH f.qualified_name AS func, f.file_path AS path, count(cf) AS complexity
    WHERE complexity >= 5
    RETURN func, path, complexity
    ORDER BY complexity DESC
    LIMIT 30
    """
)

# Step 2: Check if they have tests
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.qualified_name = 'complex_function_from_step1'
      AND EXISTS {
        MATCH (test:Frame)-[:Edge {type: 'CALLS'}]->(f)
        WHERE test.file_path CONTAINS 'test'
      }
    RETURN f.qualified_name, 'HAS TESTS' AS status
    """
)
```

### Test Coverage Priorities

```python
# High Priority: Public APIs without tests
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.frame_type IN ['CALLABLE', 'CLASS']
      AND NOT f.name STARTS WITH '_'
      AND NOT f.file_path CONTAINS 'test'
      AND NOT EXISTS {
        MATCH ()-[:Edge {type: 'CALLS'}]->(f)
        WHERE NOT f.file_path CONTAINS 'test'
      }
      AND NOT EXISTS {
        MATCH (test)-[:Edge {type: 'CALLS'}]->(f)
        WHERE test.file_path CONTAINS 'test'
      }
    RETURN f.qualified_name, f.file_path
    LIMIT 50
    """
)
```

### Test Coverage Workflow

```python
# Step 1: Get overall metrics
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.frame_type IN ['CALLABLE', 'CLASS']
      AND f.provenance = 'local'
    WITH
      count(CASE WHEN f.file_path CONTAINS 'test' THEN 1 END) AS test_count,
      count(CASE WHEN NOT f.file_path CONTAINS 'test' THEN 1 END) AS prod_count
    RETURN test_count, prod_count,
           toFloat(test_count) / toFloat(prod_count) AS test_ratio
    """
)

# Step 2: Find untested modules
query_relationships(cypher_query="...") # See "Find Untested Code" above

# Step 3: Prioritize by complexity
query_relationships(cypher_query="...") # See "Find Untested Critical Code"

# Step 4: Check specific targets
check_impact(target="UntesttedClass", include_test_coverage=True)
```

**Coverage Improvement Strategy:**
1. Test public APIs first (highest impact)
2. Test complex functions (high risk)
3. Test critical paths (authentication, data processing)
4. Test error handling (exception paths)
5. Test edge cases last (nice to have)

## TOOLS
- query_relationships()
- check_impact()

## REQUIRES
- foundation/call_graph_analysis
