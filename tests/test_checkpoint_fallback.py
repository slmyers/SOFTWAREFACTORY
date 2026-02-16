from pathlib import Path

import pytest

import graph.persistence as persistence
from graph.state import AgentStateModel, save_checkpoint


@pytest.mark.asyncio
async def test_save_checkpoint_falls_back_to_file_on_db_error(
    tmp_path: Path, monkeypatch
):
    # Force persistence.save_checkpoint_db to raise so the file-fallback path is exercised
    async def _raise(*args, **kwargs):
        raise RuntimeError("simulated db failure")

    monkeypatch.setattr(persistence, "save_checkpoint_db", _raise)

    # Run in a temp working dir so the "checkpoints/<thread_id>.json" file is created there
    monkeypatch.chdir(tmp_path)

    s = AgentStateModel(
        spec_path="specs/todo.md",
        codebase={"f.py": "x=1"},
        iteration=0,
        quality_score=50.0,
    )

    thread_id = "fallback-test-tid"

    meta = await save_checkpoint(s, thread_id)
    assert meta["thread_id"] == thread_id

    cp_path = tmp_path / "checkpoints" / f"{thread_id}.json"
    assert cp_path.exists()

    loaded = AgentStateModel.load_checkpoint(cp_path)
    assert loaded.spec_path == s.spec_path
    assert loaded.codebase == s.codebase
    assert loaded.iteration == s.iteration
