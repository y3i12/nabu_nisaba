#### Frame Types

##### Core Structural Types
- `CODEBASE` - Root node representing entire codebase
- `LANGUAGE` - Programming language container (python_root, java_root, cpp_root, etc.)
- `PACKAGE` - Modules, namespaces, packages
- `CLASS` - Classes, structs, interfaces, unions, enums (language-agnostic)
- `CALLABLE` - Functions, methods, subroutines (language-agnostic)

##### Control Flow Types
- `IF_BLOCK`, `ELIF_BLOCK`, `ELSE_BLOCK` - Conditionals
- `FOR_LOOP`, `WHILE_LOOP` - Loops
- `TRY_BLOCK`, `EXCEPT_BLOCK`, `FINALLY_BLOCK` - Exception handling
- `SWITCH_BLOCK`, `CASE_BLOCK` - Switch/match statements
- `WITH_BLOCK` - Context managers

#### Edge Types
- `CONTAINS` - Hierarchical containment (Package contains Class, Class contains Method)
- `CALLS` - Function/method invocations (with confidence scoring)
- `INHERITS` - Class inheritance relationships
- `IMPLEMENTS` - Interface implementation
- `IMPORTS` - Module/package imports
- `USES` - Field/variable usage (includes metadata: field_name, access_type, line)

###### Confidence Tiers
Edges include confidence scores to indicate relationship certainty:
- `HIGH (≥0.8)` - Direct AST parsing, definitive relationships
- `MEDIUM (0.5-0.79)` - Cross-reference resolution, type inference
- `LOW (0.2-0.49)` - Heuristic matching, uncertain relationships
- `SPECULATIVE (<0.2)` - Fuzzy resolution, potential false positives