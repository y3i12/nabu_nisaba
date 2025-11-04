# Foundation
## Confidence Filtering
Path: foundation/confidence_filtering

Understanding edge quality and filtering strategies to avoid false positives in analysis.

### Confidence Tiers

**HIGH (≥0.8):** Direct AST parsing, trust completely
**MEDIUM (0.5-0.79):** Cross-reference resolution, generally reliable
**LOW (0.2-0.49):** Heuristic matching, verify before trusting
**SPECULATIVE (<0.2):** Fuzzy resolution, likely false positives

### Edge Confidence Calculation

**Critical Insight:** Edge confidence = min(source, target) × type_multiplier

If Frame A (conf=1.0) calls Frame B (conf=0.3), the edge has conf ≈ 0.25-0.3

The chain is only as strong as its weakest link.

### Filtering by Confidence in Cypher

```python
# Only high-confidence relationships
query_relationships(
    cypher_query="""
    MATCH (a)-[e:Edge]->(b)
    WHERE e.confidence >= 0.8
    RETURN a.qualified_name, e.type, b.qualified_name
    LIMIT 50
    """
)

# High and medium confidence
query_relationships(
    cypher_query="""
    MATCH (a)-[e:Edge]->(b)
    WHERE e.confidence_tier IN ['HIGH', 'MEDIUM']
    RETURN a.qualified_name, e.type, b.qualified_name
    LIMIT 50
    """
)

# Exclude speculative relationships
query_relationships(
    cypher_query="""
    MATCH (a)-[e:Edge]->(b)
    WHERE e.confidence >= 0.5
    RETURN a.qualified_name, e.type, b.qualified_name
    LIMIT 50
    """
)
```

### Understanding Confidence Distribution

Use `show_status()` with debug mode to see edge confidence breakdown:

```python
# Full debug info including confidence distribution
show_status(detail_level="debug")
```

### Multi-Pass Parsing & Confidence Decay

**Pass 1:** Raw AST extraction → confidence=1.0 (direct parsing)
**Pass 2:** Frame hierarchy + imports → confidence=0.6-0.9 (inferred)
**Pass 3:** Symbol resolution → confidence=0.3-0.6 (fuzzy)
**Pass 4+:** Speculative → confidence=0.1-0.2 (guessing)

### When to Use Different Thresholds

```python
# Critical analysis: use >= 0.8
# Example: Finding dependencies for refactoring
MATCH (a)-[e:Edge {type: 'CALLS'}]->(b)
WHERE e.confidence >= 0.8

# General analysis: use >= 0.6
# Example: Understanding architecture
MATCH (a)-[e:Edge]->(b)
WHERE e.confidence >= 0.6

# Exploratory: use >= 0.5
# Example: Finding potential relationships
MATCH (a)-[e:Edge]->(b)
WHERE e.confidence >= 0.5

# Include all (with caution): no filter
# Example: Debugging why something isn't found
MATCH (a)-[e:Edge]->(b)
ORDER BY e.confidence DESC
```

### Finding Low-Confidence Issues

```python
# Find external dependencies with low confidence
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.provenance IN ['external', 'unknown_import']
      AND f.confidence_tier IN ['LOW', 'SPECULATIVE']
    RETURN f.qualified_name, f.confidence, f.file_path
    ORDER BY f.confidence
    LIMIT 20
    """
)

# Check what's causing low confidence
query_relationships(
    cypher_query="""
    MATCH (a)-[e:Edge]->(b)
    WHERE e.confidence < 0.5
    RETURN a.qualified_name, e.type, b.qualified_name, e.confidence
    ORDER BY e.confidence
    LIMIT 30
    """
)
```

**Best Practice:** Always filter by confidence in production queries to exclude uncertain relationships.

## TOOLS
- query_relationships()
- show_status()
