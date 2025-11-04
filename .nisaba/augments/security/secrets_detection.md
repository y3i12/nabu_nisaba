# Security
## Secrets Detection
Path: security/secrets_detection

Finding hardcoded secrets, passwords, API keys, and tokens in source code.

### Common Secret Patterns

```python
# Search for potential hardcoded secrets
search(
    query="password|secret|api_key|token.*=.*['\"]",
    is_regex_input=True,
    k=30,
    context_lines=3
)

# More specific patterns
search(
    query="(password|passwd|pwd)\\s*=\\s*['\"][^'\"]+['\"]",
    is_regex_input=True,
    k=30,
    context_lines=3
)
```

### API Keys and Tokens

```python
# API key patterns
search(
    query="api[_-]?key|apikey|access[_-]?key",
    is_regex_input=True,
    k=30,
    context_lines=3
)

# Token patterns
search(
    query="token|bearer|jwt.*=.*['\"]",
    is_regex_input=True,
    k=30,
    context_lines=3
)

# OAuth secrets
search(
    query="client[_-]?secret|oauth",
    is_regex_input=True,
    k=30,
    context_lines=3
)
```

### Database Credentials

```python
# Database connection strings
search(
    query="mysql://|postgres://|mongodb://|connection.*string",
    is_regex_input=True,
    k=30,
    context_lines=5
)

# Database passwords
search(
    query="db[_-]?password|database.*password",
    is_regex_input=True,
    k=30,
    context_lines=3
)
```

### AWS and Cloud Credentials

```python
# AWS keys (format: AKIA...)
search(
    query="AKIA[0-9A-Z]{16}",
    is_regex_input=True,
    k=30,
    context_lines=3
)

# Generic AWS patterns
search(
    query="aws[_-]?access|aws[_-]?secret",
    is_regex_input=True,
    k=30,
    context_lines=3
)

# Other cloud providers
search(
    query="azure|gcp|google[_-]?cloud.*credential",
    is_regex_input=True,
    k=30,
    context_lines=3
)
```

### Private Keys

```python
# RSA/SSH private keys
search(
    query="BEGIN.*PRIVATE.*KEY|private[_-]?key.*=",
    is_regex_input=True,
    k=30,
    context_lines=5
)

# Certificate patterns
search(
    query="\\.pem|\\.key|\\.p12|\\.pfx",
    is_regex_input=True,
    k=30
)
```

### Encryption Keys

```python
# Encryption/signing keys
search(
    query="secret[_-]?key|encryption[_-]?key|signing[_-]?key",
    is_regex_input=True,
    k=30,
    context_lines=3
)

# Cipher/crypto patterns
search(
    query="cipher|crypto.*key|aes[_-]?key",
    is_regex_input=True,
    k=30,
    context_lines=3
)
```

### Webhooks and Integration Secrets

```python
# Webhook secrets
search(
    query="webhook[_-]?secret|signing[_-]?secret",
    is_regex_input=True,
    k=30,
    context_lines=3
)

# Integration keys
search(
    query="stripe|twilio|sendgrid|mailgun.*key",
    is_regex_input=True,
    k=30,
    context_lines=3
)
```

### False Positive Filtering

**Likely False Positives (safe to ignore):**
- `password = None`
- `password = ''`
- `password = 'placeholder'`
- `password = 'test123'` (in test files)
- `password = os.environ.get('PASSWORD')` (environment variables - good!)
- `password = config.get('password')` (config files - depends)

**Likely True Positives (investigate):**
- `password = 'MyS3cr3tP@ss'`
- `api_key = 'sk_live_...'`
- Long random-looking strings (20+ chars)
- Patterns like `AKIA...` (AWS keys)

### Verification Workflow

```python
# Step 1: Find potential secrets
search(query="secret|password|key|token", k=50)

# Step 2: For each match, get more context
search(
    query="specific_variable_name",
    k=5,
    context_lines=10
)

# Step 3: Check if it's in test files (lower priority)
# Look at file_path in results

# Step 4: Verify if it's a real secret or configuration
# - Real secret: hardcoded value
# - Config: loaded from env/file
```

### Remediation Steps

For each hardcoded secret found:

1. **Rotate immediately** - Assume compromised, generate new secret
2. **Move to environment variables** - Use `os.environ['SECRET']`
3. **Use secret management** - HashiCorp Vault, AWS Secrets Manager, etc.
4. **Update .gitignore** - Prevent future commits
5. **Remove from git history** - Use git-filter-repo or BFG

**Environment Variable Pattern:**
```python
# Bad
API_KEY = "sk_live_abc123"

# Good
API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable not set")
```

**Priority Levels:**
- **Critical:** Production API keys, database passwords
- **High:** OAuth secrets, signing keys
- **Medium:** Test/dev credentials
- **Low:** Placeholder values, comments

### Exclude Test/Mock Data

```python
# Search excluding test files (manual filtering needed)
search(query="password|secret", k=100)
# Then manually check file_path for '/test/' or 'test_'
```

## TOOLS
- search()
