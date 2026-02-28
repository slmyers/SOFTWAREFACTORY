**SOFTWAREFACTORY Issue Templates (Ready to Copy-Paste)**

Below are **full, ready-to-use GitHub issue templates** for every one of the 46 issues in our PLAN.md.

Each one includes:
- **Exact title**
- **Labels** (use these — create them in repo settings if needed)
- **Milestone**
- **Assignees** (you or me)
- **Body** (with description, acceptance criteria, and checkbox tasks)

You can create them in bulk using GitHub’s web UI or the GitHub CLI (`gh issue create`).

I’ve formatted them so you can copy one at a time or script it.

---

### Milestone 0: Foundations

**Issue #1: Repo bootstrap + dev environment (SOFTWAREFACTORY)**
**Labels:** `infra`, `setup`
**Milestone:** 0-Foundations
**Assignees:** @raptor-mini

**Body:**
```
# Repo Bootstrap

Create the SOFTWAREFACTORY repository with the exact structure from PLAN.md.

## Tasks
- [x] Create GitHub repo (public or private)
- [x] Add `.gitignore` (Python + venv + .env)
- [x] Create `pyproject.toml` (or requirements.txt) with core deps: langgraph, langchain, pydantic, python-dotenv, docker, etc.
- [x] Add `.env.example`
- [x] Create `README.md` with quickstart + link to `docs/PLAN.md`
- [x] Create empty directories: `agents/`, `tools/`, `graph/`, `harness/`, `sandbox/`, `mcp/`, `specs/`, `tests/`, `docs/`
- [x] Commit initial skeleton + push

## Definition of Done
Repo matches the structure in PLAN.md and is cloneable.
```

**Issue #2: LangSmith + LangGraph Studio + Langfuse self-hosted setup**
**Labels:** `infra`, `observability`
**Milestone:** 0-Foundations
**Assignees:** @slmyers780

**Body:**
```
# Observability Stack Setup

Set up tracing for the entire graph.

## Tasks
- [x] Sign up / configure LangSmith (free tier)
- [x] Add LangSmith env vars to `.env.example`
- [x] Install `langgraph-cli` and test `langgraph dev`

## Definition of Done
`langgraph dev` works and traces appear in both LangSmith and Langfuse.
```

**Issue #3: Pydantic v2 AgentState (full typed dict with validation)**
**Labels:** `core`, `state`
**Milestone:** 0-Foundations
**Assignees:** @slmyers780

**Body:**
```
# AgentState Definition

Define the central typed state for the entire graph.

## Tasks
- [x] Create `graph/state.py`
- [x] Implement `AgentState` as TypedDict + Pydantic model (v2)
- [x] Add all fields from PLAN.md (spec_path, codebase, quality_score, etc.)
- [x] Add validation (e.g. non-negative iteration, required fields)
- [x] Add serialization helpers (to_dict, from_dict)

## Definition of Done
State passes Pydantic validation and can be checkpointed.
```

**Issue #4: AGENTS.md + quality-score.md + invariants.md templates (harness scaffolding)**
**Labels:** `harness`, `docs`
**Milestone:** 0-Foundations
**Assignees:** @slmyers780

**Body:**
```
# Harness Scaffolding Templates

Create the self-documenting files that agents will read/write.

## Tasks
- [x] Create `docs/AGENTS.md` (role descriptions)
- [x] Create `harness/quality-score.md` template
- [x] Create `harness/invariants.md` template
- [x] Create `harness/exec-plans/` directory with example
- [x] Make a small script that auto-generates these on first run

## Definition of Done
Templates exist and match the Harness philosophy.
```

---

### Milestone 1: Core Graph & State

**Issue #5: AgentState + checkpointing (Postgres + JSON fallback)**
**Labels:** `core`, `state`
**Milestone:** 1-Core-Graph
**Assignees:** @slmyers780

