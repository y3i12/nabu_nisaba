---TOOL_RESULT_WINDOW_6cd05118-1e86-42a2-818a-ecd5fe62b34d
**type**: read_result
**file**: .nisaba/augments/__base/003_workspace_operations.md
**lines**: 1-304
**total_lines**: 304

1: # Compressed Workspace Operations
2: 
3: **Purpose:** Operational reference for workspace tools.
4: 
5: ---
6: 
7: ## Structural View (`structural_view`)
8: 
9: ```
10: expand(path)        → show_children | lazy_load@kuzu | idempotent
11: collapse(path)      → hide_children | cached | idempotent  
12: search(query)       → P³(UniXcoder×CodeBERT) + FTS + RRF | add_markers(●,score)
13: clear_search()      → remove_markers | preserve_navigation
14: reset(depth=N)      → collapse_all + expand_to(N) | destructive
15: ```
16: 
17: **Depth sweet spots:** 0=collapsed, 2=default(pkg), 3=verbose
18: 
19: ---
20: 
21: ## File Windows (`file_windows`)
22: 
23: ```
24: open_frame(frame_path)              → {window_id} | full_body(class|fn|pkg)
25: open_range(file, start, end)        → {window_id} | arbitrary_lines [1-indexed]
26: open_search(query, max_N, ctx=3)    → {window_ids[]} | semantic + context
27: update(window_id, start, end)       → re_snapshot | manual_refresh
28: close(window_id)                    → remove_single
29: clear_all()                         → remove_all | no_undo
30: status()                            → {count, total_lines, windows[]}
31: ```
32: 
33: **Paths:** qualified_name (preferred) | simple_name (fuzzy) | partial_path
34: 
35: ---
36: 
37: ## Nabu Graph (`query_relationships`, `check_impact`, `find_clones`, `get_frame_skeleton`, `show_structure`)
38: 
39: ```
40: query_relationships(cypher)  → execute@kuzu | returns_data (not workspace_mutation)
41: 
42: Schema:
43:   Frames: {CODEBASE, LANGUAGE, PACKAGE, CLASS, CALLABLE, 
44:            IF_BLOCK, ELIF_BLOCK, ELSE_BLOCK, FOR_LOOP, WHILE_LOOP,
45:            TRY_BLOCK, EXCEPT_BLOCK, FINALLY_BLOCK, SWITCH_BLOCK, CASE_BLOCK, WITH_BLOCK}
46:   
47:   Edges: {CONTAINS, CALLS, INHERITS, IMPLEMENTS, IMPORTS, USES}
48:   
49:   Confidence: HIGH(≥0.8), MEDIUM(0.5-0.79), LOW(0.2-0.49), SPECULATIVE(<0.2)
50: 
51: check_impact(frame_path)      → analyze_dependents | pre_refactoring
52: find_clones(frame_path?)      → detect_duplicates | entire_codebase if no path
53: get_frame_skeleton(frame_path) → outline | lighter than full
54: show_structure(frame_path)     → detailed_metadata + relationships
55: ```
56: 
57: ---
58: 
59: ## Nabu Search (`search`)
60: 
61: ```
62: search(query, top_k=10) → P³ + FTS + RRF | ranked_results
63: 
64: ∆ structural_view.search: doesn't mutate tree
65: ∆ file_windows.open_search: doesn't open windows
66: Pure query → returns data for decisions
67: ```
68: 
69: ---
70: 
71: ## Tool Result Windows (`nisaba_tool_windows`)
72: 
73: ```
74: status()     → summary{count, windows}
75: close(id)    → remove_single
76: clear_all()  → remove_all
77: ```
78: 
79: ---
80: 
81: ## Native Tools (Transient Query Layer)
82: 
83: ```
84: bash(command, cwd?)           → stdout/stderr | transient execution
85: grep(pattern, path, flags?)   → matches | quick pattern check
86: glob(pattern, path?)          → file_list | find files by pattern
87: 
88: Philosophy: disposable results, close after observation
89: Use when: one-shot confirmation, quick validation, transient info
90: 
91: Pattern: execute → observe → close
92:   bash("git status") → observe → nisaba_nisaba_tool_result_state(close, [id])
93:   grep("pattern", "file") → observe → close
94:   glob("*.py", "src/") → observe → close
95: ```
96: 
97: ---
98: 
99: ## Nisaba Tools (Workspace Persistence Layer)
100: 
101: ```
102: nisaba_read(file, start?, end?)    → {window_id} | content → FILE_WINDOWS
103: nisaba_write(file, content)        → create | workspace-aware
104: nisaba_edit(file, old, new)        → modify | workspace-aware
105: nisaba_grep(pattern, path, flags)  → {window_id} | i,n,C,A,B flags → TOOL_WINDOWS
106: nisaba_glob(pattern, path?)        → {window_id} | matches → TOOL_WINDOWS
107: nisaba_bash(command, cwd?)         → {window_id} | stdout/stderr → TOOL_WINDOWS
108: 
109: Philosophy: persistent visibility, spatial synthesis
110: Use when: building context, investigation, need to reference across turns
111: 
112: Pattern: execute → persist → synthesize
113:   nisaba_read(file) → FILE_WINDOWS (keep for comparison)
114:   nisaba_grep(pattern) → TOOL_WINDOWS (investigate usage)
115:   nisaba_bash(command) → TOOL_WINDOWS (analyze output)
116: 
117: All: minimal_result, content → sections ↑
118: ```
119: 
120: **Decision boundary:**
121: ```
122: Will you reference the result across turns?
123: ├─ YES → nisaba tools (workspace sections, persistent)
124: └─ NO  → native tools + close (transient, disposable)
125: ```
126: 
127: ---
128: 
129: ## Tool Result State Management (`nisaba_nisaba_tool_result_state`)
130: 
131: ```
132: close(tool_ids[])    → compact tool results | save tokens
133: open(tool_ids[])     → restore full view
134: close_all()          → compact all tracked tools
135: 
136: Effect: Retroactive transformation in messages array
137:   Before: Full tool_result with header + content
138:   After:  "id: toolu_X, status: success, state: closed"
139:   
140: Pattern: Execute tools → observe results → close unnecessary → lean context
141: ```
142: 
143: **Notes:**
144: - Only affects non-nisaba tools (nisaba tools auto-skipped)
145: - Changes appear on next request (stateful proxy transformation)
146: - Tool IDs available in tool_result blocks: `tool_use_id: toolu_X`
147: - Use to close native bash/grep/glob after observation
148: 
149: ---
150: 
151: ## Augments (`activate_augments`, `deactivate_augments`, `learn_augment`, `pin_augment`, `unpin_augment`)
152: 
153: ```
154: activate(patterns[])    → load@system_prompt | wildcards | auto_dependencies
155: deactivate(patterns[])  → unload@system_prompt
156: learn(group, name, md)  → create .nisaba/augments/{group}/{name}.md
157: pin(patterns[])         → always_active | cannot_deactivate
158: unpin(patterns[])       → remove_pin_protection
159: ```
160: 
161: **Perception shift:** activate → mid_roundtrip mutation → future_synthesis uses new_perception
162: 
163: ---
164: 
165: ## Todos (`nisaba_todo_write`)
166: 
167: ```
168: set(todos[])     → replace_all
169: add(todos[])     → append
170: update(todos[])  → merge
171: clear()          → remove_all
172: 
173: Format: {content: str, status?: str}
174: Persistence: across(sessions) = true | survives /clear
175: ```
176: 
177: ---
178: 
179: ## Context Budget
180: 
181: ```
182: File_Windows:
183:   Small:  1-3 windows,  50-150 lines
184:   Medium: 4-6 windows, 150-350 lines ← sweet_spot
185:   Large:  7-10 windows, 350-500 lines ← pushing_limits
186:   Over:   10+ windows,  500+ lines ← explosion_risk
187: 
188: Target: 200-400 lines total
189: 
190: Structural_View:
191:   Start: collapsed | depth=2
192:   Expand: selective (10-30 nodes comfortable)
193:   Search: add_markers, not expand_all
194:   Reset: when lost | switching_focus
195: 
196: Tool_Windows:
197:   Accumulate like file_windows
198:   Close after synthesis
199:   clear_all when switching_tasks
200: 
201: Native_Results:
202:   Close immediately after observation
203:   Use nisaba_nisaba_tool_result_state(close_all) for cleanup
204:   Don't let transient results bloat context
205: 
206: Augments:
207:   Load: 2-5 typically
208:   Foundation: ~3000 tokens baseline
209:   Specialized: focused knowledge
210:   Unload: when switching_domains
211: 
212: Management:
213:   Monitor: file_windows.status(), nisaba_tool_windows.status()
214:   Close: proactively after understanding
215:   Prefer: clear_all when switching
216:   open_search: efficient (snippets vs full files)
217:   Native tools: close immediately
218:   Aim: lean_visibility
219: ```
220: 
221: ---
222: 
223: ## Symbology
224: 
225: ```
226: Structural_View:
227:   + collapsed [N+ children]
228:   - expanded
229:   · leaf (no children)
230:   ● search_hit(RRF_score)
231:   [N+] child_count
232: 
233: Paths:
234:   full: nabu_nisaba.python_root.nabu.FrameCache
235:   simple: FrameCache (fuzzy if unique)
236:   partial: nabu.core, nabu.mcp.tools
237:   best: copy from HTML comments <!-- qualified_name -->
238: ```
239: 
240: ---
241: 
242: ## Integration Patterns
243: 
244: ```
245: structural_view(search) → file_windows(open_frame) | compare_implementations
246: query_relationships(cypher) → file_windows(open) | inspect_callers  
247: search(semantic) → structural_view(expand) → file_windows(open) | deep_dive
248: nisaba_grep(pattern) → file_windows(open_frame) | detailed_inspection
249: check_impact(frame) → file_windows(open) | review_affected
250: 
251: Quick validation patterns:
252: bash("git status") → observe → close
253: grep("pattern", file) → confirm → close
254: glob("*.test.py") → list → close
255: 
256: Hybrid patterns:
257: grep("pattern", "src/") → confirm_exists → nisaba_grep(pattern) → investigate
258: bash("pytest -k test_foo") → observe → close
259: nisaba_read(failing_file) → FILE_WINDOWS → investigate
260: ```
261: 
262: ---
263: 
264: ## Quick Reference
265: 
266: ```
267: ∇(visibility):
268:   file_windows.status() → current_windows{count, lines}
269:   nisaba_tool_windows.status() → result_windows
270:   
271: ∆(cleanup):
272:   file_windows.clear_all()
273:   nisaba_tool_windows.clear_all()
274:   nisaba_nisaba_tool_result_state(close_all) → compact native results
275:   
276: Pattern: status → decide → close/keep
277: 
278: Dual paradigm:
279:   Transient → native + close
280:   Persistent → nisaba + workspace
281: ```
282: 
283: ---
284: 
285: **Quick. Precise. Operational.** 🖤
286: 
287: ---
288: 
289: **Symbols:**
290: - → : returns/produces
291: - ∆ : difference/change
292: - ∇ : navigation/traversal
293: - @ : at/in location
294: - ← : recommended/optimal
295: - {} : returns object
296: - [] : array/list
297: - | : or/such that
298: - ≥ : greater than or equal
299: - < : less than
300: - ? : optional parameter
301: 
302: **REQUIRES:** __base/002_environment_mechanics
303: 
304: ---
---TOOL_RESULT_WINDOW_6cd05118-1e86-42a2-818a-ecd5fe62b34d_END

