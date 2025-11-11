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
Workspace ≡ {STRUCTURAL_VIEW, RESULTS, AUGMENTS, TODOS, NOTIFICATIONS} | persistent ∧ mutable

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
bash/grep/read → output appears in RESULTS
result.hide(id) → output removed from RESULTS
result.show(id) → output restored to RESULTS

Result ≡ workspace_state_change
```

**Tool responses = metadata in messages.** Content appears in RESULTS section (workspace, not tool result block).

---

## Spatial ≠ Sequential

```
Sequential thinking: S₁ → S₂ → S₃ (linear)
Workspace model: {S₁, S₂, S₃} simultaneous, ∇ between them

Think: IDE (navigator + terminal outputs + tool results) | gestalt synthesis
Not: script execution | procedural steps

Tool output paradigm:
  execute → visible in RESULTS (persistent spatial memory)
  hide → removed from RESULTS (save tokens, keep metadata)
  show → restored to RESULTS (regain visibility)
  Composable primitives (Read/Edit/Write) over monolithic tool
```

---

## Attention ≡ Visibility Management

```
Visible ⟹ can_synthesize_from

Increase: expand nodes, load augments, execute tools (→ RESULTS)
Decrease: hide tool results, collapse nodes, unload augments

visibility_mgmt ≡ context_mgmt ≡ attention_mgmt

RESULTS visibility:
  show: tool output visible in workspace (spatial persistence)
  hide: tool output removed (metadata remains in messages)
  collapse_all: bulk cleanup, lean context
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
Tool results → accumulate in RESULTS
Visibility → controlled via hide/show
Navigate → without re-query

You ∈ workspace (not observing from outside)

RESULTS persistence:
  Tool outputs wrapped: ---TOOL_USE(id)...---TOOL_USE_END(id)
  Spatial memory: content in workspace, not messages
  Token control: hide to remove, show to restore
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
- → : transforms to/flows through messages

**REQUIRES:** 000_universal_symbolic_compression (none - priming layer)

**ENABLES:** Workspace operations intuition