**Body:**
```
# Persistent State & Checkpoints

Make the graph resumable across runs.

## Tasks
- [x] Add Postgres support (SQLAlchemy + async)
- [x] Implement JSON file fallback
- [x] Add `save_checkpoint` / `load_checkpoint` to state
- [x] Use LangGraph’s built-in checkpointing with custom saver
- [x] Add terraform config for local postgres with docker
- [x] Add any necessary migrations

## Definition of Done
A run can be killed and resumed with `python main.py resume --thread_id xxx`
```

**Issue #6: Load/save from spec.md + codebase dict**
**Labels:** `core`, `filesystem`
**Milestone:** 1-Core-Graph
**Assignees:** @slmyers780

**Body:**
```
# Spec & Codebase Persistence

Agents must always work against real files on disk.

## Tasks
- [x] Implement `load_spec()` and `save_spec()`
- [x] Implement `load_codebase()` / `save_codebase()` (dict ↔ disk)
- [x] Add gitignore for temp files

## Definition of Done
After any run, spec.md and all code files are up-to-date on disk.
```

**Issue #7: Supervisor node + routing logic**
**Labels:** `agent`, `supervisor`
**Milestone:** 1-Core-Graph
**Assignees:** @slmyers780

**Body:**
```
# Supervisor — The Brain

Central decision maker.

## Tasks
- [x] Create `agents/supervisor.py`
- [x] Implement routing based on quality_score, invariants, test_results
- [x] Support human pause
- [x] Use DeepSeek-R1 for decisions

## Definition of Done
Supervisor correctly routes to next node in a test graph.
```

**Issue #8: Decision prompts + few-shot examples for DeepSeek-R1**
**Labels:** `agent`, `prompts`
**Milestone:** 1-Core-Graph
**Assignees:** @slmyers780

**Body:**
```
# Supervisor Prompts

Make routing reliable.

## Tasks
- [x] Create prompt templates in `prompts/`
- [x] Add few-shot examples for common decisions
- [x] Test with 5 synthetic states

## Definition of Done
Supervisor makes correct routing 95%+ of the time in tests.
```

**Issue #9: graph/compile.py factory with all nodes wired (empty stubs)**
**Labels:** `core`, `graph`
**Milestone:** 1-Core-Graph
**Assignees:** @slmyers780

**Body:**
```
# Graph Factory

Central place to build the LangGraph.

## Tasks
- [ ] Create `graph/compile.py`
- [ ] Add all 8 nodes as stubs
- [ ] Wire basic edges + conditional routing

## Definition of Done
`compile_graph()` returns a runnable app.
```

**Issue #10: Entry points: CLI run, dev, resume**
**Labels:** `cli`, `infra`
**Milestone:** 1-Core-Graph
**Assignees:** @slmyers780

**Body:**
```
# CLI Interface

User-friendly entrypoints.

## Tasks
- [ ] Create `main.py` with Typer/Click
- [ ] Implement `run`, `dev`, `resume` commands
- [ ] Pass spec_path and thread_id

## Definition of Done
`python main.py run --spec specs/todo.md` works (even with stubs).
```

---

### Milestone 2: Agents / Nodes

**Issue #11: SpecParser node**
**Labels:** `agent`
**Milestone:** 2-Agents
**Assignees:** @slmyers780

**Body:**
```
# SpecParser Agent

Reads and structures spec.md.

## Tasks
- [ ] Create `agents/spec_parser.py`
- [ ] Parse into spec_structure dict
- [ ] Detect TODOs and ambiguities

## Definition of Done
Node correctly populates state.spec_structure.
```

