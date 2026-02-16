"""LangGraph saver adapter (lightweight placeholder).

This adapter provides a minimal attach point for LangGraph to call the
canonical checkpoint API implemented in graph.state. For now it marks the
graph object so higher-level code can detect the presence of a custom saver.
"""

from typing import Any


def attach_langgraph_saver(graph: Any) -> bool:
    """Attach a minimal marker to the compiled graph. Returns True on success."""
    try:
        setattr(graph, "_langgraph_custom_saver", True)
        return True
    except Exception:
        return False
