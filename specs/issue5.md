# Issue #5: AgentState + checkpointing (Postgres + JSON fallback)

**Labels:** `core`, `state`  
**Milestone:** 1-Core-Graph  
**Assignees:** @slmyers780

## Goal
Make the graph resumable across runs by adding Postgres-backed, **versioned** checkpoints with a reliable JSON-file fallback and a LangGraph-compatible checkpoint saver.

---

## Assumptions / Decisions (confirmed)
- DB driver: **Async SQLAlchemy 2.x + asyncpg** ✅
- Migrations: **Alembic** ✅
- Storage model: **JSONB** blob for full `AgentState` + indexed `thread_id` + versioned history
- Retention: **Versioned history** (append rows per checkpoint; do not overwrite)

---

## Outcomes (deliverables)
- Local Postgres dev infra (`infra/postgres/` with Terraform + Docker)
- Alembic migrations that create a `checkpoints` table
- DB-backed, versioned checkpoint persistence (JSONB) with file fallback
- Canonical `save_checkpoint` / `load_checkpoint` API used by the app and LangGraph saver
- LangGraph-compatible custom saver wired into `graph`
- `python main.py resume --thread_id <id>` behavior and tests

---

## Agents & Responsibilities (parallel)

### Agent A — Terraform + Migrations (infra)
**Primary goal:** provide repeatable local Postgres + migrations.

Tasks
- Add Terraform config under `infra/postgres/` (Docker-based Postgres dev) and expose `DATABASE_URL` via outputs.
- Add Alembic scaffolding and initial migration `0001_create_checkpoints.py`.
- Migration schema: `id UUID PK`, `thread_id TEXT (indexed)`, `version INTEGER`, `state JSONB`, `created_at TIMESTAMP`, `updated_at TIMESTAMP` (unique/index on `(thread_id, version)`).
- Add `infra/postgres/README.md` and development helper script (e.g. `scripts/dev-db-up.sh`).

Acceptance
- `terraform` spins up a dev Postgres and prints `DATABASE_URL`.
- `alembic upgrade head` creates the `checkpoints` table matching the ORM model.

---

### Agent B — Postgres support, JSON fallback, LangGraph saver, CLI `resume` (app)
**Primary goal:** implement DB persistence + JSON fallback + LangGraph saver and resume CLI.

Tasks
- Implement `graph/persistence.py` (async SQLAlchemy engine + `Checkpoint` model + helpers):
  - `save_checkpoint_db(state_dict, thread_id)`
  - `load_checkpoint_db(thread_id, version=None)`
  - `list_checkpoints_db(thread_id)`
- Extend `graph/state.py` (preserve existing file helpers) and add canonical async APIs:
  - `async save_checkpoint(state: AgentStateModel, thread_id: str)` — prefer DB, fallback to file on DB error
  - `async load_checkpoint(thread_id: str, version: Optional[int] = None)` — prefer DB, fallback to file
- Add LangGraph saver adapter `graph/langgraph_saver.py` and register it in `graph/graph.py` so LangGraph checkpoint hooks call the canonical API.
- Add `resume` CLI in `main.py` that restores state via `load_checkpoint` and resumes the run.
- Add tests: `tests/test_state_db.py`, `tests/test_checkpoint_fallback.py`, `tests/test_cli_resume.py` and extend `tests/test_state.py`.
- Update `.env.example` and `requirements.txt` (`sqlalchemy`, `asyncpg`, `alembic`).

Acceptance
- `save_checkpoint` writes a JSONB row with incremented `version` and metadata.
- `load_checkpoint` returns the exact `AgentState` previously saved.
- File fallback is exercised when DB is unreachable.
- `python main.py resume --thread_id <id>` restores and resumes a run.

---

## API contracts (stable surface)
- `async def save_checkpoint(state: AgentStateModel, thread_id: str) -> dict` — persists state (DB preferred), returns `{id, thread_id, version, created_at}`.
- `async def load_checkpoint(thread_id: str, version: Optional[int] = None) -> AgentStateModel` — loads checkpoint (latest if `version` is None).
- DB helpers in `graph/persistence.py` are async and accept/return raw `dict` payloads.
- LangGraph saver adapter forwards LangGraph saver hooks to the canonical async APIs.

> Note: Keep existing file-based helpers (`save_checkpoint_file` / `load_checkpoint_file`) unchanged for backward compatibility.

---

## Tests & verification (key cases)
- DB roundtrip: `save_checkpoint` → `load_checkpoint` → equality with original `AgentState`.
- Versioning: multiple saves for same `thread_id` produce increasing `version` values.
- Fallback: simulate DB failure → checkpoint saved to file and loadable.
- CLI resume: interrupt a run → `python main.py resume --thread_id <id>` restores exact `AgentState`.
- Migration test: Alembic creates expected `checkpoints` table.

Recommended local checks
- Start DB: `scripts/dev-db-up.sh`
- Apply migrations: `alembic upgrade head`
- Run tests: `pytest tests/test_state_db.py::test_save_and_load_checkpoint -q`
- Resume smoke: `python main.py run --spec specs/todo.md` → interrupt → `python main.py resume --thread_id <id>`

---

## PR split & review checklist

**PR A — infra & migrations (Agent A)**
- Adds `infra/postgres/*` Terraform files
- Adds `alembic/*` + initial migration
- Adds `scripts/dev-db-up.sh` and `infra/postgres/README.md`

Review checklist
- Terraform spins up Postgres locally
- Alembic migration reflects `Checkpoint` schema

**PR B — app + saver + tests (Agent B)**
- Adds `graph/persistence.py`, `graph/langgraph_saver.py`
- Updates `graph/state.py`, registers saver in `graph/graph.py`
- Adds CLI `resume` and tests
- Updates `requirements.txt` & `.env.example`

Review checklist
- Async DB API matches migration schema
- File fallback intact and covered by tests
- LangGraph saver wired and tested
- CLI `resume` integration test passes

---

## Timeline (estimate)
- Agent A (infra + migrations): 1–2 days
- Agent B (persistence + saver + CLI + tests): 2–4 days
- Integration & QA: 1 day
- Total wall-clock: ~1 week (parallel workstreams)

---

## Risks & mitigations
- Schema drift between Alembic and ORM — add CI migration smoke test.
- DB unavailable in dev/CI — keep JSON-file fallback and add tests simulating DB failure.
- LangGraph saver interface mismatch — implement a small adapter and unit tests.

---

## Minimal acceptance criteria (Definition of Done)
- Postgres-backed, versioned checkpoints persist and can be loaded.
- JSON-file fallback remains functional when DB is unavailable.
- LangGraph uses the custom saver for checkpointing during runs.
- `python main.py resume --thread_id <id>` restores and resumes a run.
- Alembic migrations exist and are applied in CI/dev.
