"""Tests for agents/spec_parser.py — Issue #11: SpecParser agent.

Covers:
- _parse_spec() correctly extracts title, sections, tasks, todos, ambiguities
- spec_parser_node() reads spec_path and populates state correctly
- spec_parser_node() handles missing spec files gracefully
- spec_parser_node() uses pre-loaded spec_content when available
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.spec_parser import _parse_spec, spec_parser_node
from graph.state import AgentState

# ---------------------------------------------------------------------------
# Minimal AgentState helper
# ---------------------------------------------------------------------------

_EMPTY_STATE: AgentState = {
    "spec_path": "",
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
    "quality_score": 0.0,
    "invariants": [],
}


def _state(**overrides) -> AgentState:
    base = dict(_EMPTY_STATE)
    base.update(overrides)
    return base  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# _parse_spec — unit tests
# ---------------------------------------------------------------------------

SAMPLE_SPEC = """\
# My Project Spec

## Goals

Build a great system.

## Tasks
- [ ] Write unit tests
- [x] Set up CI
- [ ] Document API  TODO: needs more detail

## Open Questions

Some things are TBD.
This section is unclear.
"""


def test_parse_title():
    result = _parse_spec(SAMPLE_SPEC)
    assert result["title"] == "My Project Spec"


def test_parse_sections():
    result = _parse_spec(SAMPLE_SPEC)
    headings = [s["heading"] for s in result["sections"]]
    assert "My Project Spec" in headings
    assert "Goals" in headings
    assert "Tasks" in headings
    assert "Open Questions" in headings


def test_parse_section_levels():
    result = _parse_spec(SAMPLE_SPEC)
    level_map = {s["heading"]: s["level"] for s in result["sections"]}
    assert level_map["My Project Spec"] == 1
    assert level_map["Goals"] == 2
    assert level_map["Tasks"] == 2


def test_parse_tasks_all():
    """All checkbox items (checked and unchecked) should appear in tasks."""
    result = _parse_spec(SAMPLE_SPEC)
    assert "Write unit tests" in result["tasks"]
    assert "Set up CI" in result["tasks"]


def test_parse_todos_unchecked_only():
    """Only unchecked [ ] items and TODO-keyword lines should be in todos."""
    result = _parse_spec(SAMPLE_SPEC)
    # Unchecked tasks
    assert "Write unit tests" in result["todos"]
    # Checked task should NOT be a todo
    assert "Set up CI" not in result["todos"]


def test_parse_todos_inline_keyword():
    """Lines containing TODO keyword (not checkbox) are detected as todos."""
    spec = "# Spec\n\n## Work\n\nFix the bug. TODO: revisit later\n"
    result = _parse_spec(spec)
    assert any("TODO" in t for t in result["todos"])


def test_parse_ambiguities_tbd():
    result = _parse_spec(SAMPLE_SPEC)
    assert any("TBD" in a for a in result["ambiguities"])


def test_parse_ambiguities_unclear():
    result = _parse_spec(SAMPLE_SPEC)
    assert any("unclear" in a.lower() for a in result["ambiguities"])


def test_parse_empty_content():
    result = _parse_spec("")
    assert result["title"] == ""
    assert result["sections"] == []
    assert result["tasks"] == []
    assert result["todos"] == []
    assert result["ambiguities"] == []


def test_parse_no_todos_or_ambiguities():
    spec = "# Clean Spec\n\n## Section\n\nAll clear.\n"
    result = _parse_spec(spec)
    assert result["todos"] == []
    assert result["ambiguities"] == []


# ---------------------------------------------------------------------------
# spec_parser_node — integration-level tests
# ---------------------------------------------------------------------------


def test_node_populates_spec_structure_from_content():
    """Node uses pre-loaded spec_content when provided."""
    state = _state(spec_content=SAMPLE_SPEC)
    result = spec_parser_node(state)

    assert "spec_structure" in result
    struct = result["spec_structure"]
    assert struct["title"] == "My Project Spec"
    assert len(struct["sections"]) > 0
    assert len(struct["tasks"]) > 0


def test_node_reads_spec_file(tmp_path: Path):
    """Node reads spec_path when spec_content is empty."""
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(SAMPLE_SPEC)

    state = _state(spec_path=str(spec_file))
    result = spec_parser_node(state)

    assert result["spec_content"] == SAMPLE_SPEC
    assert result["spec_structure"]["title"] == "My Project Spec"


def test_node_handles_missing_file_gracefully():
    """Node does not raise if spec_path points to a non-existent file."""
    state = _state(spec_path="/nonexistent/path/spec.md")
    result = spec_parser_node(state)

    assert result["spec_content"] == ""
    assert result["spec_structure"]["sections"] == []
    assert result["spec_structure"]["todos"] == []


def test_node_returns_next_spec_parser():
    """Node must set state['next'] = 'spec_parser' for the graph router."""
    state = _state(spec_content=SAMPLE_SPEC)
    result = spec_parser_node(state)
    assert result["next"] == "spec_parser"


def test_node_populates_todos():
    """Node surfaces todos in spec_structure."""
    state = _state(spec_content=SAMPLE_SPEC)
    result = spec_parser_node(state)
    assert len(result["spec_structure"]["todos"]) > 0


def test_node_populates_ambiguities():
    """Node surfaces ambiguities in spec_structure."""
    state = _state(spec_content=SAMPLE_SPEC)
    result = spec_parser_node(state)
    assert len(result["spec_structure"]["ambiguities"]) > 0


def test_node_prefers_existing_content_over_file(tmp_path: Path):
    """When spec_content is already set, the file is NOT read."""
    # Create a file with different content
    spec_file = tmp_path / "spec.md"
    spec_file.write_text("# File Content\n")

    inline_content = "# Inline Content\n"
    state = _state(spec_path=str(spec_file), spec_content=inline_content)
    result = spec_parser_node(state)

    assert result["spec_structure"]["title"] == "Inline Content"
