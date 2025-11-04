# Testing
## Test Quality
Path: testing/test_quality

Analyzing test structure and quality - finding orphaned tests, understanding test patterns.

### Find Orphaned Test Files

Test files that don't actually test local code:

```python
# Find test files that don't call any production code
query_relationships(
    cypher_query="""
    MATCH (test:Frame)
    WHERE test.file_path CONTAINS 'test'
      AND test.frame_type IN ['CALLABLE', 'CLASS']
      AND NOT EXISTS {
        MATCH (test)-[:Edge {type: 'CALLS'}]->(prod:Frame)
        WHERE NOT prod.file_path CONTAINS 'test'
          AND prod.provenance = 'local'
      }
    RETURN DISTINCT test.file_path
    LIMIT 50
    """
)
```

**Why orphaned tests exist:**
- Refactored code, tests left behind
- Tests only test external libraries
- Mock-heavy tests with no real code calls
- Integration tests that call external services

### Test Structure Analysis

Find test patterns and conventions:

```python
# Find test naming patterns
search(
    query="def test_|class Test",
    is_regex_input=True,
    k=50
)

# Find test frameworks in use
search(query="unittest pytest fixture describe it", k=30)

# Find assertion patterns
search(
    query="assert.*==|assertEqual|expect|should",
    is_regex_input=True,
    k=30,
    context_lines=3
)
```

### Test Complexity

Find overly complex tests (may indicate production code issues):

```python
# Find tests with high control flow complexity
query_relationships(
    cypher_query="""
    MATCH (test:Frame)-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
    WHERE test.file_path CONTAINS 'test'
      AND test.frame_type = 'CALLABLE'
      AND cf.frame_type IN ['IF_BLOCK', 'FOR_LOOP', 'WHILE_LOOP']
    WITH test.qualified_name AS test_func, count(cf) AS complexity
    WHERE complexity >= 3
    RETURN test_func, complexity
    ORDER BY complexity DESC
    LIMIT 30
    """
)
```

**Complex tests indicate:**
- Production code is hard to test (refactor needed)
- Test is doing too much (split into multiple tests)
- Missing test fixtures or helpers

### Test Dependencies

Find what production code is most tested:

```python
# Find most-tested production code
query_relationships(
    cypher_query="""
    MATCH (test:Frame)-[e:Edge {type: 'CALLS'}]->(prod:Frame)
    WHERE test.file_path CONTAINS 'test'
      AND NOT prod.file_path CONTAINS 'test'
      AND prod.provenance = 'local'
      AND e.confidence >= 0.6
    WITH prod.qualified_name AS production_code, count(DISTINCT test) AS test_count
    RETURN production_code, test_count
    ORDER BY test_count DESC
    LIMIT 30
    """
)

# Find what tests depend on
query_relationships(
    cypher_query="""
    MATCH (test:Frame)-[e:Edge]->(dep:Frame)
    WHERE test.file_path CONTAINS 'test'
      AND NOT dep.file_path CONTAINS 'test'
      AND e.type IN ['CALLS', 'IMPORTS']
    WITH test.qualified_name AS test, count(DISTINCT dep) AS dependencies
    WHERE dependencies >= 5
    RETURN test, dependencies
    ORDER BY dependencies DESC
    LIMIT 30
    """
)
```

### Fixture and Helper Analysis

Find test utilities and fixtures:

```python
# Find pytest fixtures
search(
    query="@pytest\\.fixture|@fixture",
    is_regex_input=True,
    k=30
)

# Find test helpers
search(
    query="def.*helper|def.*mock|def.*stub|def.*fake",
    is_regex_input=True,
    frame_type_filter="CALLABLE",
    k=30
)

# Find setup/teardown
search(query="setUp tearDown before after", k=30)
```

### Test Coverage Gaps by Feature

Find features with insufficient tests:

```python
# Step 1: Find all classes in a feature
search(query="class.*User.*Manager", k=20)

# Step 2: Check which have tests
query_relationships(
    cypher_query="""
    MATCH (prod:Frame)
    WHERE prod.qualified_name CONTAINS 'UserManager'
      AND NOT prod.file_path CONTAINS 'test'
    OPTIONAL MATCH (test:Frame)-[:Edge {type: 'CALLS'}]->(prod)
    WHERE test.file_path CONTAINS 'test'
    RETURN prod.qualified_name,
           count(test) AS test_count
    ORDER BY test_count
    """
)
```

### Test Isolation Issues

Find tests that might have isolation problems:

```python
# Find tests that use global state
search(
    query="global.*=|os\\.environ\\[",
    is_regex_input=True,
    k=30,
    context_lines=5
)

# Find tests with database commits (integration tests)
search(query="commit rollback session.add", k=30)

# Find tests with file I/O (brittle)
search(
    query="open\\(.*w|write\\(|with.*open",
    is_regex_input=True,
    k=30
)
```

### Test Quality Checklist

For each test file, check:

1. **Tests local code** - Not orphaned ✓
2. **Clear naming** - test_* or Test* convention ✓
3. **Simple structure** - Low complexity ✓
4. **Isolated** - No global state, file I/O ✓
5. **Fast** - No database, network calls ✓
6. **Assertions** - Actually verify behavior ✓

### Test Improvement Workflow

```python
# Step 1: Find orphaned tests
query_relationships(cypher_query="...") # See above

# Step 2: Find complex tests
query_relationships(cypher_query="...") # See complexity query

# Step 3: Find isolation issues
search(query="global commit write open", k=50)

# Step 4: Prioritize fixes
# - Remove orphaned tests (no value)
# - Simplify complex tests (hard to maintain)
# - Mock integration points (speed/reliability)
```

**Test Quality Targets:**
- **Orphaned tests:** 0%
- **Complex tests (>3 branches):** <10%
- **Integration tests:** <20% of total
- **Test execution time:** <5 seconds for unit tests

## TOOLS
- query_relationships()
- search()
