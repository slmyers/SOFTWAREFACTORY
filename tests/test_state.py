from pathlib import Path

import pytest
from pydantic import ValidationError

from graph.state import AgentStateModel


def test_valid_state_roundtrip():
    s = AgentStateModel(
        spec_path="specs/todo.md",
        codebase={"main.py": "print('hi')"},
        iteration=0,
        quality_score=50.0,
    )

    d = s.to_dict()
    s2 = AgentStateModel.from_dict(d)

    assert s2.spec_path == s.spec_path
    assert s2.codebase == s.codebase
    assert s2.iteration == s.iteration
    assert s2.quality_score == s.quality_score


def test_negative_iteration_raises():
    with pytest.raises(ValidationError):
        AgentStateModel(spec_path="specs/todo.md", codebase={}, iteration=-1, quality_score=10.0)


def test_quality_score_bounds():
    with pytest.raises(ValidationError):
        AgentStateModel(spec_path="specs/todo.md", codebase={}, iteration=0, quality_score=-0.1)

    with pytest.raises(ValidationError):
        AgentStateModel(spec_path="specs/todo.md", codebase={}, iteration=0, quality_score=101)


def test_checkpoint_file_roundtrip(tmp_path: Path):
    s = AgentStateModel(
        spec_path="specs/todo.md",
        codebase={"a.py": "x = 1"},
        iteration=1,
        quality_score=75.5,
        issues=["I1"],
        mcp_servers=["localhost:5000"],
    )

    cp = tmp_path / "harness" / "checkpoints" / "agent_state.json"
    s.save_checkpoint(cp)

    loaded = AgentStateModel.load_checkpoint(cp)
    assert loaded.spec_path == s.spec_path
    assert loaded.codebase == s.codebase
    assert loaded.iteration == s.iteration
    assert loaded.quality_score == s.quality_score
    assert loaded.issues == s.issues
    assert loaded.mcp_servers == s.mcp_servers


def test_spec_path_non_empty():
    with pytest.raises(ValidationError):
        AgentStateModel(spec_path="", codebase={}, iteration=0, quality_score=0.0)
