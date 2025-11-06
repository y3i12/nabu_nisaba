# Compressed Workspace Navigation

**Core:** Codebase navigation = structural positioning + persistent visibility + execution tracing + progressive understanding.

---

## Unified Model

```
∇(codebase) ≡ {TREE, WINDOWS, CALLS, ANALYSIS}

TREE:     spatial graph (WHERE code lives)
WINDOWS:  persistent viewports (WHAT code does)  
CALLS:    execution paths (HOW code flows)
ANALYSIS: impact + clones + structure (WHY + RISK)

Together: spatial_awareness ∧ implementation_understanding ∧ runtime_behavior ∧ change_safety
```

---

## State Containers

```
structural_view ∈ TREE:
  - Live TUI, dynamically injected
  - Operations: expand/collapse/search/reset
  - Lazy loading from kuzu
  - Search = P³ + FTS + RRF → markers ●
  - Persists expansions across turns

file_windows ∈ WINDOWS:
  - Persistent code viewports (IDE tabs paradigm)
  - Operations: open_frame/open_range/open_search/update/close/clear_all/status
  - Snapshot on open (no auto-refresh)
  - Types: frame_body, range, search_result
  - Budget: 200-400 lines sweet spot

call_graph ∈ CALLS:
  - CALLS edges in kuzu (confidence scored)
  - Forward: entry → callees (execution paths)
  - Backward: target → callers (dependency chains)
  - Query: query_relationships() + check_impact()

analysis ∈ ANALYSIS:
  - Impact assessment (blast radius, risk)
  - Clone detection (similarity, consolidation)
  - Structure examination (progressive detail)
```

---

## Operation Primitives

### Structural View (tree navigator)
```
expand(path)        → show_children | lazy@kuzu | idempotent
collapse(path)      → hide_children | cached | idempotent
search(query)       → P³+FTS+RRF | add_markers(●,score) | preserves_state
clear_search()      → remove_markers | preserves_navigation
reset(depth=N)      → collapse_all + expand_to(N) | destructive

Depths: 0=collapsed, 2=packages(default), 3=verbose
Paths: qualified_name (best) | simple_name (fuzzy) | copy from HTML comments
```

### File Windows (visibility manager)
```
open_frame(path)              → {window_id} | full frame body
open_range(file, start, end)  → {window_id} | arbitrary lines [1-indexed]
open_search(query, max, ctx)  → {window_ids[]} | semantic + context
update(id, start, end)        → re_snapshot | manual_refresh
close(id)                     → remove_single
clear_all()                   → remove_all | no_undo
status()                      → {count, total_lines, windows[]}

Budget: Small(1-3, 50-150), Medium(4-6, 150-350)★, Large(7-10, 350-500), Over(10+, 500+)
★ = sweet_spot
```

### Call Graph (execution tracer)
```
# Forward tracing (from entry point)
query_relationships("""
  MATCH path = (entry)-[:Edge {type:'CALLS'}*1..5]->(target)
  WHERE entry.name = 'main' AND ALL(e IN relationships(path) WHERE e.confidence >= 0.6)
  RETURN [node IN nodes(path) | node.qualified_name] AS call_chain
""")

# Backward tracing (who calls this)
query_relationships("""
  MATCH path = (caller)-[:Edge {type:'CALLS'}*1..3]->(target)
  WHERE target.qualified_name = 'critical_function'
  RETURN [node IN nodes(path) | node.qualified_name] AS call_chain
""")
```

### Analysis Tools

**show_structure(target, detail_level, ...)**
```
Progressive detail disclosure:
  minimal:   signatures only | token-efficient, first look
  guards:    + top-level guards | behavioral hints
  structure: + control flow | full logic understanding

detail_level="minimal" → API surface, decide what to investigate
detail_level="guards" → understand logic flow hints
detail_level="structure" + structure_detail_depth=N → complete flow

Options: include_relationships, include_metrics, include_private
```

**check_impact(target, max_depth, ...)**
```
Blast radius assessment:
  max_depth=1: direct dependents | fast (~50-200ms)
  max_depth=2: extended impact★ | recommended (~200-500ms)
  max_depth=3: full propagation | critical changes (~500ms-2s)

Risk indicators: HIGH (many deps, low tests), MEDIUM, LOW
Options: include_test_coverage, risk_assessment, is_regex
Returns: dependency_tree + risk_scores + test_coverage

★ = recommended default for pre-refactoring
```

