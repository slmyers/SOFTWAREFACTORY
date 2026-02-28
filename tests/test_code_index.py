"""Tests for tools/code_index.py.

Heavy paths that require a real embedding API or a running ChromaDB instance
are exercised with monkeypatching so the suite runs fully offline.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tools.code_index import (
    CODE_INDEX_TOOLS,
    chunk_by_lines,
    chunk_file,
    chunk_python_file,
    code_index_tool_node,
    codebase_search,
    index_codebase,
)


# ---------------------------------------------------------------------------
# Chunking – Python AST
# ---------------------------------------------------------------------------


def test_chunk_python_functions():
    source = "def foo():\n    return 1\n\ndef bar():\n    return 2\n"
    chunks = chunk_python_file("mod.py", source)
    names = [c["name"] for c in chunks]
    assert "foo" in names
    assert "bar" in names
    assert all(c["kind"] in ("FunctionDef", "AsyncFunctionDef", "ClassDef") for c in chunks)


def test_chunk_python_class():
    source = "class MyClass:\n    def method(self):\n        pass\n"
    chunks = chunk_python_file("cls.py", source)
    kinds = {c["kind"] for c in chunks}
    assert "ClassDef" in kinds


def test_chunk_python_invalid_syntax_falls_back():
    source = "def broken syntax!!!\n"
    chunks = chunk_python_file("bad.py", source)
    # Falls back to line-block chunks
    assert len(chunks) >= 1
    assert chunks[0]["kind"] == "block"


def test_chunk_python_empty_file():
    chunks = chunk_python_file("empty.py", "")
    assert chunks == []


def testchunk_by_lines_basic():
    text = "\n".join(f"line {i}" for i in range(10)) + "\n"
    chunks = chunk_by_lines("file.txt", text, chunk_size=5)
    # Two chunks: lines 1-5 and lines 6-10
    assert len(chunks) == 2
    assert chunks[0]["start_line"] == 1
    assert chunks[1]["start_line"] == 6


def testchunk_by_lines_single_chunk():
    text = "one line\n"
    chunks = chunk_by_lines("f.txt", text)
    assert len(chunks) == 1


def testchunk_by_lines_empty():
    chunks = chunk_by_lines("f.txt", "")
    assert chunks == []


def test_chunk_file_dispatches_python():
    source = "def f():\n    pass\n"
    chunks = chunk_file("main.py", source)
    assert chunks[0]["kind"] in ("FunctionDef", "AsyncFunctionDef", "ClassDef", "block")


def test_chunk_file_dispatches_non_python():
    text = "# heading\n\nsome content\n"
    chunks = chunk_file("README.md", text)
    assert len(chunks) >= 1
    assert chunks[0]["kind"] == "block"


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def test_code_index_tools_list():
    names = [t.name for t in CODE_INDEX_TOOLS]
    assert "codebase_search" in names


def test_code_index_tool_node_is_tool_node():
    from langgraph.prebuilt import ToolNode

    assert isinstance(code_index_tool_node, ToolNode)


# ---------------------------------------------------------------------------
# index_codebase – mocked embeddings + ChromaDB
# ---------------------------------------------------------------------------


def _make_fake_collection():
    col = MagicMock()
    col.count.return_value = 0
    return col


def test_index_codebase_returns_chunk_count(tmp_path):
    """index_codebase should upsert chunks and return a positive count."""
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "auth.py").write_text(
        "def login(user, pw):\n    pass\n\ndef logout(user):\n    pass\n"
    )

    fake_col = _make_fake_collection()

    def fake_embed(texts):
        return [[0.1] * 5 for _ in texts]

    with patch("tools.code_index._embed_texts", side_effect=fake_embed), patch(
        "tools.code_index._get_collection", return_value=fake_col
    ):
        count = index_codebase(str(root))

    assert count > 0
    assert fake_col.upsert.called


def test_index_codebase_empty_root(tmp_path):
    """An empty project root should return 0 without error."""
    root = tmp_path / "empty"
    root.mkdir()

    with patch("tools.code_index._embed_texts", return_value=[]), patch(
        "tools.code_index._get_collection", return_value=_make_fake_collection()
    ):
        count = index_codebase(str(root))

    assert count == 0


# ---------------------------------------------------------------------------
# codebase_search – mocked embeddings + ChromaDB
# ---------------------------------------------------------------------------


def _make_search_collection(docs, metadatas, distances):
    col = MagicMock()
    col.count.return_value = len(docs)
    col.query.return_value = {
        "documents": [docs],
        "metadatas": [metadatas],
        "distances": [distances],
    }
    return col


def test_codebase_search_returns_results(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()

    meta = {"path": "auth.py", "start_line": 1, "end_line": 3, "kind": "FunctionDef", "name": "login"}
    col = _make_search_collection(
        docs=["def login(user, pw):\n    pass\n"],
        metadatas=[meta],
        distances=[0.1],
    )

    with patch("tools.code_index._embed_texts", return_value=[[0.1] * 5]), patch(
        "tools.code_index._get_collection", return_value=col
    ):
        results = codebase_search.invoke(
            {"query": "login auth", "project_root": str(root)}
        )

    assert len(results) == 1
    assert results[0]["path"] == "auth.py"
    assert "score" in results[0]
    assert "text" in results[0]


def test_codebase_search_keyword_boost(tmp_path):
    """Results containing query terms should receive a score boost."""
    root = tmp_path / "proj"
    root.mkdir()

    metas = [
        {"path": "a.py", "start_line": 1, "end_line": 2, "kind": "FunctionDef", "name": "unrelated"},
        {"path": "b.py", "start_line": 1, "end_line": 2, "kind": "FunctionDef", "name": "auth_token"},
    ]
    docs = ["def unrelated():\n    pass\n", "def auth_token():\n    pass\n"]
    distances = [0.05, 0.20]  # b.py is semantically further away

    col = _make_search_collection(docs, metas, distances)

    with patch("tools.code_index._embed_texts", return_value=[[0.1] * 5]), patch(
        "tools.code_index._get_collection", return_value=col
    ):
        results = codebase_search.invoke(
            {"query": "auth token", "project_root": str(root), "n_results": 2}
        )

    # b.py should rank higher after keyword boost despite lower semantic score
    assert results[0]["path"] == "b.py"


def test_codebase_search_empty_index(tmp_path):
    """Search on an empty index should return an empty list without error."""
    root = tmp_path / "proj"
    root.mkdir()

    col = MagicMock()
    col.count.return_value = 0

    with patch("tools.code_index._get_collection", return_value=col):
        results = codebase_search.invoke(
            {"query": "anything", "project_root": str(root)}
        )

    assert results == []


def test_codebase_search_embedding_failure_returns_empty(tmp_path):
    """When embeddings fail, search should return an empty list gracefully."""
    root = tmp_path / "proj"
    root.mkdir()

    col = MagicMock()
    col.count.return_value = 5
    col.query.side_effect = RuntimeError("API down")

    with patch("tools.code_index._embed_texts", side_effect=RuntimeError("API down")), patch(
        "tools.code_index._get_collection", return_value=col
    ):
        results = codebase_search.invoke(
            {"query": "auth", "project_root": str(root)}
        )

    assert results == []


# ---------------------------------------------------------------------------
# MCP registry integration
# ---------------------------------------------------------------------------


def test_mcp_code_index_registered():
    """code-index server should appear in the MCP registry."""
    from mcp.client import _REGISTRY

    assert "code-index" in _REGISTRY
    assert _REGISTRY["code-index"].startswith("http")
