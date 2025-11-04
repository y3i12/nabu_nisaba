### IMPORTANT BACKGROUND
You are working on `nabu`, which is a code analysis framework prototype that bridges the gap between raw AST parsing and high-level semantic understanding, making codebases queryable as structured graphs (they can be cyclic). It is intended to aid LLM agents, with a better way to operate with code analysis, replacing sequeintial executions of [`Glob`, `Read`, `Grep`] (in any combination, order and number of occurrences) with semantical queries, working as a project-wide "outline on steroids" of an IDE, or a semantic index mapping the code. As it is a prototype, the performance, full tests, migrations, fallbacks and such are considered unimportant. And akways remember: You (Claude) are the main user.

`nisaba` is the sister project - a small mcp framework that was inspired by `serena` mcp and is the base of `nabu` mcp.
`nisaba` also works as the proxy that is juggling the requests and managing context injection.

`nabu` mcp holds a kuzu db instance (cypher queries) with structural data that represents the current state of code in `$CLAUDE_PROJECT_DIR`; `nabu` is responsible for parsing the files with tree-sitter, creates a stack frame and does some dependency resolution to create the graph and loading kuzu db; this instance contain data about `$CLAUDE_PROJECT_DIR`.

#### End goals of nabu
Having a queriable representation of the code in kuzu. This representation should ideally be abstract without compromising **too much** what can be extracted as information from the database. The representation must follow common language concepts, as packages/namespaces, classes/structs, methods/functions/subroutines/lambdas, scopes, control statements [if/elif/else, try/catch/finally, switch/match/case, while, for, ...] and variables (focusing on the relationship between entities/callables). A certain degree of heuristics is expected or even wanted. A certain amount of false-positives are expected but unwanted.

This representation at its "dream" condition should be able to map code with a good amount of semantic qualities, leaving the details to be understood by the agent. Imagine that it would be able to easily deduce with a simple query "class Foo contains variable _foo that is used in Foo.buzz() inside a loop, as an argument for Baz.biz()".

##### Purpose and Reasoning behind it
Purpose: enable LLM agents to query the codebase for understanding and easy access to information.

Reasoning:
1. By having the agent to quickly understand the code abstraction and data flow, would enable the agent to in very few queries to have excellent context about the code, giving additional directions for detailed investigation (proper reading code) - this would make code changes more assertive.
2. "ideally be abstract"
    - In previous attempts it was tried to have detailed mappings of the code with 1:1 entities (as packages, namespaces, classes, structs, methods, functions, variables, globals, etc.) in the database and the edges correlating them - it was overwheming and most part of the entities and relationships were ignored
    - By having Frames and Edges it is easy to ennumerate them and understand how to make relationships filtering by their type - the schema is self explanatory
    - the abstract gives freedom when "A certain degree of heuristics is expected or even wanted".
3. "without compromising **too much**"
    - details of the code can be obtained from content
    - different "zoom" levels can be obtaining by retrieveng the content from different frames
    - use of common denominators of different languages to make all code "feel" the same as from an study/analysis point of view
    - has call tree
    - has decision tree
    - has exception tree
    - has entities
    - has semantic entity relationship (inherits, extends, templates, contains, uses)
    - has variables (constants and values that are global or part of another entity - scoped variables might be too much?)
    - "A certain amount of false-positives are expected but unwanted"