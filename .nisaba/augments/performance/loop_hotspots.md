# Performance
## Loop Hotspots
Path: performance/loop_hotspots

Finding loop-related performance issues - nested loops, database calls in loops, O(n²) patterns.

### Nested Loops (O(n²) or worse)

```python
# Find nested loops
query_relationships(
    cypher_query="""
    MATCH (f:Frame)-[:Edge {type: 'CONTAINS'}*1]->(outer:Frame)-[:Edge {type: 'CONTAINS'}*1]->(inner:Frame)
    WHERE f.frame_type = 'CALLABLE'
      AND outer.frame_type IN ['FOR_LOOP', 'WHILE_LOOP']
      AND inner.frame_type IN ['FOR_LOOP', 'WHILE_LOOP']
    RETURN DISTINCT f.qualified_name, f.file_path
    LIMIT 50
    """
)

# Examine structure in detail
show_structure(
    target="nested_loop_function",
    detail_level="structure",
    structure_detail_depth=3
)
```

**Why nested loops are problematic:**
- **O(n²) complexity:** Scales poorly with input size
- **Becomes O(n³)** with triple nesting
- **Can often be optimized** with hash maps, pre-processing

**Optimization strategies:**
- Use hash maps for O(1) lookups instead of inner loop
- Pre-sort and use binary search
- Use set operations instead of nested iteration
- Consider algorithmic alternatives (sorting, hashing)

### Database Calls in Loops (N+1 Query Problem)

```python
# Search for loops that might contain database calls
search(query="for.*in.*execute query fetch", k=30, context_lines=7)

# Use Cypher to find LOOPS containing CALLS to database functions
query_relationships(
    cypher_query="""
    MATCH (loop:Frame)-[:Edge {type: 'CONTAINS'}*]->(call_site:Frame)-[e:Edge {type: 'CALLS'}]->(db_func:Frame)
    WHERE loop.frame_type IN ['FOR_LOOP', 'WHILE_LOOP']
      AND (db_func.name CONTAINS 'query'
           OR db_func.name CONTAINS 'execute'
           OR db_func.name CONTAINS 'fetch'
           OR db_func.name CONTAINS 'get'
           OR db_func.name CONTAINS 'find')
      AND e.confidence >= 0.5
    RETURN DISTINCT call_site.qualified_name, loop.qualified_name
    LIMIT 30
    """
)
```

**The N+1 problem:**
```python
# Bad: N+1 queries
for user in users:  # 1 query
    orders = get_orders(user.id)  # N queries
    process(orders)

# Good: 2 queries total
user_ids = [u.id for u in users]
all_orders = get_orders_batch(user_ids)
for user in users:
    orders = all_orders[user.id]
    process(orders)
```

**Fix strategies:**
- Batch queries (fetch all at once)
- Use JOIN operations
- Eager loading in ORMs
- Caching frequently accessed data

### Large Data Processing

```python
# Search for large file/collection processing
search(query="read.*file.*for.*line|load.*csv|read.*json", k=30)

# Find functions processing large inputs
search(
    query="def.*process.*data|def.*parse.*file",
    is_regex_input=True,
    k=30
)
```

**Performance patterns:**
```python
# Bad: Load entire file into memory
data = file.read()
for line in data.split('\n'):
    process(line)

# Good: Stream processing
for line in file:
    process(line)
```

### Loop Performance Checklist

For each loop found, check:

1. **Is it nested?** → Consider O(n²) alternatives
2. **Does it call database?** → Batch the queries
3. **Does it call network?** → Async or parallelize
4. **Does it allocate large objects?** → Pre-allocate or reuse
5. **Can it be vectorized?** → Use NumPy/pandas operations

### Detailed Analysis Workflow

```python
# Step 1: Find all nested loops
query_relationships(cypher_query="...") # See nested loops query

# Step 2: Examine structure
show_structure(target="suspect_function", detail_level="structure")

# Step 3: Search for database/network calls
search(query="execute query http request", k=20, context_lines=10)

# Step 4: Check context
search(query="specific_function_name", k=5, context_lines=15)
```

### Common Loop Antipatterns

```python
# Antipattern 1: String concatenation in loop
search(query="for.*in.*:.*+=.*str", k=20)

# Antipattern 2: List append in loop (when size known)
search(query="for.*in.*append", k=20)

# Antipattern 3: Repeated attribute access
search(query="for.*in.*self\\.", k=20)
```

**Fixes:**
```python
# String concat: Use join()
result = ''.join(items) instead of result += item

# List append: Pre-allocate
result = [None] * size

# Attribute: Cache in local variable
local_var = self.attribute
```

## TOOLS
- query_relationships()
- search()
- show_structure()
