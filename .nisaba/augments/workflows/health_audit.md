# Workflows
## Codebase Health Audit
Path: workflows/health_audit

Complete codebase health audit workflow - systematic review of dead code, complexity, tests, security, architecture, and duplication.

This is a comprehensive workflow for periodic codebase health assessment.

### Workflow Overview

**Goal:** Systematic assessment of codebase quality across all dimensions.

**Duration:** 30-60 minutes for medium codebases

**Output:** Prioritized list of issues and recommendations

### Step 1: Overview & Baseline

Get high-level metrics:

```python
# Database health and frame counts
show_status(detail_level="detailed")

# Shows:
# - Total frames by type (CALLABLE, CLASS, PACKAGE)
# - Confidence distribution
# - Database health
```

**Record baseline metrics:**
- Total classes, functions
- Confidence distribution
- Database size

### Step 2: Dead Code Detection

Find unused code:

```python
# Unreferenced callables
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.frame_type = 'CALLABLE'
      AND NOT EXISTS {
        MATCH ()-[:Edge {type: 'CALLS'}]->(f)
      }
      AND f.provenance = 'local'
    RETURN f.qualified_name, f.file_path
    LIMIT 100
    """
)

# Unreferenced classes
query_relationships(
    cypher_query="""
    MATCH (c:Frame)
    WHERE c.frame_type = 'CLASS'
      AND NOT EXISTS {
        MATCH ()-[e:Edge]->(c)
        WHERE e.type IN ['INHERITS', 'IMPLEMENTS', 'CALLS']
      }
      AND c.provenance = 'local'
    RETURN c.qualified_name, c.file_path
    LIMIT 50
    """
)
```

**Deliverable:** List of dead code candidates for removal

### Step 3: Complexity Hotspots

Find overly complex code:

```python
# Functions with high control flow complexity
query_relationships(
    cypher_query="""
    MATCH (f:Frame)-[:Edge {type: 'CONTAINS'}]->(cf:Frame)
    WHERE f.frame_type = 'CALLABLE'
      AND cf.frame_type IN ['IF_BLOCK', 'FOR_LOOP', 'WHILE_LOOP', 'TRY_BLOCK']
    WITH f.qualified_name AS func, f.file_path AS path, count(cf) AS complexity
    WHERE complexity >= 5
    RETURN func, path, complexity
    ORDER BY complexity DESC
    LIMIT 30
    """
)

# Deep nesting
query_relationships(
    cypher_query="""
    MATCH path = (f:Frame)-[:Edge {type: 'CONTAINS'}*3..8]->(nested:Frame)
    WHERE f.frame_type = 'CALLABLE'
    WITH f.qualified_name AS func, length(path) AS nesting_depth
    RETURN func, nesting_depth
    ORDER BY nesting_depth DESC
    LIMIT 20
    """
)
```

**Deliverable:** Priority list for refactoring

### Step 4: Test Coverage Analysis

Assess test quality:

```python
# Test-to-code ratio
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

# Untested code
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.frame_type = 'CALLABLE'
      AND NOT f.file_path CONTAINS 'test'
      AND NOT EXISTS {
        MATCH (test:Frame)-[:Edge {type: 'CALLS'}]->(f)
        WHERE test.file_path CONTAINS 'test'
      }
    RETURN count(f) AS untested_count
    """
)
```

**Deliverable:** Test coverage gaps

### Step 5: Security Issues

Find potential vulnerabilities:

```python
# SQL injection risks
search(query="execute.*+.*query|format.*sql", k=30)

# Command injection
search(query="os.system|subprocess.*shell=True", k=30)

# Hardcoded secrets
search(
    query="password|secret|api_key.*=.*['\"]",
    is_regex_input=True,
    k=30
)
```

**Deliverable:** Security issues by priority

### Step 6: Architectural Violations

Check layer boundaries:

```python
# Cross-layer violations (adjust paths for your architecture)
query_relationships(
    cypher_query="""
    MATCH (ui:Frame)-[e:Edge {type: 'CALLS'}]->(data:Frame)
    WHERE ui.file_path CONTAINS '/ui/'
      AND data.file_path CONTAINS '/data/'
      AND e.confidence >= 0.6
    RETURN ui.qualified_name, data.qualified_name
    LIMIT 50
    """
)

# Circular dependencies
query_relationships(
    cypher_query="""
    MATCH (a:Frame)-[:Edge {type: 'IMPORTS'}]->(b:Frame)-[:Edge {type: 'IMPORTS'}]->(a)
    WHERE a.frame_type = 'PACKAGE' AND b.frame_type = 'PACKAGE'
    RETURN a.qualified_name, b.qualified_name
    LIMIT 50
    """
)
```

**Deliverable:** Architectural violations list

### Step 7: Code Duplication

Find duplicated code:

```python
# Global clone detection
find_clones(
    min_similarity=0.75,
    max_results=100,
    exclude_same_file=True
)
```

**Deliverable:** Clone pairs for consolidation

### Health Score Calculation

**Scoring rubric (0-100):**

- **Dead Code (20 points):**
  - 0 dead code = 20 points
  - >10% dead code = 0 points

- **Complexity (20 points):**
  - <5% complex functions = 20 points
  - >20% complex = 0 points

- **Test Coverage (25 points):**
  - Test ratio >1.0 = 25 points
  - Test ratio <0.3 = 0 points

- **Security (15 points):**
  - 0 issues = 15 points
  - >5 critical = 0 points

- **Architecture (10 points):**
  - No violations = 10 points
  - >10 violations = 0 points

- **Duplication (10 points):**
  - <5% duplication = 10 points
  - >20% = 0 points

### Report Template

```markdown
# Codebase Health Audit - [Date]

## Executive Summary
- Health Score: X/100
- Critical Issues: X
- High Priority: X
- Medium Priority: X

## 1. Dead Code
- X unreferenced functions
- X unreferenced classes
**Action:** Review and remove

## 2. Complexity
- X functions with complexity >5
- X functions with deep nesting
**Action:** Refactor top 10

## 3. Test Coverage
- Test ratio: X.XX
- X untested functions
**Action:** Add tests for public APIs

## 4. Security
- X SQL injection risks
- X command injection risks
- X hardcoded secrets
**Action:** Fix critical issues immediately

## 5. Architecture
- X layer violations
- X circular dependencies
**Action:** Enforce boundaries

## 6. Duplication
- X clone pairs (>75% similar)
**Action:** Consolidate top duplicates

## Recommendations
1. [Highest priority action]
2. [Second priority]
3. [Third priority]
```

## TOOLS
- show_status()
- query_relationships()
- find_clones()
- check_impact()

## REQUIRES
- code_quality/dead_code_detection
- code_quality/complexity_hotspots
- testing/test_coverage_analysis
