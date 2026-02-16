from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _atomic_write(path: Path, data: str) -> None:
    _ensure_parent(path)
    dirpath = path.parent
    fd, tmp = tempfile.mkstemp(prefix=".sf_tmp_", dir=str(dirpath))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        tmp_path = Path(tmp)
        tmp_path.replace(path)
    finally:
        if Path(tmp).exists():
            try:
                Path(tmp).unlink()
            except Exception:
                pass


def _is_safe_path(root: Path, target: Path) -> bool:
    try:
        root_res = root.resolve()
        target_res = target.resolve()
        return str(target_res).startswith(str(root_res))
    except Exception:
        return False


def load_spec(path: Union[str, Path]) -> str:
    """Load a spec (markdown) file and return its content.

    Raises FileNotFoundError if missing.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    return p.read_text(encoding="utf-8")


def save_spec(path: Union[str, Path], content: str, *, atomic: bool = True) -> None:
    """Save spec content to `path`. By default, writes atomically."""
    p = Path(path)
    if atomic:
        _atomic_write(p, content)
    else:
        _ensure_parent(p)
        p.write_text(content, encoding="utf-8")


def load_codebase(
    root: Union[str, Path], patterns: Optional[List[str]] = None
) -> Dict[str, str]:
    """Walk `root` and return a mapping of repo-relative path -> file content.

    Default patterns: ['*.py','*.md','*.json']
    """
    r = Path(root)
    if patterns is None:
        patterns = ["*.py", "*.md", "*.json"]
    files: Dict[str, str] = {}
    for pattern in patterns:
        for p in r.rglob(pattern):
            if p.is_file():
                rel = p.relative_to(r).as_posix()
                files[rel] = p.read_text(encoding="utf-8")
    return files


def _apply_simple_unified_diff(
    root: Path, diff_text: str, write: bool = True
) -> Dict[str, Dict[str, str]]:
    """Apply a unified diff using the `unidiff` parser.

    Returns a mapping of repo-relative path -> {"new": content, "written": True/False}.
    This implementation relies on `unidiff.PatchSet` to parse hunks and
    reconstruct the new file content from context and added lines.
    """
    results: Dict[str, Dict[str, str]] = {}
    try:
        from unidiff import PatchSet
    except Exception as e:
        raise ImportError(
            "unidiff is required to apply unified diffs. Install with 'pip install unidiff'"
        ) from e

    # PatchSet expects an iterable of lines including line endings
    patch = PatchSet(diff_text.splitlines(keepends=True))

    for patched_file in patch:
        rel_path = patched_file.path
        if not rel_path:
            continue
        new_lines: List[str] = []
        for hunk in patched_file:
            for line in hunk:
                # include context and added lines to reconstruct new file
                if line.is_context or line.is_added:
                    new_lines.append(line.value)
        new_content = "".join(new_lines)
        if new_content and not new_content.endswith("\n"):
            new_content = new_content + "\n"
        results[rel_path] = {"new": new_content}

    # write files (unless parse-only)
    for rel, info in results.items():
        target = root / rel
        if not _is_safe_path(root, target):
            raise ValueError(f"Unsafe path in diff: {rel}")
        if write:
            _ensure_parent(target)
            _atomic_write(target, info["new"])
            info["written"] = True
        else:
            info["written"] = False

    return results


def save_codebase(
    codebase: Union[Dict[str, str], str],
    root: Union[str, Path],
    *,
    atomic: bool = True,
    dry_run: bool = False,
) -> Dict[str, Dict[str, str]]:
    """Save a codebase mapping or apply a unified diff under `root`.

    - If `codebase` is a dict: writes each key (repo-relative path) to disk.
    - If `codebase` is a str: treated as a unified diff and a conservative
      diff applier is used (see `_apply_simple_unified_diff`).

    Returns a summary mapping of path -> {new:..., written: True/False}
    When `dry_run=True`, no files are written; the function returns the planned changes.
    """
    r = Path(root)
    summary: Dict[str, Dict[str, str]] = {}
    if isinstance(codebase, str):
        # unified diff
        return _apply_simple_unified_diff(r, codebase, write=not dry_run)

    # mapping path -> content
    for rel, content in codebase.items():
        target = r / rel
        if not _is_safe_path(r, target):
            raise ValueError(f"Unsafe target path: {rel}")
        if dry_run:
            summary[rel] = {"new": content, "written": False}
            continue
        if atomic:
            _atomic_write(target, content)
        else:
            _ensure_parent(target)
            target.write_text(content, encoding="utf-8")
        summary[rel] = {"new": content, "written": True}
    return summary
