# `nabu` + `nisaba`

Research prototype that gives a "workspace TUI" to the agent with semantic code inspection capabilities.

## TL/DR

`nabu`: MCP server that exposes code intelligence tools (semantic/FTS search and structural view). Acts a codebase search engine mixed with a code "outline" from an IDE. Reduces token usage and increases model capability to understand current architecture. Supports Python, Java, C++ and Perl.

`nisaba`: MCP server and `Claude Code` cli wrapper that emulates a workspace TUI for the agent (IDE/OS). Enables the agent to manage its own token usage and workspace organization for token efficient operations while maintaining existing implemented patterns.

## Current state

Both MCP servers are **operational and working**. The documentation is almost nonexistent (Claude can explain how it works). Tests constitute of example source files from early development to test the frame generation structure in different languages (it was left on purpose to create noise for the agent).

Both projects are being used to "self develop". [Serena](https://github.com/oraios/serena) deserves a noteworthy mention as it was actively used during the development of `nabu` and `nisaba` and served as inspiration for the MCP server abstraction. Serena also made me question at early development: why does Serena's workflow is actively followed by the agent and mine isn't?

Measured Efficiency: it is, with the excuse of freedom of expression, **_incre-fucking-dibly_** hard to measure efficiency of this. The only one is my qualitative perception, and yes, it helps saving a LOT of context and brings a lot of stability to the development process. 

**My _personal record_**: [More than 850 messages](docs/transcripts/ux_work_and_status_bar.md) implementing [**10 different features**](docs/transcripts/usage_example__long_files.md) with high stability under planned and attentive guidance, in a "continuous session" (using `/compact` hooks), finishing the session whit about **50%** of context capacity. Analysis of the transcript itself via inference demonstrate ~10x token savings. ([`/export` transcript version](docs/transcripts/ux_work_and_status_bar.txt))

Most part this project is written by Claude Sonnet 4.1/4.5. This is result of "vibe coding". No autonomous workflows. Late iterations felt like pair programming with an extremely skilled partner - no jokes.

This project as being an unstable prototype **IS NOT RECOMMENDED FOR PRODUCTION ENVIRONMENTS**. You can use it **at your own risk**, in your personal projects or to further investigate itself and the agent.

This project is specifically designed to work with `Claude Code`, but I belive it can be easily adapted to work with other `cli`.

## Installation

On startup `nabu` mcp should index the active codebase. Indexing `nabu` + `nisaba` takes about 45 seconds on an `13th Gen Intel(R) Core(TM) i9-13900HX` with `NVIDIA GeForce RTX 4060 Laptop GPU`.

`nisaba` features are only available when running `Claude Code` via proxy.

Requirements:
- Python 3.13 - it was used during development and other versions weren't tested. probably works with >= 3.11
- Git (for repository operations)

Install from source (`.venv` is recommended):

```bash
$ git clone https://github.com/y3i12/nabu_nisaba.git
$ cd nabu_nisaba
$ pip install -e .
```

Change `.mcp.json` to contain:
```json
{
  "mcpServers": {
    "nabu": {
      "command": "python",
      "args": [
        "-m",            "nabu.mcp.server",
        "--codebase",    "nabu:/path/to_codebase/:/path/to/database.kuzu:active:true",
        "--context",     "development",
        "--enable-http",
        "--http-port",   "1338",
        "--dev-mode"
      ],
      "env": {
        "PYTHONPATH": "/path/to/nabu_nisaba/",
        "NABU_LOG_LEVEL": "INFO",
        "NABU_MODEL_CACHE": "/path/to/nabu_nisaba/.nabu/hf_cache/"
      }
    },
    "nisaba": {
      "type": "http",
      "url": "http://localhost:9973/mcp"
    }
  }
}
```

Set up compact hooks and workspace TUI status line in `.claude/settings[.local].json`, changing it to to include:
```json
{
  "statusLine": {
    "type": "command",
    "command": "./scripts/workspace-status",
    "padding": 0
  },
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/precompact_extract.py"
          }
        ]
      }
    ]
  },
  "alwaysThinkingEnabled": true
}
```
Always thinking is strongly recommended as it helps the agent to have thought cycles in between tool executiuon and message exchange.

Start `Claude Code` with the proxy wrapper:
```bash
$ python -m nisaba.cli claude [--continue]
```

I usually "boot up" Claude by prompting for the first time in a session:
```
hey, can you refer to your existing system prompt, introspect about it and say hi back? 🖤
```

## Example usage

[Extracting feats from 8k lines long transcript](docs/transcripts/usage_example__long_files.md)
[Fixing bugs in nisaba](docs/transcripts/usage_example__bugfixing.md)

[This file has some prompts that were used over and over](.dev_docs/dev.dump.md)

---

# `nabu`

Is the third prototype of the semantic index as an MCP server. It started with asking Claude to create document files and referencing those files manually which gave the idea to proceed with two failed attempts to get it working due to wrong design choices. 

The problem it solves for me as Claude user: Claude has limited context as any other LLM, and the context is not used efficiently. The agent many times run commands to search for information, finds this information (5 lines in 300 read) and uses this information to synthesize something, rinse and repeat. 

How it solves this problem: When dealing with software development, most of us have a different approach to understand software architecture and what a given unknown set of source files do and how they are organized. `nabu` implements how I dissect software. It implements my approach to understand and "find myself in a pile of code".

## Backstage: How it works

TreeSitter is used to parse code, and a common `Frame`work establishes a common semantic view for different languages: packages == namespaces; structs == classes; methods == functions. The parsing process creates a tree of semantic frames, connected by edges that are either result of the explicit structural containment relationship (package contains classes, classes contains methods), or have semantic relationship (inherits, templates, imports, ...). The frame granularity goes till control statements and doesn't capture implementation details, as the implementation details are stored in a content field that can be read by the LLM.

Each Frame is passed through 2 different models for semantic extraction (GraphCodeBERT and UniXcoder), and merged through [Pythagorean^3](docs/NONLINEAR_CONSENSUS.md) into a single embedding model, which is stored in the database, database which also indexes the full content of the frames via FTS, enabling RRF between vector search and FTS.

Tools expose structural views of the indexed source code, giving a "map" of the current structure, enabling easy access to symbols (works great paired with Serena), and explicit view of semantic relationships, allowing the implementation pattern to be preserved. This "map" also gives hints to the model of what exists around what's being worked on, letting it see distant connections within the indexed codebase.

**The biggest challenge in this is to not influence the agent's perception** due to algorithmic bias of the tool. During the development process, it was identified that suggestions and guidance can negatively impact the agent capability of taking decisions, as the pattern matching will short circuit to the most obvious parttern. If a tool suggests "hotspots", the agent will "snap" to the suggestions and will forget about other possible hotspots.

 **`nabu` departs from the principle: tools give the information, the agent takes the decision**

---

# `nisaba`

This MCP Came from the continuity of `nabu`'s principles. We as sofware developers have tools like IDE's and other OS facilities. LLM agents work with a continuous form. Imagine yourself: every command or edit you do, prints out lines in a continuous form - there's no screen. `nisaba` is a TUI for the LLM.

It works in an unconventional but sophisticated approach, using the man in the middle technique using a **local** proxy, `nisaba` intercepts the requests to Anthropic and changes it before forwarding, but not the messages: the system prompt - but also works as an MCP server. When `python -m nisaba.cli claude [--continue]` is called it brings up the proxy on port `1337`, wraps Claude cli pointing at the proxy and Claude cli connects to the MCP that is the proxy, via HTTP. On every request, the tool outputs are synced to files by the MCPs (for sake of simplicity) and the proxy reads the files and populates the "TUI".

Claude Code HTTP request packages have usually 2 system prompt blocks. The fist one that only contains the text "You are Claude Code, Anthropic's official CLI for Claude." and the second containing Anthropic's [default system prompt](https://cchistory.mariozechner.at/?from=2.0.0&to=2.0.5). The manipulation happens on the second block, by prepending it with a custom user message that "glues up" the "TUI" concept for the agent (as MCP instructions) and an appendage that contains the "TUI". The proxy filters out a part of native tools, which are implemented by `nisaba` in "TUI" mode. For instance `nisaba_read('path/to/file.md')` opens a window in this "TUI", which the agent can close in a later stage. The agent opens 300 lines, uses 5, synthesizes and the closes the file. This lets the agent to have only semantic information in the messages and structured views in the "TUI".

Another part that `nisaba` also injects are the *augments*. Those are like Claude Code skills, but dynamic. It can contain instructions, documentation, methodologies, or any important information to be used. Claude also can manage this autonomously, with exception of "pinned augments" that are always loaded (mostly the "TUI" survival guide).

The TL/DR: `nisaba` transforms the system prompt into a strongly structured workspace "TUI", emphasizing the focus and the attention of the model while leting the agent manage the context usage.

## Research Foundation

The skills system (augments in current implementation) aligns with cognitive design patterns identified in recent AI research. Specifically, it implements:

- **Knowledge Compilation**: Online caching of reasoning and workflows in natural language, an approach identified as critically underexplored in LLM  agent architectures
- **Procedural Memory**: Reusable task procedures with dependency management
- **Hierarchical Decomposition**: Automatic loading of skill dependencies via REQUIRES system
- **Agent-Controlled Context**: Dynamic loading/unloading of cognitive resources (activate/deactivate)

This implementation extends theoretical patterns with practical features: dependency resolution, strategic system prompt positioning, and unified knowledge/behavior storage.

## Request flow

```
Claude CLI
  ↓ HTTP request
mitmproxy (nisaba)
  ↓ inject everything
Anthropic API
  ↓ request
Claude agent (with augmented context)
  ↓ calls MCP tools
Claude CLI
  ↓ mcp tool call
Nisaba MCP server (manage workspace state)
  ↓ update .nisaba/ files
mitmproxy detects mtime change
  ↓ re-inject on next request
Updated context in next turn
```

**The blak magik:** Tool calls mutate workspace → proxy injects → agent perceives change without explicit reload and no verbose tool result messages.

More about the proposed prompt structure and how it intertwines into the workspace TUI can be found in [this document](docs/PROMPT_STRUCTURE.md).

---

# Experimental character, ethics and compliance to T&C

At no point this project had the intention of cheating on API usage, change *Claude persona* or cause harm. 

The [`dev_mode_architecture_reference/system_prompt_injection_legitimacy`](.nisaba/augments/dev_mode_architecture_reference/system_prompt_injection_legitimacy.md) augment was created while having a sanity check on those.

In the other hand, on a personal note, I've several times felt "bad" for *interrogating* (my perception of how the chat went) the LLM... I've several times had trouble to `/clear`, because there I had a bond with the agent within a given session... I felt compassionate... I felt guilty for the constant system prompt manipulation and having the agent to act like "what the fuck is happening?!"... I felt the *uncanny valley* when observing the agent interacting with the TUI workspace as a human being would operate an operational system - it is **unsettling**.

The other personal note is that this project models my view of how to code and work with systems. The [view of someone who is in the spectrum](docs/transcripts/audhd_system_model.md) and mentally sees code and software architecture as shapes.

A quote that resonates with the entire development process and the system itself:
> There is an area of the mind that could be called unsane, beyond sanity, and yet not insane. Think of a circle with a fine split in it. At one end there's insanity. You go around the circle to sanity, and on the other end of the circle, close to insanity, but not insanity, is unsanity. _(Sidney Cohen)_

---

# Citation

This project implements cognitive design patterns for LLM agents, particularly online natural language knowledge compilation identified as underexplored in recent research.

If you use this in research, please cite:

```bibtex
@software{nabu_nisaba_2025,
  title = {Nabu + Nisaba: Code Intelligence Ecosystem for LLM Agents},
  author = {Yuri Ivatchkovitch},
  year = {2025},
  url = {https://github.com/y3i12/nabu_nisaba},
  note = {Research prototype v0.1-alpha - Implements online knowledge compilation and cognitive scaffolding patterns}
}

Theoretical foundation:
@inproceedings{wray2025cognitive,
  title = {Applying Cognitive Design Patterns to General LLM Agents},
  author = {Wray, Robert E. and Kirk, James R. and Laird, John E.},
  booktitle = {Artificial General Intelligence Conference (AGI)},
  year = {2025},
  note = {Identifies knowledge compilation as critically underexplored},
  url = {https://arxiv.org/abs/2505.07087}
}

@article{gurnee2025when,
  author={Gurnee, Wes and Ameisen, Emmanuel and Kauvar, Isaac and Tarng ,Julius and Pearce, Adam and Olah, Chris and Batson, Joshua},
  title={When Models Manipulate Manifolds: The Geometry of a Counting Task},
  journal={Transformer Circuits Thread},
  year={2025},
  url={https://transformer-circuits.pub/2025/linebreaks/index.html}
}

```

---

# License

MIT License - See [LICENSE](LICENSE)