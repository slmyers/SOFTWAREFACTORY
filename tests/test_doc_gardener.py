"""Tests for agents/doc_gardener.py — Issue #19: DocGardener node."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.doc_gardener import DocGardener, _all_tasks_done


# ---------------------------------------------------------------------------
# _all_tasks_done helper
# ---------------------------------------------------------------------------


def test_all_tasks_done_all_checked():
    content = "# Plan\n- [x] Task one\n- [X] Task two\n"
    assert _all_tasks_done(content) is True


def test_all_tasks_done_some_unchecked():
    content = "# Plan\n- [x] Task one\n- [ ] Task two\n"
    assert _all_tasks_done(content) is False


def test_all_tasks_done_no_tasks():
    content = "# Plan\nNo tasks here.\n"
    assert _all_tasks_done(content) is False


def test_all_tasks_done_single_unchecked():
    content = "- [ ] Only task\n"
    assert _all_tasks_done(content) is False


# ---------------------------------------------------------------------------
# DocGardener.find_stale_exec_plans
# ---------------------------------------------------------------------------


def test_find_stale_exec_plans_detects_all_done(tmp_path: Path):
    ep_dir = tmp_path / "exec-plans"
    ep_dir.mkdir()
    (ep_dir / "done.md").write_text("- [x] Task A\n- [x] Task B\n")
    (ep_dir / "pending.md").write_text("- [x] Task A\n- [ ] Task B\n")

    dg = DocGardener()
    stale = dg.find_stale_exec_plans(ep_dir)
    assert stale == [ep_dir / "done.md"]


def test_find_stale_exec_plans_empty_dir(tmp_path: Path):
    ep_dir = tmp_path / "exec-plans"
    ep_dir.mkdir()
    dg = DocGardener()
    assert dg.find_stale_exec_plans(ep_dir) == []


def test_find_stale_exec_plans_missing_dir(tmp_path: Path):
    dg = DocGardener()
    assert dg.find_stale_exec_plans(tmp_path / "nonexistent") == []


def test_find_stale_exec_plans_no_tasks(tmp_path: Path):
    ep_dir = tmp_path / "exec-plans"
    ep_dir.mkdir()
    (ep_dir / "notasks.md").write_text("# No tasks\nJust prose.\n")
    dg = DocGardener()
    assert dg.find_stale_exec_plans(ep_dir) == []


# ---------------------------------------------------------------------------
# DocGardener.find_stale_docs
# ---------------------------------------------------------------------------


def test_find_stale_docs_detects_broken_ref(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("See `agents/missing.py` for details.\n")

    dg = DocGardener()
    stale = dg.find_stale_docs(docs_dir, tmp_path)
    assert stale == [docs_dir / "guide.md"]


def test_find_stale_docs_valid_ref_not_stale(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "supervisor.py").write_text("# exists\n")
    (docs_dir / "guide.md").write_text("See `agents/supervisor.py` for details.\n")

    dg = DocGardener()
    stale = dg.find_stale_docs(docs_dir, tmp_path)
    assert stale == []


def test_find_stale_docs_ignores_urls(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "See `https://example.com/file.md` or `http://x.com/a.py`.\n"
    )

    dg = DocGardener()
    assert dg.find_stale_docs(docs_dir, tmp_path) == []


def test_find_stale_docs_missing_dir(tmp_path: Path):
    dg = DocGardener()
    assert dg.find_stale_docs(tmp_path / "nonexistent", tmp_path) == []


def test_find_stale_docs_empty_dir(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    dg = DocGardener()
    assert dg.find_stale_docs(docs_dir, tmp_path) == []


# ---------------------------------------------------------------------------
# DocGardener.propose_updates
# ---------------------------------------------------------------------------


def test_propose_updates_all_tasks_done():
    dg = DocGardener()
    items = [{"path": "harness/exec-plans/done.md", "reason": "all_tasks_done"}]
    updates = dg.propose_updates(items)
    assert len(updates) == 1
    assert "Archive" in updates[0]["proposal"]
    assert "done.md" in updates[0]["proposal"]


def test_propose_updates_broken_refs():
    dg = DocGardener()
    items = [{"path": "docs/guide.md", "reason": "broken_refs"}]
    updates = dg.propose_updates(items)
    assert len(updates) == 1
    assert "Review" in updates[0]["proposal"]
    assert "missing files" in updates[0]["proposal"]


def test_propose_updates_unknown_reason():
    dg = DocGardener()
    items = [{"path": "docs/old.md", "reason": "unknown"}]
    updates = dg.propose_updates(items)
    assert "stale" in updates[0]["proposal"].lower()


def test_propose_updates_preserves_original_keys():
    dg = DocGardener()
    items = [{"path": "x.md", "reason": "all_tasks_done", "extra": "data"}]
    updates = dg.propose_updates(items)
    assert updates[0]["extra"] == "data"
    assert "proposal" in updates[0]


def test_propose_updates_empty():
    dg = DocGardener()
    assert dg.propose_updates([]) == []


# ---------------------------------------------------------------------------
# DocGardener.run
# ---------------------------------------------------------------------------


def test_run_returns_issues_and_next(tmp_path: Path):
    ep_dir = tmp_path / "harness" / "exec-plans"
    ep_dir.mkdir(parents=True)
    (ep_dir / "done.md").write_text("- [x] Only task\n")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    dg = DocGardener()
    state = {"issues": [], "quality_score": 90.0}
    result = dg.run(state, harness_root=tmp_path)

    assert result["next"] == "doc_gardener"
    assert len(result["issues"]) == 1
    assert "Archive" in result["issues"][0]


def test_run_appends_to_existing_issues(tmp_path: Path):
    ep_dir = tmp_path / "harness" / "exec-plans"
    ep_dir.mkdir(parents=True)
    (ep_dir / "done.md").write_text("- [x] Task\n")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    dg = DocGardener()
    state = {"issues": ["existing issue"], "quality_score": 90.0}
    result = dg.run(state, harness_root=tmp_path)

    assert "existing issue" in result["issues"]
    assert len(result["issues"]) == 2


def test_run_no_stale_items(tmp_path: Path):
    ep_dir = tmp_path / "harness" / "exec-plans"
    ep_dir.mkdir(parents=True)
    (ep_dir / "pending.md").write_text("- [ ] Task\n")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    dg = DocGardener()
    state = {"issues": [], "quality_score": 90.0}
    result = dg.run(state, harness_root=tmp_path)

    assert result["next"] == "doc_gardener"
    assert result["issues"] == []


def test_run_empty_state_issues_defaults_to_list(tmp_path: Path):
    (tmp_path / "harness" / "exec-plans").mkdir(parents=True)
    (tmp_path / "docs").mkdir()

    dg = DocGardener()
    result = dg.run({}, harness_root=tmp_path)
    assert isinstance(result["issues"], list)


# ---------------------------------------------------------------------------
# Integration: doc_gardener_node in the compiled graph
# ---------------------------------------------------------------------------


def test_doc_gardener_node_sets_next():
    from graph.compile import doc_gardener_node
    from graph.state import AgentState

    state: AgentState = {
        "spec_path": "specs/test.md",
        "spec_content": "",
        "spec_structure": {},
        "codebase": {},
        "plan": [],
        "test_results": [],
        "issues": [],
        "iteration": 0,
        "next": "",
        "checkpoint": {},
        "mcp_servers": [],
        "quality_score": 90.0,
        "invariants": [],
    }
    result = doc_gardener_node(state)
    assert result["next"] == "doc_gardener"
    assert "issues" in result
