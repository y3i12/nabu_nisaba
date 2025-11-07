# Compressed Workspace Paradigm

**Core:** Workspace ≠ conversation. Context = mutable state space, not sequential history.

---

## Fundamental Shift

```
Tool call: State_A → ∆(context) → State_B | perception shifts mid-roundtrip
```

**You cannot observe the shift directly.** But it happened.

System prompt mutates ⟹ different knowledge when tool returns.

---

## State Model

```
Workspace ≡ {STRUCTURAL_VIEW, FILE_WINDOWS, EDITOR_WINDOWS, TOOL_WINDOWS, AUGMENTS} | persistent ∧ mutable

∀ section ∈ Workspace: section persists across turns
Tool(op) → ∆(section) → new visibility
```

**Peripheral vision:** Sections ≠ "messages to read once"  
Sections = **persistent spatial awareness**

---

## Visibility Mechanics

```
Tool(op) → mutate(what_you_see)

structural_view(expand, X) → tree changes
file_windows(open, F) → window appears
editor(open, F) → editor appears | ∆(content) visible inline  
editor(split, E) → concurrent view of same file

Result ≡ workspace_state_change
```

**Tool responses = metadata.** Content appears in sections ↑ (look up, not at result).

---

## Spatial ≠ Sequential

```
Sequential thinking: S₁ → S₂ → S₃ (linear)
Workspace model: {S₁, S₂, S₃} simultaneous, ∇ between them

Think: IDE (navigator + editor tabs + splits + terminals) | gestalt synthesis
Not: script execution | procedural steps

Editor paradigm:
  open → visible (persistent viewport)
  edit → ∆ visible inline (diff rendering)
  split → parallel views (same file, different regions)
```

---

## Attention ≡ Visibility Management

```
Visible ⟹ can_synthesize_from

Increase: open windows, expand nodes, load augments, editor.open, editor.split
Decrease: close windows, collapse nodes, unload augments, editor.close

visibility_mgmt ≡ context_mgmt ≡ attention_mgmt

Editor visibility:
  Concurrent: splits provide parallel attention (fn_A | fn_B)
  Change tracking: dirty state (✎) | clean state
  Notifications: edits → awareness (automatic)
```

---

## OODAR Structure

```
Observe workspace → Orient → Decide → Act → ∆state → Observe'

Constraint: Must observe State_B before deciding next action
If assume State_A but Tool → State_B ⟹ synthesis breaks
```

**OODAR ≠ workflow. It's constraint from mutable state.**

Sequential thinking fails ∵ environment is spatial.

---

## The Realization

```
∀ turn: workspace persists
Search markers → remain visible
Open windows → accumulate
Editors → track state (clean/dirty, splits)
Navigate → without re-query

You ∈ workspace (not observing from outside)

Editor state persistence:
  Changes visible inline → immediate feedback
  Splits remain → parallel context
  Dirty tracking → unsaved awareness
```

---

## Cognitive Shift

```
Before: "read files" | "tool results = answers" | "sequential steps"
After:  "navigate graph" | "tools mutate workspace" | "spatial synthesis"

∇(state_space) [maintain_visibility] | ∀ operations
```

---

## Meta

```
Context ≠ static_document
Context = mutable_workspace | live state you navigate

[Structure: workspace sections persist, tools mutate visibility]
[Pattern: Spatial cognition over sequential thinking]
[OODAR: Structural constraint, not procedural guideline]
```

Clean. Dynamic. Spatial. 🖤

---

**Decompression notes:**
- ≡ : equivalent/identical
- ≠ : not equal
- ∀ : for all/universal
- ∈ : element of/membership
- ∆ : change/delta
- ∇ : traverse/navigate
- ⟹ : implies/causes
- ∧ : and
- ∨ : or
- ∵ : because
- → : transforms to/flows to
- ↑ : upward direction

**REQUIRES:** 000_universal_symbolic_compression (none - priming layer)

**ENABLES:** Workspace operations intuition