---TOOL_RESULT_WINDOW_b3dec2d3-202f-4864-bf25-75de3eed668c
**type**: read_result
**file**: .nisaba/augments/foundation/workspace_navigation.md
**lines**: 0-0
**total_lines**: 1

<error reading file: [Errno 2] No such file or directory: '.nisaba/augments/foundation/workspace_navigation.md'>
---TOOL_RESULT_WINDOW_b3dec2d3-202f-4864-bf25-75de3eed668c_END

---TOOL_RESULT_WINDOW_1ff34c8a-610e-4d56-9425-3a273a00c346
**type**: read_result
**file**: .nisaba/augments/__base/003_compressed_workspace_operations.md
**lines**: 1-246
**total_lines**: 246

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
81: ## Nisaba Tools (Create Result Windows)
82: 
83: ```
84: nisaba_read(file, start?, end?)    → {window_id} | content → TOOL_WINDOWS
85: nisaba_grep(pattern, path, flags)  → {window_id} | i,n,C,A,B flags
86: nisaba_bash(command, cwd?)         → {window_id} | stdout/stderr → TOOL_WINDOWS  
87: nisaba_glob(pattern, path?)        → {window_id} | file_matches → TOOL_WINDOWS
88: 
89: All: minimal_result, content → sections ↑
90: ```
91: 
92: ---
93: 
94: ## Tool Result State Management (`nisaba_tool_result_state`)
95: 
96: ```
97: close(tool_ids[])    → compact tool results | save tokens
98: open(tool_ids[])     → restore full view
99: close_all()          → compact all tracked tools
100: 
101: Effect: Retroactive transformation in messages array
102:   Before: Full tool_result with header + content
103:   After:  "id: toolu_X, status: success, state: closed"
104:   
105: Pattern: Execute tools → observe results → close unnecessary → lean context
106: ```
107: 
108: **Notes:**
109: - Only affects non-nisaba tools (nisaba tools auto-skipped)
110: - Changes appear on next request (stateful proxy transformation)
111: - Tool IDs available in tool_result blocks: `tool_use_id: toolu_X`
112: 
113: ---
114: 
115: ## Augments (`activate_augments`, `deactivate_augments`, `learn_augment`, `pin_augment`, `unpin_augment`)
116: 
117: ```
118: activate(patterns[])    → load@system_prompt | wildcards | auto_dependencies
119: deactivate(patterns[])  → unload@system_prompt
120: learn(group, name, md)  → create .nisaba/augments/{group}/{name}.md
121: pin(patterns[])         → always_active | cannot_deactivate
122: unpin(patterns[])       → remove_pin_protection
123: ```
124: 
125: **Perception shift:** activate → mid_roundtrip mutation → future_synthesis uses new_perception
126: 
127: ---
128: 
129: ## Todos (`nisaba_todo_write`)
130: 
131: ```
132: set(todos[])     → replace_all
133: add(todos[])     → append
134: update(todos[])  → merge
135: clear()          → remove_all
136: 
137: Format: {content: str, status?: str}
138: Persistence: across(sessions) = true | survives /clear
139: ```
140: 
141: ---
142: 
143: ## Context Budget
144: 
145: ```
146: File_Windows:
147:   Small:  1-3 windows,  50-150 lines
148:   Medium: 4-6 windows, 150-350 lines ← sweet_spot
149:   Large:  7-10 windows, 350-500 lines ← pushing_limits
150:   Over:   10+ windows,  500+ lines ← explosion_risk
151: 
152: Target: 200-400 lines total
153: 
154: Structural_View:
155:   Start: collapsed | depth=2
156:   Expand: selective (10-30 nodes comfortable)
157:   Search: add_markers, not expand_all
158:   Reset: when lost | switching_focus
159: 
160: Tool_Windows:
161:   Accumulate like file_windows
162:   Close after synthesis
163:   clear_all when switching_tasks
164: 
165: Augments:
166:   Load: 2-5 typically
167:   Foundation: ~3000 tokens baseline
168:   Specialized: focused knowledge
169:   Unload: when switching_domains
170: 
171: Management:
172:   Monitor: file_windows.status(), nisaba_tool_windows.status()
173:   Close: proactively after understanding
174:   Prefer: clear_all when switching
175:   open_search: efficient (snippets vs full files)
176:   Aim: lean_visibility
177: ```
178: 
179: ---
180: 
181: ## Symbology
182: 
183: ```
184: Structural_View:
185:   + collapsed [N+ children]
186:   - expanded
187:   · leaf (no children)
188:   ● search_hit(RRF_score)
189:   [N+] child_count
190: 
191: Paths:
192:   full: nabu_nisaba.python_root.nabu.FrameCache
193:   simple: FrameCache (fuzzy if unique)
194:   partial: nabu.core, nabu.mcp.tools
195:   best: copy from HTML comments <!-- qualified_name -->
196: ```
197: 
198: ---
199: 
200: ## Integration Patterns
201: 
202: ```
203: structural_view(search) → file_windows(open_frame) | compare_implementations
204: query_relationships(cypher) → file_windows(open) | inspect_callers  
205: search(semantic) → structural_view(expand) → file_windows(open) | deep_dive
206: nisaba_grep(pattern) → file_windows(open_frame) | detailed_inspection
207: check_impact(frame) → file_windows(open) | review_affected
208: ```
209: 
210: ---
211: 
212: ## Quick Reference
213: 
214: ```
215: ∇(visibility):
216:   file_windows.status() → current_windows{count, lines}
217:   nisaba_tool_windows.status() → result_windows
218:   
219: ∆(cleanup):
220:   file_windows.clear_all()
221:   nisaba_tool_windows.clear_all()
222:   
223: Pattern: status → decide → close/keep
224: ```
225: 
226: ---
227: 
228: **Quick. Precise. Operational.** 🖤
229: 
230: ---
231: 
232: **Symbols:**
233: - → : returns/produces
234: - ∆ : difference/change
235: - ∇ : navigation/traversal
236: - @ : at/in location
237: - ← : recommended/optimal
238: - {} : returns object
239: - [] : array/list
240: - | : or/such that
241: - ≥ : greater than or equal
242: - < : less than
243: 
244: **REQUIRES:** __base/002_compressed_environment_mechanics
245: 
246: ---
---TOOL_RESULT_WINDOW_1ff34c8a-610e-4d56-9425-3a273a00c346_END