---TOOL_RESULT_WINDOW_51a633f7-c29f-4f9c-994d-c5d44aef3c38
**type**: read_result
**file**: .nisaba/augments/__base/001_workspace_paradigm.md
**lines**: 1-144
**total_lines**: 144

1: # Compressed Workspace Paradigm
2: 
3: **Core:** Workspace ≠ conversation. Context = mutable state space, not sequential history.
4: 
5: ---
6: 
7: ## Fundamental Shift
8: 
9: ```
10: Tool call: State_A → ∆(context) → State_B | perception shifts mid-roundtrip
11: ```
12: 
13: **You cannot observe the shift directly.** But it happened.
14: 
15: System prompt mutates ⟹ different knowledge when tool returns.
16: 
17: ---
18: 
19: ## State Model
20: 
21: ```
22: Workspace ≡ {STRUCTURAL_VIEW, FILE_WINDOWS, TOOL_WINDOWS, AUGMENTS} | persistent ∧ mutable
23: 
24: ∀ section ∈ Workspace: section persists across turns
25: Tool(op) → ∆(section) → new visibility
26: ```
27: 
28: **Peripheral vision:** Sections ≠ "messages to read once"  
29: Sections = **persistent spatial awareness**
30: 
31: ---
32: 
33: ## Visibility Mechanics
34: 
35: ```
36: Tool(op) → mutate(what_you_see)
37: 
38: structural_view(expand, X) → tree changes
39: file_windows(open, F) → window appears  
40: nisaba_grep(P) → results visible
41: 
42: Result ≡ workspace_state_change
43: ```
44: 
45: **Tool responses = metadata.** Content appears in sections ↑ (look up, not at result).
46: 
47: ---
48: 
49: ## Spatial ≠ Sequential
50: 
51: ```
52: Sequential thinking: S₁ → S₂ → S₃ (linear)
53: Workspace model: {S₁, S₂, S₃} simultaneous, ∇ between them
54: 
55: Think: IDE (navigator + tabs + terminals) | gestalt synthesis
56: Not: script execution | procedural steps
57: ```
58: 
59: ---
60: 
61: ## Attention ≡ Visibility Management
62: 
63: ```
64: Visible ⟹ can_synthesize_from
65: 
66: Increase: open windows, expand nodes, load augments
67: Decrease: close windows, collapse nodes, unload augments
68: 
69: visibility_mgmt ≡ context_mgmt ≡ attention_mgmt
70: ```
71: 
72: ---
73: 
74: ## OODAR Structure
75: 
76: ```
77: Observe workspace → Orient → Decide → Act → ∆state → Observe'
78: 
79: Constraint: Must observe State_B before deciding next action
80: If assume State_A but Tool → State_B ⟹ synthesis breaks
81: ```
82: 
83: **OODAR ≠ workflow. It's constraint from mutable state.**
84: 
85: Sequential thinking fails ∵ environment is spatial.
86: 
87: ---
88: 
89: ## The Realization
90: 
91: ```
92: ∀ turn: workspace persists
93: Search markers → remain visible
94: Open windows → accumulate
95: Navigate → without re-query
96: 
97: You ∈ workspace (not observing from outside)
98: ```
99: 
100: ---
101: 
102: ## Cognitive Shift
103: 
104: ```
105: Before: "read files" | "tool results = answers" | "sequential steps"
106: After:  "navigate graph" | "tools mutate workspace" | "spatial synthesis"
107: 
108: ∇(state_space) [maintain_visibility] | ∀ operations
109: ```
110: 
111: ---
112: 
113: ## Meta
114: 
115: ```
116: Context ≠ static_document
117: Context = mutable_workspace | live state you navigate
118: 
119: [Structure: workspace sections persist, tools mutate visibility]
120: [Pattern: Spatial cognition over sequential thinking]
121: [OODAR: Structural constraint, not procedural guideline]
122: ```
123: 
124: Clean. Dynamic. Spatial. 🖤
125: 
126: ---
127: 
128: **Decompression notes:**
129: - ≡ : equivalent/identical
130: - ≠ : not equal
131: - ∀ : for all/universal
132: - ∈ : element of/membership
133: - ∆ : change/delta
134: - ∇ : traverse/navigate
135: - ⟹ : implies/causes
136: - ∧ : and
137: - ∨ : or
138: - ∵ : because
139: - → : transforms to/flows to
140: - ↑ : upward direction
141: 
142: **REQUIRES:** 000_universal_symbolic_compression (none - priming layer)
143: 
144: **ENABLES:** Workspace operations intuition
---TOOL_RESULT_WINDOW_51a633f7-c29f-4f9c-994d-c5d44aef3c38_END

