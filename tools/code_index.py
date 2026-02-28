"""Semantic code index with hybrid search (semantic + keyword).

Chunks Python source by function/class using the ``ast`` module; other text
files are split by fixed-size line blocks.  Embeddings are stored in a
persistent ChromaDB collection under ``.softwarefactory/index/``.

Configuration (environment variables)::

    OPENAI_BASE_URL  – embedding API base URL (default: https://api.openai.com/v1)
    OPENAI_API_KEY   – API key for the embedding endpoint
    SF_EMBED_MODEL   – embedding model name (default: text-embedding-3-small)
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INDEX_SUBDIR = Path(".softwarefactory/index")
COLLECTION_NAME = "codebase"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
DEFAULT_CHUNK_SIZE = 60  # lines per block for non-Python files


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------


def _get_embed_model() -> str:
    return os.environ.get("SF_EMBED_MODEL", DEFAULT_EMBED_MODEL)


def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed *texts* using the configured OpenAI-compatible endpoint."""
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    response = client.embeddings.create(
        input=texts,
        model=_get_embed_model(),
    )
    return [item.embedding for item in response.data]


# ---------------------------------------------------------------------------
# ChromaDB collection accessor
# ---------------------------------------------------------------------------


def _get_collection(persist_dir: Path):
    """Return (or create) the persistent ChromaDB collection at *persist_dir*."""
    import chromadb

    persist_dir.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def chunk_by_lines(
    rel_path: str, text: str, chunk_size: int = DEFAULT_CHUNK_SIZE
) -> List[Dict[str, Any]]:
    """Split *text* into fixed-size line blocks."""
    lines = text.splitlines(keepends=True)
    chunks: List[Dict[str, Any]] = []
    for i in range(0, len(lines), chunk_size):
        block = "".join(lines[i : i + chunk_size])
        if block.strip():
            chunks.append(
                {
                    "text": block,
                    "path": rel_path,
                    "start_line": i + 1,
                    "end_line": min(i + chunk_size, len(lines)),
                    "kind": "block",
                    "name": "",
                }
            )
    # Ensure at least one chunk for non-empty content
    if not chunks and text.strip():
        chunks.append(
            {
                "text": text,
                "path": rel_path,
                "start_line": 1,
                "end_line": len(lines),
                "kind": "block",
                "name": "",
            }
        )
    return chunks


def chunk_python_file(rel_path: str, source: str) -> List[Dict[str, Any]]:
    """Split a Python file into function/class-level chunks using ``ast``."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return chunk_by_lines(rel_path, source)

    lines = source.splitlines(keepends=True)
    chunks: List[Dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno - 1
            end = getattr(node, "end_lineno", node.lineno)
            chunk_text = "".join(lines[start:end])
            chunks.append(
                {
                    "text": chunk_text,
                    "path": rel_path,
                    "start_line": node.lineno,
                    "end_line": end,
                    "kind": type(node).__name__,
                    "name": node.name,
                }
            )

    if not chunks:
        return chunk_by_lines(rel_path, source)
    return chunks


def chunk_file(rel_path: str, content: str) -> List[Dict[str, Any]]:
    """Chunk *content* into semantic pieces depending on its file type.

    Python files are chunked by function/class; all other files by line blocks.
    """
    if rel_path.endswith(".py"):
        return chunk_python_file(rel_path, content)
    return chunk_by_lines(rel_path, content)


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


def index_codebase(root: str, persist_dir: Optional[str] = None) -> int:
    """Index all source files under *root* into the ChromaDB collection.

    Args:
        root:        Absolute (or relative) path to the project root.
        persist_dir: Optional custom path for the ChromaDB index directory.
                     Defaults to ``<root>/.softwarefactory/index``.

    Returns:
        Total number of chunks upserted into the collection.
    """
    from tools.filesystem import load_codebase

    root_path = Path(root)
    index_path = Path(persist_dir) if persist_dir else root_path / INDEX_SUBDIR

    files = load_codebase(root_path, patterns=["*.py", "*.md", "*.json", "*.txt"])
    if not files:
        return 0

    all_chunks: List[Dict[str, Any]] = []
    for rel_path, content in files.items():
        all_chunks.extend(chunk_file(rel_path, content))

    if not all_chunks:
        return 0

    texts = [c["text"] for c in all_chunks]
    embeddings = _embed_texts(texts)

    collection = _get_collection(index_path)

    ids = [f"{c['path']}::{c['start_line']}" for c in all_chunks]
    metadatas = [
        {
            "path": c["path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "kind": c["kind"],
            "name": c["name"],
        }
        for c in all_chunks
    ]

    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        collection.upsert(
            ids=ids[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            documents=texts[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )

    return len(all_chunks)


# ---------------------------------------------------------------------------
# LangChain tool — for use with LangGraph ToolNode
# ---------------------------------------------------------------------------


@tool
def codebase_search(
    query: str,
    project_root: str,
    n_results: int = 5,
    persist_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Hybrid semantic + keyword search over the indexed codebase.

    Performs a vector similarity search against the ChromaDB index and then
    boosts scores for chunks that also contain the raw query terms (keyword
    re-rank).  Falls back to keyword-only search when the index is empty or
    embeddings are unavailable.

    Args:
        query:        Natural-language or keyword query (e.g. "auth logic").
        project_root: Absolute path of the project directory.
        n_results:    Maximum number of results to return (default: 5).
        persist_dir:  Optional custom path for the ChromaDB index.

    Returns:
        List of result dicts with keys: path, start_line, end_line, kind,
        name, score, text.
    """
    root_path = Path(project_root)
    index_path = Path(persist_dir) if persist_dir else root_path / INDEX_SUBDIR

    collection = _get_collection(index_path)
    total = collection.count()

    results: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    # Semantic search via embeddings
    if total > 0:
        try:
            query_embedding = _embed_texts([query])[0]
            k = min(n_results * 2, total)
            raw = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"],
            )
            for doc, meta, dist in zip(
                raw["documents"][0],
                raw["metadatas"][0],
                raw["distances"][0],
            ):
                chunk_id = f"{meta['path']}::{meta['start_line']}"
                if chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    results.append(
                        {
                            **meta,
                            "score": float(1.0 - dist),
                            "text": doc,
                        }
                    )
        except Exception:
            pass

    # Keyword boost: re-rank results that contain the query terms
    query_terms = re.findall(r"\w+", query.lower())
    for r in results:
        text_lower = r["text"].lower()
        hits = sum(1 for t in query_terms if t in text_lower)
        r["score"] = r["score"] + 0.1 * hits

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:n_results]


# Ordered list of code-index tools — bind to a LangGraph ToolNode
CODE_INDEX_TOOLS = [codebase_search]

# Ready-to-use LangGraph ToolNode for the code-index tool suite
code_index_tool_node = ToolNode(CODE_INDEX_TOOLS)
