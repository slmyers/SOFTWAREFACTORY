# Issue #3 — Pydantic v2 AgentState (spec)

Goal
----
Define the canonical runtime state for the graph as a `TypedDict` + Pydantic v2 model with JSON checkpoint helpers.

Scope
-----
- `graph/state.py`: `AgentState` (TypedDict) and `AgentStateModel` (Pydantic v2)
- JSON checkpoint helpers: `save_checkpoint` / `load_checkpoint` (sync, JSON fallback)
- Unit tests in `tests/test_state.py` covering validation, serialization, and checkpointing

Fields (authoritative)
----------------------
- `spec_path: str` (required, non-empty)
- `spec_content: str` (default: empty)
- `spec_structure: dict` (default: {})
- `codebase: dict[str, str]` (required)
- `plan: list[dict]` (default: [])
- `test_results: list[dict]` (default: [])
- `issues: list[str]` (default: [])
- `iteration: int` (required, >= 0)
- `next: str` (default: "")
- `checkpoint: dict` (default: {})
- `mcp_servers: list[str]` (default: [])
- `quality_score: float` (required, 0..100)
- `invariants: list[str]` (default: [])

Acceptance criteria
-------------------
- Model validates required/core fields and rejects invalid values
- `to_dict`/`from_dict` round-trip works
- `save_checkpoint` / `load_checkpoint` JSON fallback works and is tested

Notes
-----
DB/Postgres persistence is intentionally deferred to Issue #5.