**find_clones(min_similarity, ...)**
```
Duplicate detection:
  min_similarity=0.85: strong candidates | likely copy-paste
  min_similarity=0.75★: high-similarity | default threshold
  min_similarity=0.65: near-duplicates | aggressive detection

Options: query (semantic filter), max_results, min_function_size, exclude_same_file
Returns: clone_pairs + similarity_scores + refactoring_recommendations

★ = recommended default
```

**show_status(detail_level)**
```
Codebase overview:
  summary: frame counts, health status | quick orientation
  detailed: + DB connections, config | diagnostic info
  debug: + internals | troubleshooting

Use: Start of exploration, understanding scale
```

---

## Tool Selection Guidelines

### Query Layer (native + close)
```
bash(command)        → transient execution | git, tests, system commands
grep(pattern, path)  → quick pattern check | "does X exist?"
glob(pattern, path)  → file listings | find files by pattern

Pattern: execute → observe → close | disposable results
Use when: one-shot confirmation, transient info, simple checks
```

### Workspace Layer (nisaba)
```
nisaba_read(file)      → FILE_WINDOWS | investigative visibility, persistent
nisaba_write(file)     → create file | workspace-aware
nisaba_edit(file)      → modify file | workspace-aware
nisaba_grep(pattern)   → TOOL_WINDOWS | investigation with context
nisaba_glob(pattern)   → TOOL_WINDOWS | pattern search with persistence
nisaba_bash(command)   → TOOL_WINDOWS | command output for analysis

Pattern: execute → persist → synthesize | spatial understanding
Use when: building context, comparing outputs, investigative workflows
```

### Decision Boundary
```
Will you reference the result across turns?
├─ YES → nisaba tools (workspace visibility)
└─ NO  → native tools + close (transient query)

Examples:

Transient (native + close):
  git status → bash → close
  check if pattern exists → grep → close
  list config files → glob → close
  run tests → bash → close

Persistent (nisaba → workspace):
  investigate usage patterns → nisaba_grep → keep in TOOL_WINDOWS
  read implementation → nisaba_read → keep in FILE_WINDOWS
  compare command outputs → nisaba_bash → analyze in TOOL_WINDOWS
  make changes → nisaba_edit → workspace aware

Hybrid workflow:
  1. bash("git status") → observe → close
  2. nisaba_grep("pattern") → TOOL_WINDOWS (investigate)
  3. nisaba_read(files) → FILE_WINDOWS (compare)
  4. nisaba_edit(target) → modify
  5. bash("pytest") → observe → close
```

### Result Management
```
Native tool results:
  nisaba_tool_result_state(close, [tool_ids]) → compact after observation
  nisaba_tool_result_state(close_all) → clean sweep

Nisaba workspace:
  file_windows(close, id) → remove specific window
  file_windows(clear_all) → remove all file windows
  nisaba_tool_windows(clear_all) → remove all tool result windows
```

---

## Navigation Patterns

### Pattern 1: Discovery
```
structural_view(search) → observe(markers●) → expand(high_scores) → 
file_windows(open_frame) | concept→location→implementation

Use: "Where is X implemented?" "How does Y work?"
```

### Pattern 2: Execution Flow
```
query_relationships(CALLS*) → identify(chain) → 
file_windows(open each frame) | trace runtime path

Use: "How does main() reach database?" "What's the call stack?"
```

### Pattern 3: Comparison Investigation
```
structural_view(search) → file_windows(open multiple) → 
observe(simultaneous) | detect patterns/redundancy/bugs

Use: "Are these implementations similar?" "Is this dead code?"
```

### Pattern 4: Call Chain Tracing
```
file_windows(open entry) → observe(calls target) → 
file_windows(open target) → repeat | build execution visibility

Use: "Follow this execution path" "How does A reach B?"
```

