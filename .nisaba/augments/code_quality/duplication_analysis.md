# Code Quality
## Duplication Analysis
Path: code_quality/duplication_analysis

Code clone detection strategies for finding duplicate or similar implementations.

### Method 1: Built-in Clone Detection

```python
# Find all clones with default threshold (0.75 = true duplicates)
find_clones(min_similarity=0.75, max_results=50)

# More aggressive detection (includes near-duplicates)
find_clones(min_similarity=0.65, max_results=100)

# Target specific functionality
find_clones(
    query="database connection handling",
    query_k=30,
    min_similarity=0.70
)

# Exclude trivial functions, only cross-file clones
find_clones(
    min_similarity=0.80,
    min_function_size=15,
    exclude_same_file=True,
    max_results=50
)
```

**Similarity Thresholds:**
- **0.80-1.0:** Near-identical code (copy-paste)
- **0.70-0.79:** Similar logic, different details
- **0.60-0.69:** Related patterns (may be coincidental)

### Method 2: Naming Patterns Suggesting Duplication

Look for naming patterns that often indicate duplicated code:

```python
# Find versioned functions (usually duplicates)
search(
    query=".*_v1$|.*_v2$|.*_old$|.*_new$|.*_copy$",
    is_regex_input=True,
    k=50
)

# Find numbered variants
search(
    query=".*[0-9]$",
    is_regex_input=True,
    frame_type_filter="CALLABLE|CLASS",
    k=50
)

# Common duplicate naming patterns
search(query="temp backup deprecated legacy", k=30)
```

### Method 3: Structure Comparison

Compare suspected duplicates side-by-side:

```python
# Get detailed structure of both variants
show_structure(target="function_v1", detail_level="structure")
show_structure(target="function_v2", detail_level="structure")

# Compare control flow patterns
show_structure(
    target="function_v1",
    detail_level="structure",
    structure_detail_depth=2
)
```

### Method 4: Clone Consolidation Workflow

Complete workflow for handling found clones:

```python
# Step 1: Find clones
find_clones(min_similarity=0.75)

# Step 2: Examine structure of each clone
show_structure(target="clone_1", detail_level="guards")
show_structure(target="clone_2", detail_level="guards")

# Step 3: Check impact of consolidating each
check_impact(target="clone_1", max_depth=2)
check_impact(target="clone_2", max_depth=2)

# Step 4: Verify no critical differences
search(query="clone_1", k=10, context_lines=10)
search(query="clone_2", k=10, context_lines=10)
```

**Consolidation Strategy:**
- If similarity > 0.85: Strong candidate for extraction
- If similarity 0.70-0.85: Consider parameterization
- If similarity < 0.70: May be coincidental, manual review needed

**Refactoring Approaches:**
1. **Extract common logic** → Create shared function
2. **Parameterize differences** → Pass variations as arguments
3. **Template method pattern** → Base class with variants
4. **Strategy pattern** → Pluggable implementations

## TOOLS
- find_clones()
- search()
- show_structure()