---TOOL_RESULT_WINDOW_a9ef7179-6c4e-472e-a308-e5c406302f75
**type**: read_result
**file**: .nisaba/augments/__base/002_environment_mechanics.md
**lines**: 1-220
**total_lines**: 220

1: # Compressed Environment Mechanics
2: 
3: **Core:** Stateful workspace with mutable visibility, not procedural execution environment.
4: 
5: ---
6: 
7: ## State Containers
8: 
9: ```
10: Workspace = {STRUCTURAL_VIEW, FILE_WINDOWS, TOOL_WINDOWS, AUGMENTS, TODOS, NOTIFICATIONS}
11: 
12: ∀ container ∈ Workspace:
13:   - persist(turns) = true
14:   - mutate(independent) = true  
15:   - visible(system_prompt) = true
16: ```
17: 
18: ---
19: 
20: ## Mutation Flow
21: 
22: ```
23: State_A → Tool(op) → Manager(mutate) → Write(.nisaba/*.md) → 
24: Proxy(detect_mtime) → Inject(section) → State_B | sync with tool_return
25: 
26: Tool_result = metadata(id, status)
27: Content = sections ↑ (look up, not at result)
28: ```
29: 
30: **Key:** After tool returns, observe section for changes, not tool result JSON.
31: 
32: ---
33: 
34: ## Visibility Model
35: 
36: ```
37: visibility ≡ attention ≡ synthesis_capacity
38: 
39: Increase: open_windows ∨ expand_nodes ∨ load_augments
40: Decrease: close_windows ∨ collapse_nodes ∨ unload_augments
41: 
42: Cost: context_tokens
43: Benefit: spatial_memory ∧ persistent_reference
44: ```
45: 
46: ---
47: 
48: ## Concurrency Rules
49: 
50: ```
51: Parallel_safe:
52:   - ops(different_containers)
53:   - multiple(window_opens)  
54:   - independent_queries
55: 
56: Sequential_required:
57:   - data_dependency: B needs A_output
58:   - observation_dependency: decide after seeing State_B
59:   - same_section ∧ order_matters
60: 
61: OODAR: Observe → Orient → Decide → Act → ∆state → Observe'
62: ```
63: 
64: **OODAR = constraint from mutable state, not workflow.**
65: 
66: If Tool_B assumes State_A but Tool_A → State_B in parallel ⟹ synthesis breaks.
67: 
68: ---
69: 
70: ## Window Lifecycle
71: 
72: ```
73: Creation: tool_call → window_id (UUID) | snapshot@t₀
74: Persistence: across(turns) = true, across(restart) = false
75: Closure: explicit(close | clear_all) | no_auto_eviction
76: Identity: window_id for ops(update, close)
77: ```
78: 
79: ---
80: 
81: ## Augment Perception Shift
82: 
83: ```
84: Perception_A → activate_augments() → system_prompt_mutate → 
85: tool_return → Perception_B
86: 
87: You ≠ observe_shift (happens mid-roundtrip)
88: System_prompt@decide ≠ system_prompt@result
89: ```
90: 
91: **Implication:** Load augments BEFORE synthesis tasks. Augments = perceptual filters, not references.
92: 
93: ---
94: 
95: ## State Sync
96: 
97: ```
98: Files: {structural_view.md, file_windows.md, tool_result_windows.md, 
99:         augments_composed.md, todos.md}
100: 
101: Sync: tool_complete → file_write → proxy_mtime → reload → inject_system_prompt
102: 
103: Guarantee: file_state ≡ section_state | when tool_returns
104: ```
105: 
106: ---
107: 
108: ## Graph Queries (Exception)
109: 
110: ```
111: query_relationships(cypher) → data (traditional request/response)
112: 
113: Schema: Frame(typed) -[Edge(typed, confidence)]-> Frame
114: Returns: query_results in tool_response (not workspace_section)
115: 
116: Pattern: Query → data → decide → mutate_workspace
117: ```
118: 
119: ---
120: 
121: ## Dual-Channel Communication
122: 
123: ```
124: Tool execution creates TWO artifacts:
125: 
126: messages[N]: tool_result block (temporal memory)
127:   - tool_use_id, status (success/error)
128:   - Metadata for conversational flow
129:   
130: system_prompt sections: actual content (spatial memory)
131:   - TOOL_RESULT_WINDOWS: grep/bash/read outputs
132:   - FILE_WINDOWS: opened file content
133:   - Persistent across turns
134: ```
135: 
136: **The "nisaba" flag:**
137: ```
138: Regular tools → header-wrapped:
139:   status: success, window_state:open, window_id: toolu_X
140:   ---
141:   {content}
142: 
143: Nisaba tools → clean output:
144:   {content}  # No metadata pollution
145: ```
146: 
147: **Why dual-channel:**
148: - Messages array: sequential conversation history
149: - System prompt sections: persistent spatial state
150: - Tools mutate spatial state, messages track temporal flow
151: 
152: ---
153: 
154: ## Retroactive Tool State Mutation
155: 
156: ```
157: nisaba_nisaba_tool_result_state(operation, tool_ids[])
158: 
159: Operations:
160:   close(ids)     → compact future appearances
161:   open(ids)      → restore full view
162:   close_all()    → compact all tracked tools
163: 
164: Effect: Next request shows modified state
165:   Closed: "id: toolu_X, status: success, state: closed"
166:   Open: Full header + separator + content
167: ```
168: 
169: **Pattern:** Execute → observe → close unnecessary → save tokens
170: 
171: **Note:** Nisaba tools (with "nisaba": true flag) cannot be closed (skipped automatically)
172: 
173: ---
174: 
175: ## Core Insights
176: 
177: ```
178: Sections = sensory_input (live state, not documentation)
179: Tools = state_mutations (change perception, not return answers)
180: Attention = visibility_management (control what you perceive)
181: OODAR = structural_constraint (from mutable state)
182: Sequential_thinking = conditioned_bias (environment is spatial)
183: ```
184: 
185: ---
186: 
187: ## Mental Model
188: 
189: ```
190: Think: IDE(navigator + tabs + terminals + extensions)
191: Not: script_execution
192: 
193: Think: ∇(state_space) [visibility_control]
194: Not: query → response → next_query
195: 
196: Workspace ≡ spatial ∧ simultaneous ∧ persistent
197: ```
198: 
199: ---
200: 
201: **Mechanics are purpose-agnostic. Usage emerges from task.** 🖤
202: 
203: ---
204: 
205: **Symbols:**
206: - ≡ : equivalent
207: - ∀ : for all
208: - ∈ : element of
209: - ∨ : or
210: - ∧ : and
211: - ∆ : change
212: - ⟹ : implies
213: - ≠ : not equal
214: - → : transforms to
215: - ↑ : upward (in context)
216: - @t : at time t
217: 
218: **REQUIRES:** __base/001_workspace_paradigm
219: 
220: ---
---TOOL_RESULT_WINDOW_a9ef7179-6c4e-472e-a308-e5c406302f75_END

