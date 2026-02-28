"""DocGardener agent: keeps harness exec-plans and docs clean.

Runs after Supervisor. Finds stale exec-plans (all tasks complete) and docs
with broken file references, then proposes updates.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = ["DocGardener"]

# Matches markdown task checkboxes: "- [ ]" or "- [x]"
_TASK_RE = re.compile(r"^\s*-\s*\[( |x)\]", re.IGNORECASE | re.MULTILINE)

# Matches backtick-enclosed relative file references, e.g. `path/to/file.py`
_REF_RE = re.compile(r"`([^`]+\.[a-zA-Z]{1,10})`")


def _all_tasks_done(content: str) -> bool:
    """Return True if the content has at least one task and all are checked."""
    tasks = _TASK_RE.findall(content)
    return bool(tasks) and all(t.strip().lower() == "x" for t in tasks)


class DocGardener:
    """Finds stale exec-plans and docs, proposes updates.

    Methods
    -------
    find_stale_exec_plans(exec_plans_dir)
        Returns list of Path objects for exec-plan files where all tasks are done.
    find_stale_docs(docs_dir, harness_root)
        Returns list of Path objects for doc files with broken file references.
    propose_updates(stale_items)
        Returns a list of proposed update dicts for stale items.
    run(state, harness_root)
        Runs all checks and returns a state-update dict.
    """

    def find_stale_exec_plans(
        self, exec_plans_dir: Optional[Path] = None
    ) -> List[Path]:
        """Return exec-plan files where every task checkbox is checked.

        Parameters
        ----------
        exec_plans_dir:
            Directory to scan for ``*.md`` exec-plan files.
            Defaults to ``harness/exec-plans`` relative to cwd.
        """
        d = Path(exec_plans_dir) if exec_plans_dir is not None else Path("harness/exec-plans")
        stale: List[Path] = []
        if not d.is_dir():
            return stale
        for p in sorted(d.glob("*.md")):
            try:
                content = p.read_text(encoding="utf-8")
            except OSError:
                continue
            if _all_tasks_done(content):
                stale.append(p)
        return stale

    def find_stale_docs(
        self,
        docs_dir: Optional[Path] = None,
        harness_root: Optional[Path] = None,
    ) -> List[Path]:
        """Return doc files that contain backtick references to missing files.

        Parameters
        ----------
        docs_dir:
            Directory to scan for ``*.md`` doc files.
            Defaults to ``docs`` relative to cwd.
        harness_root:
            Root directory used to resolve relative file references.
            Defaults to cwd.
        """
        d = Path(docs_dir) if docs_dir is not None else Path("docs")
        root = Path(harness_root) if harness_root is not None else Path(".")
        stale: List[Path] = []
        if not d.is_dir():
            return stale
        for p in sorted(d.rglob("*.md")):
            try:
                content = p.read_text(encoding="utf-8")
            except OSError:
                continue
            for match in _REF_RE.finditer(content):
                ref = match.group(1)
                # Skip absolute paths and URLs
                if ref.startswith(("/", "http://", "https://")):
                    continue
                if not (root / ref).exists():
                    stale.append(p)
                    break
        return stale

    def propose_updates(
        self, stale_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate human-readable proposals for stale items.

        Parameters
        ----------
        stale_items:
            List of dicts with keys ``path`` and ``reason``.

        Returns
        -------
        List of dicts with the original keys plus a ``proposal`` string.
        """
        updates: List[Dict[str, Any]] = []
        for item in stale_items:
            path = item.get("path", "")
            reason = item.get("reason", "stale")
            if reason == "all_tasks_done":
                proposal = f"Archive `{path}` — all tasks are complete."
            elif reason == "broken_refs":
                proposal = f"Review `{path}` — contains references to missing files."
            else:
                proposal = f"Review `{path}` — may be stale."
            updates.append({**item, "proposal": proposal})
        return updates

    def run(
        self,
        state: Dict[str, Any],
        harness_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Run all staleness checks and return a state-update dict.

        Parameters
        ----------
        state:
            Current AgentState dict (or compatible mapping).
        harness_root:
            Root directory for the harness. Defaults to ``Path('.')``.

        Returns
        -------
        Dict with ``issues`` (existing list extended with new proposals) and
        ``next`` set to ``'doc_gardener'``.
        """
        root = Path(harness_root) if harness_root is not None else Path(".")
        exec_plans_dir = root / "harness" / "exec-plans"
        docs_dir = root / "docs"

        stale_plans = self.find_stale_exec_plans(exec_plans_dir)
        stale_docs = self.find_stale_docs(docs_dir, root)

        stale_items: List[Dict[str, Any]] = []
        for p in stale_plans:
            stale_items.append({"path": str(p), "reason": "all_tasks_done"})
        for p in stale_docs:
            stale_items.append({"path": str(p), "reason": "broken_refs"})

        updates = self.propose_updates(stale_items)

        existing_issues: List[str] = list(state.get("issues") or [])
        for u in updates:
            existing_issues.append(u["proposal"])

        return {
            "issues": existing_issues,
            "next": "doc_gardener",
        }
