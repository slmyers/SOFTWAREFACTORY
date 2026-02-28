"""Tests for tools/file_edits.py — unified diff editing pipeline (Issue #47)."""

from __future__ import annotations

import pytest

from tools.file_edits import DiffPreview, apply_unified_diff, diff_preview


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIMPLE_DIFF = """\
--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -1,3 +1,4 @@
 line one
-line two
+line TWO
+line two-b
 line three
"""

_NEW_FILE_DIFF = """\
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,3 @@
+# new_file.py
+def hello():
+    pass
"""

_MULTI_FILE_DIFF = """\
--- a/a.py
+++ b/a.py
@@ -1,2 +1,2 @@
-x = 1
+x = 2
 y = 3
--- a/b.py
+++ b/b.py
@@ -1,2 +1,2 @@
-foo = "old"
+foo = "new"
 bar = 0
"""


# ---------------------------------------------------------------------------
# apply_unified_diff — basic cases
# ---------------------------------------------------------------------------


def test_apply_unified_diff_modifies_file(tmp_path):
    """A simple one-hunk diff modifies the target file correctly."""
    (tmp_path / "pkg").mkdir()
    src = tmp_path / "pkg" / "mod.py"
    src.write_text("line one\nline two\nline three\n")

    results = apply_unified_diff(_SIMPLE_DIFF, tmp_path)

    assert "pkg/mod.py" in results
    assert results["pkg/mod.py"]["written"] is True
    assert src.read_text() == "line one\nline TWO\nline two-b\nline three\n"


def test_apply_unified_diff_creates_new_file(tmp_path):
    """Diff with /dev/null source creates a new file."""
    results = apply_unified_diff(_NEW_FILE_DIFF, tmp_path)

    assert "new_file.py" in results
    assert results["new_file.py"]["written"] is True
    assert (tmp_path / "new_file.py").read_text() == "# new_file.py\ndef hello():\n    pass\n"


def test_apply_unified_diff_multi_file(tmp_path):
    """A diff spanning two files updates both correctly."""
    (tmp_path / "a.py").write_text("x = 1\ny = 3\n")
    (tmp_path / "b.py").write_text('foo = "old"\nbar = 0\n')

    results = apply_unified_diff(_MULTI_FILE_DIFF, tmp_path)

    assert results["a.py"]["written"] is True
    assert results["b.py"]["written"] is True
    assert (tmp_path / "a.py").read_text() == "x = 2\ny = 3\n"
    assert (tmp_path / "b.py").read_text() == 'foo = "new"\nbar = 0\n'


def test_apply_unified_diff_dry_run(tmp_path):
    """dry_run=True returns results without writing files."""
    (tmp_path / "pkg").mkdir()
    src = tmp_path / "pkg" / "mod.py"
    original = "line one\nline two\nline three\n"
    src.write_text(original)

    results = apply_unified_diff(_SIMPLE_DIFF, tmp_path, dry_run=True)

    assert results["pkg/mod.py"]["written"] is False
    # File must NOT have been modified
    assert src.read_text() == original


def test_apply_unified_diff_path_escape_raises(tmp_path):
    """A diff targeting a path outside project_root raises ValueError."""
    evil_diff = """\
--- a/../outside.py
+++ b/../outside.py
@@ -1 +1 @@
-old
+new
"""
    with pytest.raises(ValueError, match="escapes project root"):
        apply_unified_diff(evil_diff, tmp_path)


def test_apply_unified_diff_empty_diff(tmp_path):
    """Garbage/empty input produces no changes and no exception."""
    results = apply_unified_diff("this is not a diff\n", tmp_path)
    assert results == {}


# ---------------------------------------------------------------------------
# diff_preview
# ---------------------------------------------------------------------------


def test_diff_preview_counts(tmp_path):
    """DiffPreview counts additions, deletions, hunks, files correctly."""
    preview = diff_preview(_SIMPLE_DIFF, tmp_path)

    assert isinstance(preview, DiffPreview)
    assert "pkg/mod.py" in preview.files_changed
    assert preview.additions == 2
    assert preview.deletions == 1
    assert preview.hunks == 1
    assert "1 file(s) changed" in preview.summary
    assert "+2" in preview.summary
    assert "1 hunk" in preview.summary


def test_diff_preview_multi_file(tmp_path):
    """DiffPreview handles multi-file diffs."""
    preview = diff_preview(_MULTI_FILE_DIFF, tmp_path)

    assert len(preview.files_changed) == 2
    assert preview.additions == 2
    assert preview.deletions == 2
    assert preview.hunks == 2
    assert "2 file(s) changed" in preview.summary


def test_diff_preview_new_file(tmp_path):
    """DiffPreview handles new-file diffs."""
    preview = diff_preview(_NEW_FILE_DIFF, tmp_path)

    assert "new_file.py" in preview.files_changed
    assert preview.additions == 3
    assert preview.deletions == 0


def test_diff_preview_path_escape_raises(tmp_path):
    """diff_preview raises ValueError for unsafe paths."""
    evil_diff = """\
--- a/../bad.py
+++ b/../bad.py
@@ -1 +1 @@
-x
+y
"""
    with pytest.raises(ValueError, match="escapes project root"):
        diff_preview(evil_diff, tmp_path)


def test_diff_preview_str(tmp_path):
    """str(DiffPreview) returns the summary string."""
    preview = diff_preview(_SIMPLE_DIFF, tmp_path)
    assert str(preview) == preview.summary