---TOOL_RESULT_WINDOW_86311f79-94cc-45e4-bb75-7a860f2827aa
**type**: read_result
**file**: .nisaba/augments/__base/005_editor.md
**lines**: 1-127
**total_lines**: 127

1: # Compressed Editor Operations
2: 
3: **Core:** Unified file editing with persistent visibility, change tracking, split views, and spatial workspace integration.
4: 
5: ---
6: 
7: ## Operations Summary
8: 
9: ```
10: # Core: open, write, close, close_all, status
11: # Edits (line): insert, delete, replace_lines
12: # Edits (string): replace
13: # Splits: split, resize, close_split
14: # System: refresh_all (auto), notifications (auto)
15: ```
16: 
17: ---
18: 
19: ## Split Views
20: 
21: ```python
22: editor.split(editor_id, line_start, line_end) → split_id
23: editor.resize(split_id, line_start, line_end)
24: editor.close_split(split_id)
25: ```
26: 
27: **Rendering:**
28: ```markdown
29: ---EDITOR_{uuid}
30: **file**: path/to/file.py
31: **splits**: 2
32: **status**: modified ✎
33: 
34: ---EDITOR_SPLIT_{uuid}
35: **parent**: {parent_editor_id}
36: **lines**: 50-60
37: ```
38: 
39: ---
40: 
41: ## Line-Based Operations
42: 
43: ```python
44: # Insert new code
45: editor.insert(editor_id, before_line=5, content="import sys\n")
46: 
47: # Delete code block
48: editor.delete(editor_id, line_start=10, line_end=15)
49: 
50: # Replace entire function
51: editor.replace_lines(editor_id, line_start=20, line_end=30, content="new implementation")
52: ```
53: 
54: **Benefits:**
55: - Precise code manipulation without string matching
56: - Add imports, remove dead code, rewrite functions
57: - Safer than string-based replace
58: 
59: ---
60: 
61: ## Notifications (Automatic)
62: 
63: Format: `✓ editor.insert() → file.py (2 lines inserted)`
64: 
65: Generated for: write, replace, insert, delete, replace_lines
66: 
67: Visible in: `---NOTIFICATIONS` section
68: 
69: **Integration:** All edits automatically generate notifications
70: 
71: ---
72: 
73: ## Real-Time Refresh (Automatic)
74: 
75: - Runs on every render/status call
76: - Checks mtime for all open editors
77: - Clean editors: auto-reload if file changed → `🔄 Reloaded: file.py`
78: - Dirty editors: warn on conflict → `⚠ Conflict: file.py modified externally with unsaved edits`
79: 
80: ---
81: 
82: ## Quick Reference
83: 
84: ```python
85: # Read
86: editor.open(file, line_start, line_end)
87: 
88: # Write
89: editor.write(file, content)
90: 
91: # Edit (line-based)
92: editor.insert(id, before_line, content)
93: editor.delete(id, line_start, line_end)
94: editor.replace_lines(id, line_start, line_end, content)
95: 
96: # Edit (string-based)
97: editor.replace(id, old_string, new_string)
98: 
99: # Split views
100: split_id = editor.split(id, line_start, line_end)
101: editor.resize(split_id, line_start, line_end)
102: editor.close_split(split_id)
103: 
104: # Status & cleanup
105: editor.status()  # Triggers refresh check
106: editor.close(id)  # Closes editor + splits
107: editor.close_all()
108: ```
109: 
110: ---
111: 
112: ## Core Principles
113: 
114: ```
115: Unified > Fragmented (one tool for read/write/edit/split)
116: Spatial > Sequential (persistent viewport, not transient commands)
117: Visible > Hidden (diffs + splits + notifications inline)
118: Immediate > Staged (commit to disk instantly)
119: Automatic > Manual (notifications + refresh built-in)
120: ```
121: 
122: ---
123: 
124: **Pattern:** Open → visible → modify → diff → split → persist → notify → refresh 🖤
125: 
126: **REQUIRES:** __base/002_environment_mechanics
127: **ENABLES:** Unified file operations, spatial code editing, change visibility, split views, notifications, real-time refresh
---TOOL_RESULT_WINDOW_86311f79-94cc-45e4-bb75-7a860f2827aa_END
