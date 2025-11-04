# Documentation
## Documentation Gaps
Path: documentation/doc_gaps

Finding undocumented or poorly documented code, naming consistency issues.

### Find Public APIs Without Docstrings

```python
# Find public classes and functions (candidates for documentation)
search(
    query="^def [^_]|^class [^_]",
    is_regex_input=True,
    k=50
)

# Then examine with docstrings
show_structure(
    target="PublicClass",
    detail_level="minimal",
    include_docstrings=True,
    include_private=False
)
```

**Manual verification needed:** Check if docstrings exist and are meaningful.

### Find Complex Functions Without Documentation

Complex functions (many control structures) likely need documentation:

```python
# Find complex functions (>= 5 control structures)
query_relationships(
    cypher_query="""
    MATCH (f:Frame)-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
    WHERE f.frame_type = 'CALLABLE'
      AND NOT f.name STARTS WITH '_'
      AND cf.frame_type IN ['IF_BLOCK', 'FOR_LOOP', 'TRY_BLOCK']
    WITH f.qualified_name AS func, f.file_path AS path, count(cf) AS complexity
    WHERE complexity >= 5
    RETURN func, path, complexity
    ORDER BY complexity DESC
    LIMIT 30
    """
)

# Then examine for docstrings
show_structure(target="complex_function", include_docstrings=True)
```

### Find Public Classes Without Documentation

```python
# Find public classes (likely need docs)
query_relationships(
    cypher_query="""
    MATCH (c:Frame)
    WHERE c.frame_type = 'CLASS'
      AND NOT c.name STARTS WITH '_'
      AND c.provenance = 'local'
    RETURN c.qualified_name, c.file_path
    LIMIT 50
    """
)

# Check each for docstrings
show_structure(
    target="PublicClass",
    include_docstrings=True,
    include_private=False
)
```

### Naming Consistency Analysis

Find naming convention violations:

```python
# Find classes not in PascalCase
search(
    query="class [a-z_]",
    is_regex_input=True,
    frame_type_filter="CLASS",
    k=30
)

# Find functions not in snake_case
search(
    query="def [A-Z]|def .*[A-Z]",
    is_regex_input=True,
    frame_type_filter="CALLABLE",
    k=30
)
```

### Inconsistent Verb Usage

Find similar operations with different naming:

```python
# CRUD operations - should be consistent
search(query="get_* fetch_* retrieve_* obtain_*", k=50)
search(query="create_* make_* build_* generate_*", k=50)
search(query="delete_* remove_* destroy_* clear_*", k=50)
search(query="update_* modify_* change_* set_*", k=50)

# Find most common pattern, standardize on it
```

**Standardization strategy:**
1. Count usage of each variant
2. Pick most common as standard
3. Refactor others to match
4. Document the convention

### Abbreviation Inconsistencies

```python
# Find abbreviation variations
search(query="config configuration cfg", k=30)
search(query="msg message mesg", k=30)
search(query="temp temporary tmp", k=30)
search(query="num number nbr", k=30)
search(query="str string", k=30)
```

**Resolution:**
- Pick one abbreviation strategy per codebase
- Either: Never abbreviate (configuration)
- Or: Standard abbreviations (cfg, msg, tmp)
- Document the choice

### Documentation Priority Matrix

**High Priority (document first):**
- Public APIs (classes, functions)
- Complex functions (>5 control structures)
- Non-obvious algorithms
- Public interfaces used by external code

**Medium Priority:**
- Internal helper functions
- Data structures/classes
- Configuration options
- Error handling patterns

**Low Priority:**
- Private methods (unless complex)
- Trivial getters/setters
- Self-explanatory code
- Test utilities

### Documentation Workflow

```python
# Step 1: Find undocumented public APIs
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.frame_type IN ['CLASS', 'CALLABLE']
      AND NOT f.name STARTS WITH '_'
      AND f.provenance = 'local'
    RETURN f.qualified_name, f.file_path
    LIMIT 100
    """
)

# Step 2: Check docstrings
show_structure(target="each_candidate", include_docstrings=True)

# Step 3: Find complex undocumented code
query_relationships(cypher_query="...") # See complex functions query

# Step 4: Check naming consistency
search(query="class [a-z]|def [A-Z]", is_regex_input=True)

# Step 5: Prioritize based on:
# - Public API? (high)
# - Complex? (high)
# - Frequently used? (check callers)
# - Naming issues? (medium)
```

### Naming Convention Guidelines

**Python conventions:**
- **Classes:** PascalCase (MyClass)
- **Functions/methods:** snake_case (my_function)
- **Constants:** UPPER_SNAKE_CASE (MY_CONSTANT)
- **Private:** prefix with _ (_internal_method)

**Consistency checks:**
```python
# Find constant candidates not in UPPER_CASE
search(query="^[a-z_]*=.*['\"]", is_regex_input=True, k=30)

# Find private methods without underscore
search(query="def [a-z]", is_regex_input=True, k=50)
```

### Documentation Quality Checklist

Good docstrings include:

1. **Purpose** - What does it do?
2. **Parameters** - What inputs? Types? Constraints?
3. **Returns** - What output? Type?
4. **Raises** - What exceptions?
5. **Examples** - Usage examples for complex APIs

**Example:**
```python
def calculate_total(items: List[Item], discount: float = 0.0) -> Decimal:
    """Calculate total price with optional discount.

    Args:
        items: List of items to sum
        discount: Percentage discount (0.0-1.0)

    Returns:
        Total price after discount

    Raises:
        ValueError: If discount not in range [0, 1]

    Example:
        >>> calculate_total([item1, item2], discount=0.1)
        Decimal('45.00')
    """
```

## TOOLS
- search()
- query_relationships()
- show_structure()
