"""SpecParser agent: reads and structures spec.md (Issue #11).

Reads the spec file referenced by ``state["spec_path"]``, parses its Markdown
content into a structured dict, and detects TODO items and ambiguities.

Exported
--------
spec_parser_node : LangGraph-compatible node function.
_parse_spec      : Pure parsing helper (importable for tests).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from graph.state import AgentState

__all__ = ["spec_parser_node", "_parse_spec"]

# Patterns for ambiguity detection
_AMBIGUITY_RE = re.compile(r"\b(TBD|unclear|ambiguous)\b", re.IGNORECASE)
# Standalone TODO marker (not part of a checkbox line)
_TODO_RE = re.compile(r"\bTODO\b", re.IGNORECASE)
# Markdown task-list checkbox: "- [ ] text" or "- [x] text"
_CHECKBOX_RE = re.compile(r"^\s*-\s+\[([ xX])\]\s+(.*)")


def _parse_spec(content: str) -> Dict[str, Any]:
    """Parse Markdown spec *content* into a structured dict.

    Returns
    -------
    dict with keys:
        title       – first H1 heading text (or "")
        sections    – list of {"heading": str, "level": int, "content": str}
        tasks       – all task-list items (checked and unchecked)
        todos       – unchecked task items + lines containing TODO keyword
        ambiguities – lines containing TBD / unclear / ambiguous
    """
    lines = content.splitlines()

    title: str = ""
    sections: List[Dict[str, Any]] = []
    tasks: List[str] = []
    todos: List[str] = []
    ambiguities: List[str] = []

    current_section: Dict[str, Any] | None = None
    current_content: List[str] = []

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            # Flush previous section
            if current_section is not None:
                current_section["content"] = "\n".join(current_content).strip()
                sections.append(current_section)
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            if level == 1 and not title:
                title = heading_text
            current_section = {"heading": heading_text, "level": level, "content": ""}
            current_content = []
        else:
            if current_section is not None:
                current_content.append(line)

            checkbox_match = _CHECKBOX_RE.match(line)
            if checkbox_match:
                checked, task_text = checkbox_match.group(1), checkbox_match.group(2).strip()
                tasks.append(task_text)
                if checked == " ":
                    todos.append(task_text)
            elif _TODO_RE.search(line):
                todos.append(line.strip())

            if _AMBIGUITY_RE.search(line):
                ambiguities.append(line.strip())

    # Flush last section
    if current_section is not None:
        current_section["content"] = "\n".join(current_content).strip()
        sections.append(current_section)

    return {
        "title": title,
        "sections": sections,
        "tasks": tasks,
        "todos": todos,
        "ambiguities": ambiguities,
    }


def spec_parser_node(state: AgentState) -> dict:
    """LangGraph node: read spec_path, parse content, populate spec_structure.

    Reads the file at ``state["spec_path"]`` (unless ``state["spec_content"]``
    is already populated).  Silently handles missing files so the graph can
    proceed even in environments where the spec file is not present.

    Returns a partial-state dict that LangGraph merges into the running state.
    """
    spec_path = state.get("spec_path", "")
    content: str = state.get("spec_content", "") or ""

    if not content and spec_path:
        try:
            content = Path(spec_path).read_text()
        except (FileNotFoundError, OSError):
            content = ""

    spec_structure = _parse_spec(content) if content else {
        "title": "",
        "sections": [],
        "tasks": [],
        "todos": [],
        "ambiguities": [],
    }

    return {
        "spec_content": content,
        "spec_structure": spec_structure,
        # Set next to this node's own name so the Supervisor knows who just ran
        # (matches the pipeline convention used by all agent nodes).
        "next": "spec_parser",
    }
