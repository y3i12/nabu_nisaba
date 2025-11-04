# Refactoring
## Clone Consolidation
Path: refactoring/clone_consolidation

Finding and preparing to consolidate duplicate code.

### Step 1: Find Clones

```python
# Find high-similarity clones (likely candidates)
find_clones(min_similarity=0.75, max_results=50)

# More aggressive (includes near-duplicates)
find_clones(min_similarity=0.65, max_results=100)

# Target specific functionality
find_clones(
    query="database connection handling",
    query_k=30,
    min_similarity=0.70
)

# Only significant functions, cross-file
find_clones(
    min_similarity=0.80,
    min_function_size=15,
    exclude_same_file=True
)
```

### Step 2: Compare Clone Structures

Examine each clone's structure to understand differences:

```python
# Get structure of first clone
show_structure(
    target="validate_user_input_v1",
    detail_level="structure",
    structure_detail_depth=2
)

# Get structure of second clone
show_structure(
    target="validate_user_input_v2",
    detail_level="structure",
    structure_detail_depth=2
)

# If they're methods, include class context
show_structure(
    target="ClassA",
    detail_level="guards",
    include_relationships=True
)
```

### Step 3: Impact Analysis for Each Clone

Check who depends on each clone variant:

```python
# Check impact of consolidating first clone
check_impact(
    target="validate_user_input_v1",
    max_depth=2,
    include_test_coverage=True
)

# Check impact of consolidating second clone
check_impact(
    target="validate_user_input_v2",
    max_depth=2,
    include_test_coverage=True
)
```

### Step 4: Verify Semantic Differences

Search for context around each clone:

```python
# Get context for first clone
search(
    query="validate_user_input_v1",
    k=10,
    context_lines=10
)

# Get context for second clone
search(
    query="validate_user_input_v2",
    k=10,
    context_lines=10
)
```

### Consolidation Decision Matrix

**Similarity > 0.85:**
- Strong extraction candidate
- Differences likely in minor details
- Action: Extract to shared function

**Similarity 0.70-0.85:**
- Consider parameterization
- Differences may be intentional variants
- Action: Extract with parameters for variations

**Similarity < 0.70:**
- May be coincidental similarity
- Manual review strongly recommended
- Action: Keep separate unless proven duplication

### Refactoring Strategies

**1. Extract Common Function:**
```python
# Before: clone_1 and clone_2 with 85% similarity
# After: shared_function() called by both
```

**2. Parameterize Differences:**
```python
# Before: validate_v1(data) and validate_v2(data)
# After: validate(data, strict=True/False)
```

**3. Template Method Pattern:**
```python
# Before: ProcessorA and ProcessorB with similar flow
# After: BaseProcessor with template method, variants override steps
```

**4. Strategy Pattern:**
```python
# Before: Multiple similar implementations
# After: Common interface, pluggable strategies
```

### Complete Consolidation Workflow

```python
# 1. Find clones
find_clones(min_similarity=0.75, max_results=50)

# 2. For each clone pair:
#    a. Compare structures
show_structure(target="clone_1", detail_level="structure")
show_structure(target="clone_2", detail_level="structure")

#    b. Check impact
check_impact(target="clone_1", max_depth=2)
check_impact(target="clone_2", max_depth=2)

#    c. Verify differences
search(query="clone_1", k=5, context_lines=10)
search(query="clone_2", k=5, context_lines=10)

# 3. Make consolidation decision based on:
#    - Similarity score
#    - Impact analysis (how many dependents)
#    - Test coverage (is it safe to refactor?)
#    - Semantic differences (are they intentional?)
```

### Post-Consolidation Validation

After consolidating:
1. Run tests to verify behavior preserved
2. Re-check impact to ensure no new issues
3. Search for any missed variants
4. Update documentation

## TOOLS
- find_clones()
- show_structure()
- check_impact()

## REQUIRES
- refactoring/impact_analysis
