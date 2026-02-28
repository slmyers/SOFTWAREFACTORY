from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from unidiff import PatchSet

DEFAULT_PATTERNS = ["*.py", "*.md", "*.json"]


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
        # Use Path.is_relative_to when available to avoid false positives
        try:
            return target_res.is_relative_to(root_res)
        except AttributeError:
            try:
                target_res.relative_to(root_res)
                return True
            except Exception:
                return False
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
        patterns = DEFAULT_PATTERNS.copy()
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


# ---------------------------------------------------------------------------
# LangChain tools — for use with LangGraph ToolNode
# ---------------------------------------------------------------------------


@tool
def read_file(path: str, project_root: str) -> str:
    """Read and return the contents of a file inside *project_root*.

    Args:
        path: Path to the file, relative to *project_root* or absolute.
        project_root: Absolute path of the project directory.  The resolved
            *path* must reside inside this directory.

    Returns:
        The UTF-8 text content of the file.

    Raises:
        ValueError: If the resolved path escapes *project_root*.
        FileNotFoundError: If the file does not exist.
    """
    root = Path(project_root)
    target = (root / path) if not Path(path).is_absolute() else Path(path)
    if not _is_safe_path(root, target):
        raise ValueError(f"Path escapes project root: {path!r}")
    if not target.exists():
        raise FileNotFoundError(target)
    return target.read_text(encoding="utf-8")


@tool
def write_file(path: str, content: str, project_root: str) -> str:
    """Write *content* to a file inside *project_root* (atomic write).

    Creates any missing parent directories.  Existing files are overwritten.

    Args:
        path: Destination path, relative to *project_root* or absolute.
        content: UTF-8 text to write.
        project_root: Absolute path of the project directory.  The resolved
            *path* must reside inside this directory.

    Returns:
        A short confirmation message with the resolved file path.

    Raises:
        ValueError: If the resolved path escapes *project_root*.
    """
    root = Path(project_root)
    target = (root / path) if not Path(path).is_absolute() else Path(path)
    if not _is_safe_path(root, target):
        raise ValueError(f"Path escapes project root: {path!r}")
    _atomic_write(target, content)
    return f"wrote {target}"


@tool
def list_dir(path: str, project_root: str) -> List[str]:
    """Return a sorted list of entries inside *path* within *project_root*.

    Each entry is a POSIX-style path relative to *project_root*.  Files are
    returned as-is; directories are shown with a trailing ``/``.

    Args:
        path: Directory to list, relative to *project_root* or absolute.
            Pass ``"."`` (or ``""`` / ``project_root``) to list the root itself.
        project_root: Absolute path of the project directory.

    Returns:
        Sorted list of relative entry paths (directories end with ``/``).

    Raises:
        ValueError: If the resolved path escapes *project_root*.
        NotADirectoryError: If *path* is not a directory.
    """
    root = Path(project_root)
    if path in ("", "."):
        target = root
    else:
        target = (root / path) if not Path(path).is_absolute() else Path(path)
    if not _is_safe_path(root, target):
        raise ValueError(f"Path escapes project root: {path!r}")
    if not target.is_dir():
        raise NotADirectoryError(target)
    entries = []
    for entry in sorted(target.iterdir()):
        rel = entry.relative_to(root).as_posix()
        entries.append(rel + "/" if entry.is_dir() else rel)
    return entries


@tool
def grep(pattern: str, path: str, project_root: str, recursive: bool = True) -> List[str]:
    """Search files under *path* for lines matching *pattern* (regex).

    Args:
        pattern: Python ``re`` regular expression to search for.
        path: File or directory to search, relative to *project_root* or
            absolute.  Pass ``"."`` to search the entire project.
        project_root: Absolute path of the project directory.
        recursive: When *True* (default) and *path* is a directory, recurse
            into sub-directories.

    Returns:
        List of match strings in ``"<rel_path>:<lineno>:<line>"`` format.

    Raises:
        ValueError: If the resolved path escapes *project_root*.
    """
    root = Path(project_root)
    if path in ("", "."):
        target = root
    else:
        target = (root / path) if not Path(path).is_absolute() else Path(path)
    if not _is_safe_path(root, target):
        raise ValueError(f"Path escapes project root: {path!r}")

    compiled = re.compile(pattern)
    results: List[str] = []

    def _search_file(fp: Path) -> None:
        try:
            for lineno, line in enumerate(fp.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                if compiled.search(line):
                    rel = fp.relative_to(root).as_posix()
                    results.append(f"{rel}:{lineno}:{line}")
        except (OSError, IsADirectoryError):
            pass

    if target.is_file():
        _search_file(target)
    elif target.is_dir():
        iter_fn = target.rglob("*") if recursive else target.glob("*")
        for fp in sorted(iter_fn):
            if fp.is_file():
                _search_file(fp)

    return results


# Ordered list of all filesystem tools — bind to a LangGraph ToolNode
FILESYSTEM_TOOLS = [read_file, write_file, list_dir, grep]

# Ready-to-use LangGraph ToolNode for the filesystem tool suite
filesystem_tool_node = ToolNode(FILESYSTEM_TOOLS)