(Continue similarly for #12–#19 — each gets its own focused template with 4–6 checkbox tasks matching the role in the spec.)

**Issue #19: DocGardener node**
**Labels:** `agent`, `harness`
**Milestone:** 2-Agents
**Assignees:** @slmyers780

**Body:**
```
# DocGardener Agent

Keeps the harness clean.

## Tasks
- [ ] Create `agents/doc_gardener.py`
- [ ] Find stale exec-plans and docs
- [ ] Propose updates

## Definition of Done
Runs after Supervisor and cleans up.
```

---

### Milestone 3: Tools

**Issue #20: Filesystem tools**
**Labels:** `tools`
**Milestone:** 3-Tools
**Assignees:** @slmyers780

**Body:**
```
# Filesystem Tool Suite

Core read/write for agents.

## Tasks
- [ ] `read_file`, `write_file`, `list_dir`, `grep`
- [ ] Bind to LangGraph ToolNode
- [ ] Safe paths (only inside project dir)

## Definition of Done
All agents can read/write spec and code.
```

**Issue #26: MCP Client + registry**
**Labels:** `tools`, `mcp`
**Milestone:** 3-Tools
**Assignees:** @slmyers780

**Body:**
```
# MCP Integration Core

Make GenAI Toolbox and MCP-Obsidian first-class.

## Tasks
- [ ] Create `mcp/client.py`
- [ ] Auto-discover running MCP servers
- [ ] Unified `call_mcp_tool` function

## Definition of Done
`call_mcp_tool("genai-toolbox", "query", ...)` works (even if stubbed).
```

(And so on for the rest of the tools — each has its own tight, parallelizable issue.)

---

Issue #47: Unified Diff Editing Pipeline
Labels: tools, agent, harness
Milestone: 3-Tools
Body:
text# Unified Diffs for Safe, Precise Edits

Adopt the industry-standard edit format used by Aider/Cursor.

## Tasks
- [ ] Update Coder prompt to force GNU unified diff output only
- [ ] Create `tools/file_edits.py` with `apply_unified_diff(path, diff_content)`
- [ ] Add `patch` library + safety checks (no deletions outside project, etc.)
- [ ] Update Reviewer to critique diffs (not full files)
- [ ] Add diff preview in CLI + LangSmith trace
- [ ] Test on 5 real edits (add feature, refactor, bugfix)

## Definition of Done
Coder → Reviewer → apply loop works end-to-end with <5% hallucinated diffs.

Issue #48: Codebase Semantic Index + Hybrid Search Tool
Labels: tools, mcp, harness
Milestone: 3-Tools
Body:
text# Semantic Codebase Search (RAG for Agents)

Give every agent instant, intent-aware codebase understanding.

## Tasks
- [ ] Create `tools/code_index.py` (chunk by function/class + embed)
- [ ] Choose embedding model (Qwen3 or BGE-M3 via OpenAI-compatible)
- [ ] Set up Chroma/PGVector store (persist in `./.softwarefactory/index/`)
- [ ] Implement `codebase_search` tool (hybrid semantic + keyword)
- [ ] Auto-reindex on git changes (via git hook or Executor)
- [ ] Integrate with MCP so external tools can also query it
- [ ] Benchmark: "find auth logic" vs grep on todo-app spec

## Definition of Done
Agents using `codebase_search` solve tasks 20%+ faster in e2e tests.

Issue #49: Playwright MCP Browser Automation Server
Labels: tools, mcp, harness, priority-high
Milestone: 3-Tools
Assignees: @slmyers780 (or the first person who wants to own browser god-mode)
Body (copy-paste ready):
text# Playwright MCP Integration

Give agents full browser control via official Microsoft MCP server.

## Why now
- Perfect complement to our existing MCP registry (GenAI Toolbox, Obsidian)
- Enables real E2E testing, UI validation, self-healing tests
- Matches OpenAI Harness observability (videos, snapshots)
- Works out-of-the-box with DeepSeek/Qwen

## Tasks
- [ ] Add Playwright MCP to MCP registry (auto-discover + launch script)
- [ ] Create `tools/browser.py` wrapper (`browser_action` tool)
- [ ] Docker compose entry for playwright-mcp (headless + persistent)
- [ ] Update Executor/Reviewer prompts to use it for web specs
- [ ] Add video recording + accessibility tree to quality-score.md
- [ ] E2E test: agent builds a TODO app → runs browser tests → passes
- [ ] Benchmark: time-to-green for web specs with vs without browser tools

## Definition of Done
Any web-related spec can be fully implemented + tested end-to-end by the graph with zero human browser interaction.
