import os
import uuid
import pytest

import pytest_asyncio
import graph.persistence as persistence
from graph.state import AgentStateModel


@pytest_asyncio.fixture
async def thread_id():
    tid = f"test-tid-{uuid.uuid4().hex[:8]}"
    yield tid
    # best-effort cleanup of DB rows created by the test
    try:
        await persistence.delete_checkpoints_db(tid)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_persistence_db_roundtrip_or_skip(thread_id):
    """Save -> load roundtrip against Postgres. Skips when DATABASE_URL is not set."""
    if os.getenv("DATABASE_URL") is None:
        pytest.skip("DATABASE_URL not configured; skipping DB integration test")

    s = AgentStateModel(
        spec_path="specs/todo.md",
        codebase={"x.py": "x = 1"},
        iteration=0,
        quality_score=10.0,
    )

    meta = await persistence.save_checkpoint_db(s.to_dict(), thread_id)
    assert meta["thread_id"] == thread_id
    assert isinstance(meta["version"], int) and meta["version"] >= 1

    loaded = await persistence.load_checkpoint_db(thread_id)
    assert loaded["spec_path"] == s.spec_path
    assert loaded["codebase"] == s.codebase
    assert loaded["iteration"] == s.iteration


@pytest.mark.asyncio
async def test_versioning_increments_or_skip(thread_id):
    if os.getenv("DATABASE_URL") is None:
        pytest.skip("DATABASE_URL not configured; skipping DB integration test")

    s1 = AgentStateModel(
        spec_path="specs/todo.md",
        codebase={"a.py": "a = 1"},
        iteration=1,
        quality_score=20.0,
    )

    s2 = AgentStateModel(
        spec_path="specs/todo.md",
        codebase={"a.py": "a = 2"},
        iteration=2,
        quality_score=30.0,
    )

    m1 = await persistence.save_checkpoint_db(s1.to_dict(), thread_id)
    m2 = await persistence.save_checkpoint_db(s2.to_dict(), thread_id)

    assert m2["version"] == m1["version"] + 1

    entries = await persistence.list_checkpoints_db(thread_id)
    versions = [e["version"] for e in entries]
    assert versions[0] == m2["version"]
    assert versions[-1] == m1["version"]
