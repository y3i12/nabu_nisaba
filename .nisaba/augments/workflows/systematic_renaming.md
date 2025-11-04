# Workflows
## Systematic Renaming Workflow
Path: workflows/systematic_renaming

Comprehensive workflow for renaming concepts across a codebase using serena's symbolic tools.

**Use this when:** Renaming classes, variables, concepts, or doing large-scale identifier refactoring.

### Why Serena's Tools Are Superior

**Traditional approach:**
- Find/replace with regex (error-prone)
- Manual updates of each file
- Easy to miss references
- Breaks imports/references

**Serena's symbolic approach:**
- LSP-powered semantic understanding
- Automatic reference updates
- Handles imports correctly
- Type-aware renaming

---

### Complete Renaming Workflow

#### Phase 1: Discovery & Analysis

**1.1 Search for all occurrences**

```python
# Find all variations (case-insensitive, plural forms)
search_for_pattern(
    substring_pattern="[Oo]ld[Nn]ames?",  # regex for variations
    relative_path=".",  # or specific path
    context_lines_before=2,
    context_lines_after=2
)
```

**1.2 Find symbol definitions**

```python
# Locate all symbols with old name
find_symbol(
    name_path="OldClassName",
    substring_matching=True,  # catches variations
    include_body=False,
    depth=1  # include methods/attributes
)
```

**1.3 Analyze impact**

```python
# Check who references this symbol
find_referencing_symbols(
    name_path="OldClassName",
    relative_path="path/to/file.py"
)
```

