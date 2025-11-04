# Workflows
## Pre-Refactoring Workflow
Path: workflows/pre_refactoring

Complete pre-refactoring analysis workflow - understand structure, check impact, find duplicates, verify tests.

This workflow combines multiple analysis skills to safely prepare for refactoring.

### Workflow Overview

**Goal:** Gather all necessary information before changing code to minimize risk.

**Steps:**
1. Understand current structure
2. Find all dependencies
3. Identify similar code
4. Verify test coverage
5. Check critical dependencies

### Step 1: Understand Current Structure

Get clean API overview:

```python
# Get structure with minimal detail (token-efficient)
show_structure(target="TargetClass", detail_level="minimal")

# If needed, add behavioral hints
show_structure(
    target="TargetClass",
    detail_level="guards",
    include_relationships=True
)
```

**What to look for:**
- Method signatures (what's the API?)
- Public vs private methods
- Dependencies on other classes
- Who inherits from this class?

### Step 2: Find All Dependencies

Check who depends on this code:

```python
# Extended impact (2 levels deep)
check_impact(
    target="TargetClass",
    max_depth=2,
    include_test_coverage=True,
    risk_assessment=True
)
```

**Interpret results:**
- **High risk:** Many dependents, low test coverage
- **Medium risk:** Moderate dependents, some tests
- **Low risk:** Few dependents, well-tested

### Step 3: Find Similar Code

Look for duplicates or similar implementations:

```python
# Find clones of this code
find_clones(
    query="TargetClass functionality description",
    query_k=20,
    min_similarity=0.70
)

# Or find all clones globally
find_clones(min_similarity=0.75, max_results=50)
```

**Consider consolidation:**
- If similarity > 0.80: Strong consolidation candidate
- Check if clones should be unified with refactoring
- May reveal better abstraction

### Step 4: Verify Test Coverage

Ensure changes can be safely tested:

```python
# Already included in check_impact above, but can also:
query_relationships(
    cypher_query="""
    MATCH (test:Frame)-[e:Edge {type: 'CALLS'}]->(target:Frame)
    WHERE target.qualified_name CONTAINS 'TargetClass'
      AND test.file_path CONTAINS 'test'
      AND e.confidence >= 0.6
    RETURN test.qualified_name, test.file_path
    LIMIT 50
    """
)
```

**Test coverage goals:**
- All public methods tested
- Edge cases covered
- Integration tests for critical paths

### Step 5: Verify Critical Dependencies

Double-check high-confidence dependencies:

```python
# Find direct callers with high confidence
query_relationships(
    cypher_query="""
    MATCH (caller)-[e:Edge {type: 'CALLS'}]->(target:Frame)
    WHERE target.qualified_name CONTAINS 'TargetClass'
      AND e.confidence >= 0.7
    RETURN caller.qualified_name, caller.file_path, e.confidence
    ORDER BY e.confidence DESC
    LIMIT 50
    """
)
```

**Focus on:**
- High-confidence callers (>0.8)
- Critical paths (main → target)
- Public API usage

### Complete Workflow Example

```python
# === PRE-REFACTORING CHECKLIST ===

# 1. Structure
show_structure(target="MyClass", detail_level="minimal")

# 2. Impact
check_impact(
    target="MyClass",
    max_depth=2,
    include_test_coverage=True,
    risk_assessment=True
)

# 3. Duplicates
find_clones(query="MyClass", query_k=20, min_similarity=0.70)

# 4. Test coverage (if not clear from check_impact)
query_relationships(
    cypher_query="""
    MATCH (test:Frame)-[:Edge {type: 'CALLS'}]->(target:Frame)
    WHERE target.qualified_name = 'MyClass'
      AND test.file_path CONTAINS 'test'
    RETURN count(test) AS test_count
    """
)

# 5. Critical deps
query_relationships(
    cypher_query="""
    MATCH (caller)-[e:Edge {type: 'CALLS'}]->(target:Frame)
    WHERE target.qualified_name = 'MyClass'
      AND e.confidence >= 0.7
    RETURN caller.qualified_name, e.confidence
    ORDER BY e.confidence DESC
    LIMIT 30
    """
)
```

### Decision Matrix

**Safe to refactor when:**
- ✅ Well-tested (>80% coverage)
- ✅ Clear structure understood
- ✅ Few dependents (<10) OR all internal
- ✅ No duplicates found OR consolidation planned
- ✅ High confidence relationships (>0.7)

**Risky - proceed with caution:**
- ⚠️ Low test coverage (<50%)
- ⚠️ Many external dependents (>20)
- ⚠️ Complex structure (high coupling)
- ⚠️ Low confidence edges (<0.5)

**Do NOT refactor yet:**
- ❌ No tests
- ❌ Critical production path
- ❌ Unknown dependencies
- ❌ Duplicates not analyzed

### Post-Analysis Actions

Based on findings:

1. **Add missing tests** before refactoring
2. **Document dependencies** for review
3. **Plan consolidation** if duplicates found
4. **Communicate changes** to dependent teams
5. **Create feature flag** for risky changes

## TOOLS
- show_structure()
- check_impact()
- find_clones()
- query_relationships()

## REQUIRES
- refactoring/impact_analysis
- refactoring/clone_consolidation
- testing/test_coverage_analysis