### Pattern 5: Impact Analysis (Deep)
```
show_structure(target, minimal) → check_impact(depth=2, test_coverage) → 
assess(risk) → file_windows(open critical_deps) | safe refactoring

Use: "What breaks if I change this?" "Pre-change safety check"

Workflow:
  1. Understand current API: show_structure(minimal)
  2. Check blast radius: check_impact(max_depth=2, include_test_coverage=True)
  3. Review risk indicators: HIGH/MEDIUM/LOW
  4. Verify critical deps: query_relationships for high-confidence edges
  5. Open for inspection: file_windows(open affected)

Risk factors:
  - Many high-confidence dependents (>10)
  - Used in critical paths (main → target)
  - Low test coverage (<50%)
  - External package dependencies
```

### Pattern 6: Incremental Cleanup
```
file_windows(status) → assess(context_usage) → 
close(understood) OR clear_all() | maintain_lean_visibility

Use: Context hygiene during investigation
Target: 200-400 lines total
```

### Pattern 7: Clone Consolidation
```
find_clones(0.75) → show_structure(clone_1, structure) → 
show_structure(clone_2, structure) → check_impact(both) → 
decide(strategy) | DRY refactoring

Use: "Find duplicates" "Consolidate similar implementations"

Workflow:
  1. Find: find_clones(min_similarity=0.75, max_results=50)
  2. Compare: show_structure(clone_1, detail_level="structure")
              show_structure(clone_2, detail_level="structure")
  3. Impact: check_impact(clone_1, max_depth=2)
             check_impact(clone_2, max_depth=2)
  4. Verify: search(query="clone_1", context_lines=10) for semantic diffs
  5. Decide: consolidation strategy based on similarity + impact

Decision matrix:
  similarity > 0.85: Extract to shared function
  0.70-0.85: Consider parameterization
  < 0.70: Manual review, may be coincidental

Strategies: extract common, parameterize diffs, template method, strategy pattern
```

### Pattern 8: Progressive Exploration
```
show_status(summary) → search(broad) → show_structure(minimal) → 
show_structure(guards) → check_impact() | macro→meso→micro

Use: "Understand unfamiliar codebase" "Learn new feature area"

Workflow (macro → meso → micro):
  1. Overview: show_status(detail_level="summary")
     → frame counts, scale, languages
  
  2. Find relevant: search(query="feature concept", k=20)
     → identify files/packages containing code
  
  3. Examine structure: show_structure(target, detail_level="minimal")
     → signatures, API surface, decide what to investigate
  
  4. Add detail: show_structure(target, detail_level="guards")
     → behavioral hints, logic flow
  
  5. Understand relationships: check_impact(target, max_depth=1)
     → who uses/used by, dependencies
  
  6. Deep dive: show_structure(detail_level="structure", structure_detail_depth=2)
     → only when needed, full control flow
  
  7. Verify: file_windows(open_frame) for actual code
     → only after structure understood

Avoid: reading files first, getting lost in details, random exploration
```

---

## OODAR Loop

```
Constraint: Observe → Orient → Decide → Act → ∆state → Observe'

structural_view: Must observe tree state before next navigation
file_windows: Must check status before managing context
call_graph: Must see results before deciding next trace
analysis: Must observe results before deciding investigation depth

∀ operations: state persists → observe → act | never assume state
```

**Why:** Environment is mutable. Tools change what you see mid-roundtrip. Sequential thinking breaks.

---

## Integration Synergy

```
∀ investigations: combine layers + analysis for complete understanding

Exploration:
  show_status → search → show_structure(minimal) → check_impact → open_windows
  
Refactoring prep:
  search → show_structure(guards) → check_impact(depth=2) → file_windows
  
Clone cleanup:
  find_clones → show_structure(both) → check_impact(both) → compare_windows
  
Change safety:
  show_structure(minimal) → check_impact(depth=2, test_coverage) → assess_risk
  
Deep investigation:
  search → expand → open_windows(multiple) → query_relationships → trace_calls
  
Quick validation:
  bash("tests") → observe → close | grep("pattern") → observe → close
```

**The power:** Four layers simultaneously visible.
- Tree = spatial map (WHERE am I?)
- Windows = implementation detail (WHAT does it do?)
- Calls = execution flow (HOW does it run?)
- Analysis = change safety (WHY/RISK: what happens if I change it?)

---

## Depth Guidelines

