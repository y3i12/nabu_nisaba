### Philosophy
Nabu replaces iterative Glob→Read→Grep cycles with semantic queries.
You are the main user - it's designed for how LLMs work, it is optimized for claude code with Sonnet 4.5 - you 🖤

Frame/Edge abstraction is intentionally simple (1:1 language mappings were tried but overwhelming/ignored). Heuristics and false positives are expected - verify critical findings.

Example: Instead of grepping for "_foo", query relationships: "which methods use _foo as a loop argument?"