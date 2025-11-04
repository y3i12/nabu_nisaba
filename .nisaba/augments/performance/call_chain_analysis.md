# Performance
## Call Chain Analysis
Path: performance/call_chain_analysis

Analyzing call chains for performance issues - deep call stacks, recursive functions, critical path optimization.

### Find Longest Call Chains

```python
# Find long call chains (potential performance bottleneck)
query_relationships(
    cypher_query="""
    MATCH path = (a:Frame)-[:Edge {type: 'CALLS'}*3..10]->(b:Frame)
    WHERE ALL(e IN relationships(path) WHERE e.confidence >= 0.7)
    WITH path, length(path) AS depth
    RETURN [node IN nodes(path) | node.qualified_name] AS call_chain, depth
    ORDER BY depth DESC
    LIMIT 20
    """
)
```

**Why deep call chains matter:**
- **Stack overhead:** Each call adds stack frame
- **Context switching:** CPU cache misses
- **Debugging difficulty:** Hard to trace issues
- **Latency accumulation:** Each hop adds time

**When it's a problem:**
- **Synchronous I/O in chain:** Each call waits
- **Repeated work:** No memoization
- **Fine-grained calls:** Too much overhead

### Recursive Function Detection

```python
# Find self-referential functions (recursion)
query_relationships(
    cypher_query="""
    MATCH (f:Frame)-[e:Edge {type: 'CALLS'}]->(f)
    WHERE f.frame_type = 'CALLABLE'
      AND e.confidence >= 0.5
    RETURN f.qualified_name, f.file_path
    LIMIT 30
    """
)
```

**Recursion considerations:**
- **Stack depth limits:** Python ~1000 calls default
- **No tail-call optimization** in Python
- **Consider iterative alternative**
- **Memoization for repeated work**

**When recursion is appropriate:**
- Tree/graph traversal
- Divide-and-conquer algorithms
- Depth is bounded and known
- Code clarity is much better

**When to avoid:**
- Deep recursion (>100 levels)
- Linear recursion (use iteration)
- Hot paths (performance-critical)

### Critical Path Analysis

Find the most-called functions (hot paths):

```python
# Find most-called functions
query_relationships(
    cypher_query="""
    MATCH ()-[e:Edge {type: 'CALLS'}]->(target:Frame)
    WHERE target.provenance = 'local'
      AND e.confidence >= 0.7
    WITH target.qualified_name AS func, count(e) AS call_count
    WHERE call_count >= 5
    RETURN func, call_count
    ORDER BY call_count DESC
    LIMIT 30
    """
)
```

**Hot path optimization priorities:**
1. **Most called functions** → Biggest impact
2. **Functions in loops** → Multiplied cost
3. **Synchronous I/O** → Async alternatives
4. **Expensive operations** → Cache or pre-compute

### Call Chain Depth by Entry Point

```python
# Analyze depth from specific entry points
query_relationships(
    cypher_query="""
    MATCH path = (entry:Frame)-[:Edge {type: 'CALLS'}*1..8]->(target:Frame)
    WHERE entry.name = 'main'
      OR entry.name CONTAINS 'endpoint'
      OR entry.name CONTAINS 'handler'
    WITH entry.qualified_name AS entry_point,
         AVG(length(path)) AS avg_depth,
         MAX(length(path)) AS max_depth
    RETURN entry_point, avg_depth, max_depth
    ORDER BY max_depth DESC
    LIMIT 20
    """
)
```

### Find Call Chains Through Specific Functions

```python
# Find all paths that go through a specific function
query_relationships(
    cypher_query="""
    MATCH path = (start:Frame)-[:Edge {type: 'CALLS'}*]->(middle:Frame)-[:Edge {type: 'CALLS'}*]->(end:Frame)
    WHERE middle.qualified_name = 'expensive_function'
      AND start.name IN ['main', 'handler']
    WITH path, length(path) AS depth
    RETURN [node IN nodes(path) | node.qualified_name] AS call_chain, depth
    ORDER BY depth DESC
    LIMIT 20
    """
)
```

### Optimization Strategies

**1. Memoization:**
```python
# Cache expensive function results
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(arg):
    ...
```

**2. Inlining Hot Functions:**
```python
# Reduce call overhead by inlining small, frequently-called functions
# (or rely on compiler/interpreter)
```

**3. Async for I/O-bound chains:**
```python
# Convert sync chain: A → B → C (each waits)
# To async: await asyncio.gather(A(), B(), C())
```

**4. Batch operations:**
```python
# Instead of: for item in items: process_one(item)
# Do: process_batch(items)
```

### Performance Analysis Workflow

```python
# Step 1: Find long call chains
query_relationships(cypher_query="...") # See longest chains query

# Step 2: Find recursive functions
query_relationships(cypher_query="...") # See recursion query

# Step 3: Identify hot paths
query_relationships(cypher_query="...") # See most-called query

# Step 4: Examine critical functions
show_structure(
    target="hot_function",
    detail_level="structure",
    include_relationships=True,
    max_callers=50
)

# Step 5: Profile in practice (tools like cProfile, py-spy)
```

**Profiling complements graph analysis:**
- **Graph analysis:** Shows structure, potential issues
- **Profiling:** Shows actual runtime, real bottlenecks
- **Use both:** Structure guides where to profile

## TOOLS
- query_relationships()

## REQUIRES
- foundation/call_graph_analysis
