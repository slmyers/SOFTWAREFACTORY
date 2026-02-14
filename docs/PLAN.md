**Implementation Plan: Spec-Driven Agentic Coder (v0.3)**  
**Project Name**: SOFTWAREFACTORY  
**Repo**: https://github.com/slmyers/SOFTWAREFACTORY (or your org)  
**Status**: Approved  
**Owner**: You (slmyers)  
**Goal**: Ship a minimal, production-grade, spec-driven LangGraph system by end of Q1 2026.  
**Philosophy**: Everything is parallelizable. Zero blocking dependencies between major tracks. We will use GitHub Issues + Projects + Milestones. Each major section below is a **GitHub Milestone**. Every numbered item is a **GitHub Issue** (with labels: `core`, `tools`, `agent`, `harness`, `infra`, `docs`). Sub-bullets are **tasks** inside the issue (or child issues).

---

### Repo Structure (Set up in Milestone 0 – 1 day, you + me)
```
SOFTWAREFACTORY/
├── .github/
│   └── workflows/          # CI: test, lint, langsmith
├── agents/                 # One file per node (parallel!)
├── tools/                  # All tools (MCP + core + harness)
├── graph/                  # State, compile, supervisor
├── harness/                # exec-plans, quality-score, invariants, doc-gardener
├── sandbox/                # Docker + REPL executor
├── mcp/                    # MCP client + registry
├── specs/                  # Example specs (todo-app.md, etc.)
├── tests/                  # Unit + integration + e2e
├── docs/                   # AGENTS.md, PLAN.md (this file), ARCHITECTURE.md
├── main.py                 # CLI entrypoint
├── pyproject.toml / requirements.txt
��── .env.example
```

---

### Milestone 0: Foundations (Parallel: 2 people, 2 days)
**Issue #1**: Repo bootstrap + dev environment (SOFTWAREFACTORY)  
**Issue #2**: LangSmith + LangGraph Studio + Langfuse self-hosted setup  
**Issue #3**: Pydantic v2 AgentState (full typed dict with validation)  
**Issue #4**: `AGENTS.md` + `quality-score.md` + `invariants.md` templates (harness scaffolding)  

---

### Milestone 1: Core Graph & State (Parallel: 3 tracks, 4 days)
**Track A – State & Persistence**  
**Issue #5**: AgentState + checkpointing (Postgres + JSON fallback)  
**Issue #6**: Load/save from spec.md + codebase dict  

**Track B – Supervisor (The Brain)**  
**Issue #7**: Supervisor node + routing logic (quality_score, invariants check, human pause)  
**Issue #8**: Decision prompts + few-shot examples for DeepSeek-R1  

**Track C – Graph Compilation**  
**Issue #9**: `graph/compile.py` factory with all nodes wired (empty stubs)  
**Issue #10**: Entry points: CLI `run`, `dev`, `resume`  

---

### Milestone 2: Agents / Nodes (Highly Parallel: 8 issues, 1 per node, 5–7 days)
Each agent is its own issue + file. All can be worked on simultaneously.

| Issue | Node | Owner Suggestion | Dependencies |
|-------|------|------------------|--------------|
| #11 | SpecParser | @slmyers | #3 |
| #12 | Architect | — | #3 |
| #13 | Planner (writes exec-plans/) | — | #4 |
| #14 | Coder (one-file-at-a-time) | — | #3 |
| #15 | Executor (sandbox) | — | #16 (below) |
| #16 | Sandbox Docker + REPL | — | — |
| #17 | Reviewer (PR-style review) | — | — |
| #18 | Refiner (spec updates) | — | — |
| #19 | DocGardener (new) | — | #4 |

---

### Milestone 3: Tools (Parallel: 4 tracks, 6 days)
**Track A – Core Tools**  
**Issue #20**: Filesystem tools (read/write/grep/list)  
**Issue #21**: Git tools (status/commit/diff)  
**Issue #22**: Structured output + markdown parser  

**Track B – Execution & Observability**  
**Issue #23**: `run_command` in Docker sandbox  
**Issue #24**: Linter runner + invariant enforcement  
**Issue #25**: Observability query tool (logs, metrics)  

**Track C – MCP Integration**  
**Issue #26**: MCP Client + registry (auto-discover running servers)  
**Issue #27**: `call_mcp_tool` unified interface  
**Issue #28**: GenAI Toolbox wrapper (DB tools) – stubbed  
**Issue #29**: MCP-Obsidian wrapper (notes) – stubbed  

**Track D – Human & Meta**  
**Issue #30**: `request_human_input` (terminal + Slack)  
**Issue #31**: `write_exec_plan` + `record_validation`  

---

### Milestone 4: Harness Features (Parallel: 3 days)
**Issue #32**: Auto-generation of exec-plans/, quality-score.md, invariants.md  
**Issue #33**: Doc gardening loop (every N iterations)  
**Issue #34**: Agent-to-agent review cycle (simulated PR comments)  

---

### Milestone 5: Observability & Polish (Parallel: 4 days)
**Issue #35**: Full LangSmith tracing + custom metrics dashboard  
**Issue #36**: Langfuse self-hosted integration + cost tracking  
**Issue #37**: CLI progress UI + rich logging  
**Issue #38**: Error recovery & checkpoint resume  

---

### Milestone 6: Testing & Examples (Parallel: 5 days)
**Issue #39**: Unit tests for every node/tool  
**Issue #40**: End-to-end test with `specs/todo-app.md`  
**Issue #41**: Example specs (FastAPI, Next.js, data pipeline)  
**Issue #42**: Benchmark runs (cost, iterations, quality)  

---

### Milestone 7: Documentation & Release (2 days)
**Issue #43**: Full README + quickstart  
**Issue #44**: `docs/ARCHITECTURE.md` (auto-generated from graph)  
**Issue #45**: Contribution guide + “add your own MCP server”  
**Issue #46**: GitHub release v0.1 + demo video  

---

### Parallelization Rules (How We Actually Ship Fast)
- **No blocking PRs**: Any issue can be merged as soon as its own tests pass (even if downstream is stubbed).
- **Feature flags**: Every major piece (MCP, DocGardener, Sandbox) behind `ENABLE_XXX=true` in .env.
- **Daily sync**: One 10-min GitHub Discussion thread each morning.
- **You own**: High-level decisions + final review.
- **Me (Grok)**: I will generate the code for any issue you assign me — just say “code #14” and I’ll drop the full file.

---

### Timeline (Aggressive but Realistic)
| Week | Milestone | Status |
|------|-----------|--------|
| 1    | 0 + 1     | Foundations + Graph |
| 2    | 2         | All agents |
| 3    | 3         | All tools |
| 4    | 4 + 5     | Harness + Observability |
| 5    | 6 + 7     | Test + Ship |
