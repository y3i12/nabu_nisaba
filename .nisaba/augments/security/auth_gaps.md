# Security
## Authentication & Authorization Gaps
Path: security/auth_gaps

Finding endpoints and functions missing authentication or authorization checks.

### Find Public Endpoints

```python
# Find API endpoints and routes
search(query="@app.route @api def endpoint", k=50, context_lines=7)

# Find Flask/Django routes
search(
    query="@app\\.(route|get|post|put|delete)",
    is_regex_input=True,
    k=50,
    context_lines=7
)

# Find FastAPI endpoints
search(
    query="@router\\.(get|post|put|delete)",
    is_regex_input=True,
    k=50,
    context_lines=7
)
```

### Find Endpoints Without Auth Checks

```python
# Find endpoints that don't call auth functions
query_relationships(
    cypher_query="""
    MATCH (endpoint:Frame)
    WHERE (endpoint.name CONTAINS 'api_'
           OR endpoint.name CONTAINS 'endpoint'
           OR endpoint.name CONTAINS 'route')
      AND NOT EXISTS {
        MATCH (endpoint)-[:Edge {type: 'CALLS'}*1..2]->(auth:Frame)
        WHERE auth.name CONTAINS 'auth'
           OR auth.name CONTAINS 'check'
           OR auth.name CONTAINS 'verify'
           OR auth.name CONTAINS 'require'
      }
      AND endpoint.provenance = 'local'
    RETURN endpoint.qualified_name, endpoint.file_path
    LIMIT 50
    """
)
```

### Trace Authentication Flow

For suspected unprotected endpoints, trace the call chain:

```python
# Check what an endpoint calls
query_relationships(
    cypher_query="""
    MATCH (endpoint:Frame)-[:Edge {type: 'CALLS'}*1..3]->(called:Frame)
    WHERE endpoint.qualified_name = 'api_endpoint_function'
      AND called.name CONTAINS 'auth'
    RETURN called.qualified_name, called.name
    LIMIT 20
    """
)

# Or check structure
show_structure(
    target="api_endpoint_function",
    detail_level="guards",
    include_relationships=True
)
```

### Find Auth Pattern Usage

Identify authentication patterns used in the codebase:

```python
# Find decorator-based auth
search(
    query="@require_auth|@login_required|@authenticated",
    is_regex_input=True,
    k=30
)

# Find middleware auth
search(query="authenticate middleware check_auth", k=30)

# Find manual auth checks
search(
    query="if.*auth|if.*token|if.*session",
    is_regex_input=True,
    k=40,
    context_lines=5
)
```

### Compare Protected vs Unprotected

```python
# Step 1: Find endpoints with auth decorators
search(query="@require_auth", k=50)

# Step 2: Find endpoints without auth decorators
search(
    query="@app\\.route.*\\ndef [^_]",
    is_regex_input=True,
    k=50
)

# Step 3: Compare lists to find gaps
```

### Authorization Checks (Role-Based)

Find functions that should check roles but might not:

```python
# Search for admin/role checks
search(query="is_admin check_role has_permission", k=30)

# Find functions with "admin" in name but no role check
query_relationships(
    cypher_query="""
    MATCH (f:Frame)
    WHERE f.name CONTAINS 'admin'
      AND f.frame_type = 'CALLABLE'
      AND NOT EXISTS {
        MATCH (f)-[:Edge {type: 'CALLS'}*1..2]->(check:Frame)
        WHERE check.name CONTAINS 'role'
           OR check.name CONTAINS 'permission'
           OR check.name CONTAINS 'admin'
      }
    RETURN f.qualified_name, f.file_path
    LIMIT 30
    """
)
```

### Common Auth Bypass Patterns

Look for these anti-patterns:

```python
# Commented-out auth checks (dangerous!)
search(query="# @require_auth|#.*authenticate", k=20)

# Auth checks in wrong order
search(query="if.*not.*auth.*return|if.*auth.*pass", k=20)
```

### Auth Gap Analysis Workflow

```python
# Step 1: Identify auth patterns
search(query="auth authenticate login check_user", k=30)

# Step 2: Find all endpoints
search(query="@app @router @api endpoint", k=50)

# Step 3: For each endpoint, check auth flow
show_structure(target="endpoint_name", detail_level="guards")

# Step 4: Trace calls to verify auth
query_relationships(
    cypher_query="""
    MATCH (endpoint)-[:Edge {type: 'CALLS'}*1..2]->(auth)
    WHERE endpoint.qualified_name = 'endpoint_name'
    RETURN auth.qualified_name
    """
)
```

### Mitigation Strategies

For endpoints missing auth:

1. **Centralized auth** - Use decorators or middleware
2. **Default deny** - Require explicit public endpoint marking
3. **Auth before logic** - Check auth first, then process request
4. **Role-based access** - Check not just "logged in" but "authorized"
5. **Test coverage** - Verify auth is enforced in tests

**Risk Levels:**
- **Critical:** Write operations without auth (create/update/delete)
- **High:** Read sensitive data without auth
- **Medium:** Admin functions without role checks
- **Low:** Public endpoints that should be public

## TOOLS
- search()
- query_relationships()

## REQUIRES
- foundation/call_graph_analysis
