"""Unified diff editing pipeline for SOFTWAREFACTORY (Issue #47).

Public API
----------
apply_unified_diff(path, diff_content, project_root)
    Apply a GNU unified diff to a file inside *project_root*.

DiffPreview
    Dataclass holding a human-readable preview of pending diff changes.

diff_preview(diff_content, project_root)
    Return a DiffPreview for display in the CLI / LangSmith trace.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from unidiff import PatchSet

from tools.filesystem import _atomic_write, _ensure_parent, _is_safe_path

__all__ = [
    "apply_unified_diff",
    "DiffPreview",
    "diff_preview",
]

# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------


def _validate_diff_paths(patch: PatchSet, root: Path) -> None:
    """Raise ValueError if any patch target path escapes *root*."""
    for patched_file in patch:
        rel = patched_file.path
        if not rel:
            continue
        target = root / rel
        if not _is_safe_path(root, target):
            raise ValueError(
                f"Diff contains path that escapes project root: {rel!r}"
            )


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------


def apply_unified_diff(
    diff_content: str,
    project_root: str | Path,
    *,
    dry_run: bool = False,
) -> Dict[str, Dict[str, object]]:
    """Apply a GNU unified diff inside *project_root*.

    Parameters
    ----------
    diff_content:
        Full text of a GNU unified diff (``--- a/...`` / ``+++ b/...`` format).
    project_root:
        Absolute path to the project directory.  Every path referenced in the
        diff must resolve to a location *inside* this directory.
    dry_run:
        When *True* parse and validate the diff but do **not** write any files.

    Returns
    -------
    dict
        Mapping of repo-relative path → ``{"new": <content>, "written": bool}``.

    Raises
    ------
    ValueError
        If the diff contains a path that escapes *project_root*.
    """
    root = Path(project_root)

    patch = PatchSet(diff_content.splitlines(keepends=True))

    # Safety: reject any path that escapes the project root
    _validate_diff_paths(patch, root)

    results: Dict[str, Dict[str, object]] = {}

    for patched_file in patch:
        rel_path = patched_file.path
        if not rel_path:
            continue

        # Reconstruct new file content from context + added lines
        new_lines: List[str] = []
        for hunk in patched_file:
            for line in hunk:
                if line.is_context or line.is_added:
                    new_lines.append(line.value)

        new_content = "".join(new_lines)
        if new_content and not new_content.endswith("\n"):
            new_content += "\n"

        results[rel_path] = {"new": new_content, "written": False}

    if not dry_run:
        for rel, info in results.items():
            target = root / rel
            _ensure_parent(target)
            _atomic_write(target, str(info["new"]))
            info["written"] = True

    return results


# ---------------------------------------------------------------------------
# Diff preview (for CLI output and LangSmith traces)
# ---------------------------------------------------------------------------


@dataclass
class DiffPreview:
    """Human-readable summary of a pending unified diff.

    Attributes
    ----------
    files_changed : list of repo-relative paths that will be modified.
    additions     : total number of added lines across all files.
    deletions     : total number of removed lines across all files.
    hunks         : total number of hunks.
    summary       : one-line text summary suitable for CLI / trace output.
    """

    files_changed: List[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    hunks: int = 0
    summary: str = ""

    def __str__(self) -> str:  # pragma: no cover
        return self.summary


def diff_preview(
    diff_content: str,
    project_root: str | Path,
) -> DiffPreview:
    """Parse *diff_content* and return a :class:`DiffPreview`.

    Parameters
    ----------
    diff_content:
        GNU unified diff text.
    project_root:
        Project root (used for safety validation only — no files are written).

    Raises
    ------
    ValueError
        If the diff contains unsafe paths.
    """
    root = Path(project_root)

    patch = PatchSet(diff_content.splitlines(keepends=True))

    _validate_diff_paths(patch, root)

    files_changed: List[str] = []
    additions = 0
    deletions = 0
    hunks = 0

    for patched_file in patch:
        rel = patched_file.path
        if not rel:
            continue
        files_changed.append(rel)
        for hunk in patched_file:
            hunks += 1
            for line in hunk:
                if line.is_added:
                    additions += 1
                elif line.is_removed:
                    deletions += 1

    n = len(files_changed)
    summary = (
        f"{n} file(s) changed: +{additions} −{deletions} lines across {hunks} hunk(s)"
    )
    return DiffPreview(
        files_changed=files_changed,
        additions=additions,
        deletions=deletions,
        hunks=hunks,
        summary=summary,
    )
