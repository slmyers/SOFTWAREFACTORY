"""Tests for CLI entry points in main.py (Issue #10).

Tests cover the `run`, `dev`, and `resume` commands using typer's CliRunner
so that no real graph execution or external API is needed.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------


def test_run_requires_spec():
    """run command must fail when --spec is not provided."""
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0


def test_run_invokes_graph(tmp_path: Path):
    """run command builds initial state and invokes the compiled graph."""
    spec = tmp_path / "todo.md"
    spec.write_text("# Todo spec")

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"next": "__end__"}

    with patch("main.compile_graph", return_value=mock_graph):
        result = runner.invoke(app, ["run", "--spec", str(spec)])

    assert result.exit_code == 0, result.output
    mock_graph.invoke.assert_called_once()
    call_args = mock_graph.invoke.call_args
    initial_state = call_args[0][0]
    assert initial_state["spec_path"] == str(spec)
    assert initial_state["spec_content"] == "# Todo spec"
    assert initial_state["iteration"] == 0
    assert initial_state["codebase"] == {}


def test_run_accepts_thread_id(tmp_path: Path):
    """run command accepts an explicit --thread-id."""
    spec = tmp_path / "todo.md"
    spec.write_text("")

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"next": "__end__"}

    with patch("main.compile_graph", return_value=mock_graph):
        result = runner.invoke(
            app, ["run", "--spec", str(spec), "--thread-id", "test-thread-123"]
        )

    assert result.exit_code == 0, result.output
    config = mock_graph.invoke.call_args[0][1]
    assert config["configurable"]["thread_id"] == "test-thread-123"


# ---------------------------------------------------------------------------
# dev command
# ---------------------------------------------------------------------------


def test_dev_verbose_output(tmp_path: Path):
    """dev command prints DEV mode message and verbose thread/spec info."""
    spec = tmp_path / "spec.md"
    spec.write_text("# Dev spec")

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"next": "__end__"}

    with patch("main.compile_graph", return_value=mock_graph):
        result = runner.invoke(app, ["dev", "--spec", str(spec)])

    assert result.exit_code == 0, result.output
    assert "DEV mode" in result.output
    assert str(spec) in result.output


def test_dev_invokes_graph(tmp_path: Path):
    """dev command also invokes the compiled graph."""
    spec = tmp_path / "spec.md"
    spec.write_text("")

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"next": "__end__"}

    with patch("main.compile_graph", return_value=mock_graph):
        result = runner.invoke(app, ["dev", "--spec", str(spec)])

    assert result.exit_code == 0, result.output
    mock_graph.invoke.assert_called_once()


# ---------------------------------------------------------------------------
# resume command
# ---------------------------------------------------------------------------


def test_resume_missing_checkpoint(tmp_path: Path):
    """resume exits with code 1 when the checkpoint file does not exist."""
    with patch(
        "main.load_checkpoint",
        side_effect=FileNotFoundError("not found"),
    ):
        result = runner.invoke(app, ["resume", "--thread-id", "no-such-thread"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_resume_restores_state(tmp_path: Path):
    """resume loads checkpoint, rebuilds state, and invokes the graph."""
    from graph.state import AgentStateModel

    saved_state = AgentStateModel(
        spec_path="specs/todo.md",
        codebase={"main.py": "x = 1"},
        iteration=2,
        quality_score=60.0,
    )

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"next": "__end__"}

    async def _fake_load(thread_id, version=None):
        return saved_state

    with patch("main.load_checkpoint", side_effect=_fake_load), patch(
        "main.compile_graph", return_value=mock_graph
    ):
        result = runner.invoke(app, ["resume", "--thread-id", "my-thread"])

    assert result.exit_code == 0, result.output
    mock_graph.invoke.assert_called_once()
    state_arg = mock_graph.invoke.call_args[0][0]
    assert state_arg["spec_path"] == "specs/todo.md"
    assert state_arg["iteration"] == 2


def test_resume_overrides_spec(tmp_path: Path):
    """resume --spec overrides the spec_path from the checkpoint."""
    from graph.state import AgentStateModel

    saved_state = AgentStateModel(
        spec_path="specs/old.md",
        codebase={},
        iteration=1,
        quality_score=50.0,
    )

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"next": "__end__"}

    async def _fake_load(thread_id, version=None):
        return saved_state

    new_spec = tmp_path / "new.md"
    new_spec.write_text("# new")

    with patch("main.load_checkpoint", side_effect=_fake_load), patch(
        "main.compile_graph", return_value=mock_graph
    ):
        result = runner.invoke(
            app, ["resume", "--thread-id", "t1", "--spec", str(new_spec)]
        )

    assert result.exit_code == 0, result.output
    state_arg = mock_graph.invoke.call_args[0][0]
    assert state_arg["spec_path"] == str(new_spec)
