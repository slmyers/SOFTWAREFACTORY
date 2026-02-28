import pytest

from tools.filesystem import (
    FILESYSTEM_TOOLS,
    filesystem_tool_node,
    grep,
    list_dir,
    load_codebase,
    load_spec,
    read_file,
    save_codebase,
    save_spec,
    write_file,
)


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
@@ -1,1 +1,2 @@
-old line
+new line 1
+new line 2
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


# ---------------------------------------------------------------------------
# Tests for the four LangChain @tool functions
# ---------------------------------------------------------------------------


def test_read_file_success(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "hello.txt").write_text("hello world\n")
    result = read_file.invoke({"path": "hello.txt", "project_root": str(root)})
    assert result == "hello world\n"


def test_read_file_path_escape(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    with pytest.raises(ValueError, match="escapes"):
        read_file.invoke({"path": "../outside.txt", "project_root": str(root)})


def test_read_file_not_found(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    with pytest.raises(FileNotFoundError):
        read_file.invoke({"path": "missing.txt", "project_root": str(root)})


def test_write_file_success(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    result = write_file.invoke({"path": "sub/out.txt", "content": "data\n", "project_root": str(root)})
    assert "out.txt" in result
    assert (root / "sub" / "out.txt").read_text() == "data\n"


def test_write_file_path_escape(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    with pytest.raises(ValueError, match="escapes"):
        write_file.invoke({"path": "../evil.txt", "content": "bad", "project_root": str(root)})


def test_list_dir_success(tmp_path):
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "mod.py").write_text("x=1\n")
    (root / "readme.md").write_text("# hi\n")
    entries = list_dir.invoke({"path": ".", "project_root": str(root)})
    assert "pkg/" in entries
    assert "readme.md" in entries


def test_list_dir_subdir(tmp_path):
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("")
    entries = list_dir.invoke({"path": "src", "project_root": str(root)})
    assert "src/a.py" in entries


def test_list_dir_path_escape(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    with pytest.raises(ValueError, match="escapes"):
        list_dir.invoke({"path": "../other", "project_root": str(root)})


def test_grep_finds_matches(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "code.py").write_text("def foo():\n    return 42\n")
    matches = grep.invoke({"pattern": r"def \w+", "path": ".", "project_root": str(root)})
    assert any("code.py" in m and "def foo" in m for m in matches)


def test_grep_no_matches(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "code.py").write_text("x = 1\n")
    matches = grep.invoke({"pattern": "NOTPRESENT", "path": ".", "project_root": str(root)})
    assert matches == []


def test_grep_single_file(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "notes.txt").write_text("line one\nfoo bar\nline three\n")
    matches = grep.invoke({"pattern": "foo", "path": "notes.txt", "project_root": str(root)})
    assert len(matches) == 1
    assert "notes.txt:2:foo bar" in matches[0]


def test_grep_path_escape(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    with pytest.raises(ValueError, match="escapes"):
        grep.invoke({"pattern": "x", "path": "../../etc", "project_root": str(root)})


def test_filesystem_tools_list():
    names = [t.name for t in FILESYSTEM_TOOLS]
    assert "read_file" in names
    assert "write_file" in names
    assert "list_dir" in names
    assert "grep" in names


def test_filesystem_tool_node_is_tool_node():
    from langgraph.prebuilt import ToolNode
    assert isinstance(filesystem_tool_node, ToolNode)
