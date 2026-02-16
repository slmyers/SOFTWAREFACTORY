import pytest

from tools.filesystem import load_codebase, load_spec, save_codebase, save_spec


def test_save_and_load_spec(tmp_path):
    p = tmp_path / "specs"
    target = p / "spec.md"
    content = "# Hello\n\nThis is a spec.\n"
    save_spec(target, content)
    out = load_spec(target)
    assert out == content


def test_load_codebase_and_save_mapping(tmp_path):
    root = tmp_path / "repo"
    (root / "a").mkdir(parents=True)
    f1 = root / "a" / "one.py"
    f2 = root / "two.md"
    f1.write_text("print(1)\n")
    f2.write_text("# two\n")

    files = load_codebase(root)
    assert "a/one.py" in files
    assert "two.md" in files

    # modify and save
    files["a/one.py"] = "print(2)\n"
    summary = save_codebase(files, root, dry_run=True)
    assert summary["a/one.py"]["written"] is False
    summary2 = save_codebase({"a/one.py": "print(2)\n"}, root)
    assert summary2["a/one.py"]["written"] is True
    assert (root / "a" / "one.py").read_text() == "print(2)\n"


def test_save_codebase_unified_diff(tmp_path):
    root = tmp_path / "repo"
    (root / "pkg").mkdir(parents=True)
    file_path = root / "pkg" / "mod.py"
    file_path.write_text("old line\n")

    diff = """--- a/pkg/mod.py
+++ b/pkg/mod.py
new line 1
new line 2
"""
    summary = save_codebase(diff, root)
    assert "pkg/mod.py" in summary
    assert summary["pkg/mod.py"]["written"] is True
    assert file_path.read_text() == "new line 1\nnew line 2\n"


def test_path_safety(tmp_path):
    root = tmp_path / "repo"
    (root).mkdir()
    # attempt to write outside repo
    with pytest.raises(ValueError):
        save_codebase({"../outside.txt": "bad"}, root)
