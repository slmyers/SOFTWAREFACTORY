"""CLI entry points for SOFTWAREFACTORY (Issue #10).

Commands
--------
run     -- Start a new graph run from a spec file.
dev     -- Same as run but with verbose/debug output enabled.
resume  -- Resume a previous run from a saved checkpoint thread.
diff    -- Preview a unified diff without applying it.

Usage examples
--------------
  python main.py run --spec specs/todo.md
  python main.py dev --spec specs/todo.md
  python main.py resume --thread-id <uuid>
  python main.py diff --patch path/to/changes.diff --root .
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional
from uuid import uuid4

import typer
from rich.console import Console

from graph.compile import compile_graph
from graph.state import AgentStateModel, load_checkpoint
from tools.file_edits import apply_unified_diff, diff_preview

app = typer.Typer(name="softwarefactory", add_completion=False)
console = Console()


def _build_initial_state(spec_path: str) -> dict:
    """Return a minimal initial AgentState dict for a fresh run."""
    path = Path(spec_path)
    if not path.exists():
        console.print(f"[bold yellow]Warning:[/bold yellow] spec file not found: {spec_path!r} — starting with empty spec_content")
    spec_content = path.read_text() if path.exists() else ""
    return {
        "spec_path": spec_path,
        "spec_content": spec_content,
        "spec_structure": {},
        "codebase": {},
        "plan": [],
        "test_results": [],
        "issues": [],
        "iteration": 0,
        "next": "",
        "checkpoint": {},
        "mcp_servers": [],
        "quality_score": 0.0,
        "invariants": [],
    }


def _invoke_graph(initial_state: dict, thread_id: str, verbose: bool = False) -> None:
    """Compile and invoke the graph with the given initial state."""
    graph = compile_graph()
    config = {"configurable": {"thread_id": thread_id}}
    if verbose:
        console.print(f"[bold cyan]Thread ID:[/bold cyan] {thread_id}")
        console.print(f"[bold cyan]spec_path:[/bold cyan] {initial_state.get('spec_path')}")

    result = graph.invoke(initial_state, config)

    if verbose:
        console.print("[bold green]Run complete.[/bold green]")
        console.print(f"Final next: {result.get('next', '<none>')}")
    else:
        console.print(f"[green]Done[/green] (thread_id={thread_id})")


@app.command()
def run(
    spec: str = typer.Option(..., "--spec", help="Path to the spec file (e.g. specs/todo.md)"),
    thread_id: Optional[str] = typer.Option(None, "--thread-id", help="Optional thread ID (auto-generated if omitted)"),
) -> None:
    """Start a new graph run from a spec file."""
    tid = thread_id or str(uuid4())
    initial_state = _build_initial_state(spec)
    _invoke_graph(initial_state, tid)


@app.command()
def dev(
    spec: str = typer.Option(..., "--spec", help="Path to the spec file (e.g. specs/todo.md)"),
    thread_id: Optional[str] = typer.Option(None, "--thread-id", help="Optional thread ID (auto-generated if omitted)"),
) -> None:
    """Start a new graph run in development/verbose mode."""
    tid = thread_id or str(uuid4())
    initial_state = _build_initial_state(spec)
    console.print("[bold yellow]DEV mode — verbose output enabled[/bold yellow]")
    _invoke_graph(initial_state, tid, verbose=True)


@app.command()
def resume(
    thread_id: str = typer.Option(..., "--thread-id", help="Thread ID of the checkpoint to resume"),
    spec: Optional[str] = typer.Option(None, "--spec", help="Override spec path (optional)"),
) -> None:
    """Resume a previous graph run from a saved checkpoint."""

    async def _resume() -> None:
        state_model: AgentStateModel = await load_checkpoint(thread_id)
        state_dict = state_model.to_dict()
        if spec:
            spec_path_obj = Path(spec)
            state_dict["spec_path"] = spec
            state_dict["spec_content"] = spec_path_obj.read_text() if spec_path_obj.exists() else ""
        _invoke_graph(state_dict, thread_id)

    try:
        asyncio.run(_resume())
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] No checkpoint found for thread_id={thread_id!r}")
        raise typer.Exit(code=1)


@app.command()
def diff(
    patch: str = typer.Option(..., "--patch", help="Path to a .diff / .patch file"),
    root: str = typer.Option(".", "--root", help="Project root directory (default: current directory)"),
    apply: bool = typer.Option(False, "--apply", help="Apply the diff after previewing it"),
) -> None:
    """Preview (and optionally apply) a unified diff inside the project root."""
    patch_path = Path(patch)
    if not patch_path.exists():
        console.print(f"[bold red]Error:[/bold red] patch file not found: {patch!r}")
        raise typer.Exit(code=1)

    diff_content = patch_path.read_text(encoding="utf-8")
    root_path = Path(root).resolve()

    try:
        preview = diff_preview(diff_content, root_path)
    except ValueError as exc:
        console.print(f"[bold red]Invalid diff:[/bold red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Diff preview:[/bold cyan] {preview.summary}")
    for f in preview.files_changed:
        console.print(f"  [yellow]{f}[/yellow]")

    if apply:
        try:
            results = apply_unified_diff(diff_content, root_path)
        except ValueError as exc:
            console.print(f"[bold red]Apply failed:[/bold red] {exc}")
            raise typer.Exit(code=1)
        written = [p for p, info in results.items() if info.get("written")]
        console.print(f"[green]Applied:[/green] {len(written)} file(s) written.")


if __name__ == "__main__":
    app()