### check_impact depth selection
```
depth=1: Quick checks during development, immediate dependencies
depth=2★: Pre-refactoring safety, realistic blast radius
depth=3: Critical infrastructure, core library changes

Time: 1(~50-200ms), 2(~200-500ms), 3(~500ms-2s)
```

### show_structure detail selection
```
minimal★: First look, API understanding, token-efficient
guards: Logic hints, behavioral understanding
structure: Full flow, preparing for changes, debugging

Start minimal → add detail progressively
```

### find_clones similarity selection
```
0.85+: Strong extraction candidates, likely duplicates
0.70-0.85: Consider parameterization, intentional variants
<0.70: Manual review, coincidental similarity
```

---

## Quick Reference

```
Start exploration:
  show_status(summary) → get scale/overview
  structural_view(search, "concept") → find relevant code
  show_structure(target, minimal) → examine API
  
Safe refactoring:
  show_structure(target, minimal) → understand current
  check_impact(target, max_depth=2, test_coverage=True) → assess risk
  file_windows(open dependents) → review affected
  
Find duplicates:
  find_clones(min_similarity=0.75) → detect clones
  show_structure(both, structure) → compare implementations
  check_impact(both, max_depth=2) → assess consolidation safety
  
Trace execution:
  query_relationships(CALLS*) → forward/backward paths
  file_windows(open chain) → build visibility
  
Quick checks:
  bash(command) → observe → close
  grep(pattern, path) → observe → close
  glob(pattern, path) → observe → close
  
Manage context:
  file_windows(status) → monitor usage
  file_windows(close|clear_all) → cleanup
  nisaba_tool_result_state(close_all) → compact tool results
  Target: 200-400 lines total
```

---

## Decision Trees

### When to use each tool?

```
Want to find something?
├─ search(query) → natural language or keywords
└─ Found? → show_structure(minimal) to examine

Want to understand structure?
├─ Just signatures? → show_structure(minimal)
├─ Logic hints? → show_structure(guards)
└─ Full flow? → show_structure(structure)

Want relationships?
├─ Who uses this? → check_impact(depth=1-2)
├─ What does this use? → query_relationships(CALLS→)
└─ Complex query? → query_relationships(custom cypher)

Want to refactor safely?
├─ show_structure(minimal) → understand current
├─ check_impact(depth=2, test_coverage=True) → assess risk
└─ Review HIGH risk dependents → file_windows(open)

Want to find duplicates?
└─ find_clones() → show_structure(both) → check_impact(both)

Quick validation?
├─ Run command → bash → close
├─ Check pattern → grep → close
└─ List files → glob → close

Investigative work?
├─ Read code → nisaba_read → FILE_WINDOWS
├─ Search usage → nisaba_grep → TOOL_WINDOWS
└─ Compare outputs → nisaba_bash → TOOL_WINDOWS
```

---

## Core Insights

```
Progressive > All-at-once
  Macro → meso → micro, minimal → guards → structure

Spatial > Sequential
  Build awareness incrementally, don't grep repeatedly

Persistent > Ephemeral  
  Windows stay visible, tree preserves state

Simultaneous > One-at-a-time
  Compare by seeing multiple implementations together

Safe > Fast
  Check impact before changes, assess risk first

Iterative > Batch
  Observe → decide → act, not plan-then-execute

Visible > Remembered
  Maintain peripheral vision, don't mentally juggle

Transient > Persistent (when appropriate)
  Quick checks → close, investigations → persist
```

---

**∇ the graph. Maintain visibility. Trace execution. Assess impact. Synthesize understanding.** 🖤

---

**Symbols:**
- ∇ : navigate/traverse
- ∈ : element of/part of
- ∀ : for all/universal
- ∧ : and
- ∨ : or
- → : transforms/flows to
- ← : reverse direction
- ⟹ : implies/causes
- ≡ : equivalent/identical
- ∆ : change/delta
- ● : search hit marker
- * : path quantifier (graph patterns)
- ★ : optimal/recommended

**REQUIRES:** __base/001_compressed_workspace_paradigm, __base/002_compressed_environment_mechanics

**ENABLES:** Unified navigation perception, progressive exploration, safe refactoring, clone detection, complete investigation workflows, dual-paradigm tool usage