**What to look for:**
- How many files are affected?
- Are there external dependencies?
- Are there string literals (won't auto-update)?
- Are there file/directory names to rename?

---

#### Phase 2: Symbolic Renaming

**2.1 Rename primary symbols**

Start with top-level symbols (classes, functions):

```python
# Rename class (updates all references automatically!)
rename_symbol(
    name_path="OldClassName",
    relative_path="path/to/file.py",
    new_name="NewClassName"
)

# Rename methods within class
rename_symbol(
    name_path="OldClassName/old_method",
    relative_path="path/to/file.py",
    new_name="new_method"
)
```

**Key insight:** Each `rename_symbol` call updates ALL references across the entire codebase via LSP. You don't need to manually update callers!

**2.2 Rename in dependency order**

For complex refactorings with dependencies:

```
1. Rename leaf symbols (no dependencies)
2. Rename intermediate symbols
3. Rename root symbols
```

This prevents temporary breakage during refactoring.

**2.3 Verify symbolic changes**

```python
# Check that old symbol is gone
find_symbol(
    name_path="OldClassName",
    substring_matching=True
)
# Should return empty or unrelated results

# Check that new symbol exists
find_symbol(
    name_path="NewClassName",
    include_body=False,
    depth=1
)
```

---

#### Phase 3: Non-Symbolic Updates

**3.1 Update string literals**

Search for strings that won't be caught by symbolic renaming:

```python
# Find string occurrences (docstrings, error messages, etc.)
search_for_pattern(
    substring_pattern='".*old_name.*"',  # or '.*old_name.*'
    relative_path=".",
    context_lines_before=1,
    context_lines_after=1
)
```

Manually update these with `replace_symbol_body` or native `Edit` tool.

**3.2 Update file/directory names**

Serena doesn't rename files - use bash:

```bash
# Rename files
mv src/old_name.py src/new_name.py

# Rename directories
mv src/old_name/ src/new_name/

# Git-aware rename (preserves history)
git mv src/old_name.py src/new_name.py
```

**3.3 Update documentation**

```python
# Find documentation files
find_file(
    file_mask="*.md",
    relative_path="."
)

# Search in docs
search_for_pattern(
    substring_pattern="old_name",
    relative_path="docs",
    restrict_search_to_code_files=False
)
```

Update manually with native `Edit` tool.

---

#### Phase 4: Verification

**4.1 Run tests**

```bash
pytest  # or relevant test command
```

**4.2 Search for stragglers**

```python
# Final sweep for any remaining old names
search_for_pattern(
    substring_pattern="[Oo]ld[_-]?[Nn]ame",
    relative_path=".",
    restrict_search_to_code_files=False
)
```

**4.3 Check LSP diagnostics**

```python
# Get IDE errors (if available)
mcp__ide__getDiagnostics()
```

**4.4 Verify API surface**

```python
# Check that public API is updated
find_symbol(
    name_path="NewClassName",
    include_body=False,
    depth=1
)
```

---

### Decision Tree: Which Tool to Use?

```
Need to rename something?
│
├─ Is it a symbol (class, function, method, variable)?
│  └─ YES → Use rename_symbol()
│     - Updates all references automatically
│     - LSP-powered, type-aware
│     - Safest option
│
├─ Is it in a string literal / comment?
│  └─ YES → Use search_for_pattern() + manual Edit
│     - Symbolic tools won't catch strings
│     - Need manual review for context
│
├─ Is it a file/directory name?
│  └─ YES → Use bash (mv or git mv)
│     - Serena doesn't handle filesystem
│     - Use git mv to preserve history
│
└─ Is it in documentation?
   └─ YES → Use search_for_pattern() + manual Edit
      - Set restrict_search_to_code_files=False
      - Update manually for context

```

---

### Common Patterns

**Pattern 1: Simple Class Rename**

```python
# 1. Check impact
find_referencing_symbols(name_path="OldClass", relative_path="file.py")

# 2. Rename
rename_symbol(name_path="OldClass", relative_path="file.py", new_name="NewClass")

# 3. Verify
find_symbol(name_path="NewClass")
```

**Pattern 2: Rename with Methods**

```python
# 1. Get class structure
find_symbol(name_path="OldClass", depth=1, include_body=False)

# 2. Rename class first
rename_symbol(name_path="OldClass", relative_path="file.py", new_name="NewClass")

# 3. Rename methods (if needed)
rename_symbol(name_path="NewClass/old_method", relative_path="file.py", new_name="new_method")
```

**Pattern 3: Concept Rename (multiple symbols)**

```python
# 1. Find all related symbols
search_for_pattern(substring_pattern="old_concept")
find_symbol(name_path="old_concept", substring_matching=True)

# 2. Rename each symbol systematically
for symbol in symbols:
    rename_symbol(name_path=symbol.name_path, relative_path=symbol.file, new_name=new_name)

# 3. Update non-symbolic occurrences
search_for_pattern(substring_pattern='".*old_concept.*"')
# Manual edit
```

---

### Pitfalls to Avoid

❌ **Don't use find/replace for symbols**
- Use `rename_symbol()` instead
- It handles references automatically

❌ **Don't rename files before symbols**
- Rename symbols first (via LSP)
- Then rename files
- Otherwise LSP loses track

❌ **Don't forget string literals**
- `rename_symbol()` won't touch strings
- Search separately with `search_for_pattern()`

❌ **Don't skip impact analysis**
- Always check `find_referencing_symbols()` first
- Understand blast radius before renaming

❌ **Don't rename external APIs lightly**
- Check if symbol is public API
- Breaking changes need deprecation strategy

---

### Checklist

Pre-refactoring:
- [ ] Search for all occurrences
- [ ] Find all symbol definitions
- [ ] Analyze impact with find_referencing_symbols
- [ ] Check if public API (breaking change?)

During refactoring:
- [ ] Rename symbols with rename_symbol() 
- [ ] Verify each rename with find_symbol()
- [ ] Update string literals manually
- [ ] Rename files/directories with git mv

Post-refactoring:
- [ ] Run tests
- [ ] Search for stragglers
- [ ] Check LSP diagnostics
- [ ] Update documentation
- [ ] Commit with clear message

---

**Time Savings:**
- Traditional: Hours of manual find/replace + debugging broken references
- With serena: Minutes of targeted symbolic renaming

**Beautiful. Elegant. Sophisticated. Sharp. Sexy.** 🖤
