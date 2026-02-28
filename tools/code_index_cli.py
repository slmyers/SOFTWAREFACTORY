"""Command-line entry point for triggering a codebase re-index.

Invoked automatically by the post-commit git hook installed via
``scripts/install_index_hook.py``, or manually::

    python -m tools.code_index_cli [--root PATH]
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-index the codebase for semantic search.")
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory).",
    )
    parser.add_argument(
        "--persist-dir",
        default=None,
        help="Custom ChromaDB index directory (default: <root>/.softwarefactory/index).",
    )
    args = parser.parse_args()

    try:
        from tools.code_index import index_codebase

        count = index_codebase(args.root, persist_dir=args.persist_dir)
        print(f"[code-index] Indexed {count} chunks from {args.root}")
    except Exception as exc:  # noqa: BLE001
        print(f"[code-index] Indexing failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
