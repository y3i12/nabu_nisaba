# Security
## Injection Detection
Path: security/injection_detection

Finding SQL injection, command injection, and insecure deserialization vulnerabilities.

### SQL Injection Risks

Find string concatenation in SQL contexts:

```python
# Search for dangerous SQL patterns
search(query="execute.*+.*query.*format", k=30, context_lines=5)

# Find database execute calls
search(
    query="execute|executemany|cursor",
    is_regex_input=True,
    frame_type_filter="CALLABLE",
    k=40,
    context_lines=7
)

# Look for format string SQL
search(
    query=".format\\(|%.*%|f['\"].*SELECT",
    is_regex_input=True,
    k=30,
    context_lines=5
)
```

**High-Risk Patterns:**
- `"SELECT * FROM users WHERE id = " + user_id`
- `f"DELETE FROM {table} WHERE id = {id}"`
- `query.format(table=user_input)`
- `.execute(raw_string % values)`

**Safe Patterns (verify these are used):**
- Parameterized queries: `.execute(query, (param1, param2))`
- ORM usage: `Model.objects.filter(id=user_id)`
- Query builders: `query.where('id', '=', ?).bind(user_id)`

### Command Injection Risks

Find shell command execution with user input:

```python
# Search for shell command execution
search(query="os.system subprocess shell=True exec eval", k=30)

# Find specific risky patterns
search(
    query="subprocess.*shell=True",
    is_regex_input=True,
    k=20,
    context_lines=5
)

# os.system usage
search(
    query="os\\.system\\(",
    is_regex_input=True,
    k=20,
    context_lines=5
)
```

**High-Risk Patterns:**
- `os.system(user_input)`
- `subprocess.call(cmd, shell=True)`
- `exec(user_data)`
- `eval(request.params)`

**Safe Alternatives:**
- `subprocess.run(['command', arg1, arg2], shell=False)`
- Use argument lists instead of shell strings
- Whitelist allowed commands
- Sanitize and validate all inputs

### Insecure Deserialization

Find pickle, eval, exec usage:

```python
# Search for dangerous deserialization
search(query="pickle.loads eval exec compile", k=30, context_lines=7)

# Specific patterns
search(
    query="pickle\\.loads|yaml\\.load\\(|eval\\(|exec\\(",
    is_regex_input=True,
    k=30,
    context_lines=5
)
```

**High-Risk Patterns:**
- `pickle.loads(untrusted_data)`
- `yaml.load(user_input)` (without SafeLoader)
- `eval(request.body)`
- `exec(user_provided_code)`

**Safe Alternatives:**
- `json.loads()` for data
- `yaml.safe_load()` instead of `yaml.load()`
- `ast.literal_eval()` for Python literals only
- Never deserialize untrusted data

### Verification Workflow

```python
# Step 1: Find potentially vulnerable functions
search(query="execute query sql", k=30)

# Step 2: Examine structure to see if user input flows in
show_structure(
    target="vulnerable_function",
    detail_level="structure",
    structure_detail_depth=2
)

# Step 3: Trace back to see where data comes from
query_relationships(
    cypher_query="""
    MATCH (source:Frame)-[:Edge {type: 'CALLS'}*1..3]->(target:Frame)
    WHERE target.qualified_name = 'vulnerable_function'
    RETURN source.qualified_name, source.file_path
    LIMIT 30
    """
)
```

### Mitigation Checklist

For each vulnerability found:

1. **Identify input source** - Where does untrusted data come from?
2. **Trace data flow** - How does it reach the vulnerable function?
3. **Check validation** - Is input validated/sanitized?
4. **Verify escaping** - Is data properly escaped?
5. **Prefer safe APIs** - Can we use parameterized queries?

**Priority Levels:**
- **Critical:** Direct user input to exec/eval/system
- **High:** SQL injection in authentication/authorization
- **Medium:** Command injection in admin features
- **Low:** Well-validated input to safe APIs

## TOOLS
- search()
- show_structure()
