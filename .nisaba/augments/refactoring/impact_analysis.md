# Refactoring
## Impact Analysis
Path: refactoring/impact_analysis

Understanding blast radius before making changes - what depends on the code you're about to modify?

### Basic Impact Check

```python
# Direct and extended dependencies (recommended default)
check_impact(target="MyClass", max_depth=2)

# Deep traversal with test coverage
check_impact(
    target="database_connect",
    max_depth=3,
    include_test_coverage=True,
    risk_assessment=True
)
```

### Depth Guidelines

- **max_depth=1:** Direct dependents only (fast, ~50-200ms)
- **max_depth=2:** Extended impact (recommended default, ~200-500ms)
- **max_depth=3:** Full propagation (can be large, ~500ms-2s)

**Use depth=1 for:**
- Quick checks during development
- Understanding immediate dependencies

**Use depth=2 for:**
- Pre-refactoring safety checks
- Understanding realistic blast radius

**Use depth=3 for:**
- Critical infrastructure changes
- Core library modifications

### Multiple Targets via Regex

Analyze impact of multiple related changes:

```python
# Check impact of all Manager classes
check_impact(
    target=".*Manager$",
    is_regex=True,
    max_depth=2,
    visualization="mermaid"
)

# Check impact of all handle_* functions
check_impact(
    target="handle_.*",
    is_regex=True,
    max_depth=1
)
```

### Specific Codebase Analysis

```python
# Check impact within a specific codebase
check_impact(
    target="utils.parser",
    codebase="my_lib",
    max_depth=2
)
```

### Interpreting Results

**Risk Assessment Indicators:**
- **High Risk:** Many dependents, used in critical paths, low test coverage
- **Medium Risk:** Moderate dependents, some test coverage
- **Low Risk:** Few dependents, well-tested, isolated

**Dependency Tree Analysis:**
```
MyClass
├─ DirectDependent1 (confidence: 0.9)
│  ├─ IndirectDependent1 (confidence: 0.8)
│  └─ IndirectDependent2 (confidence: 0.7)
└─ DirectDependent2 (confidence: 0.85)
   └─ IndirectDependent3 (confidence: 0.6)
```

### Combining with Structure Examination

```python
# Step 1: Understand current API
show_structure(target="MyClass", detail_level="minimal")

# Step 2: Check impact
check_impact(target="MyClass", max_depth=2, include_test_coverage=True)

# Step 3: Verify critical dependencies with Cypher
query_relationships(
    cypher_query="""
    MATCH (caller)-[e:Edge {type: 'CALLS'}]->(target:Frame {qualified_name: "MyClass.critical_method"})
    WHERE e.confidence >= 0.7
    RETURN caller.qualified_name, caller.file_path, e.confidence
    ORDER BY e.confidence DESC
    LIMIT 50
    """
)
```

### Pre-Change Checklist

1. **Understand structure** → `show_structure()`
2. **Check impact** → `check_impact(max_depth=2)`
3. **Verify test coverage** → `check_impact(include_test_coverage=True)`
4. **Check confidence** → Filter results by confidence tier
5. **Review critical deps** → Manual inspection of high-impact dependents

**Breaking Change Risk Factors:**
- Many high-confidence dependents (>10)
- Used in critical paths (main → target)
- Low test coverage (<50%)
- External package dependencies

## TOOLS
- check_impact()
- show_structure()
