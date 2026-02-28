"""Browser automation tool via the Playwright MCP server (issue #49).

Agents call ``browser_action`` to drive a real browser headlessly through the
official Microsoft Playwright MCP server.  The tool delegates every action to
``call_mcp_tool("playwright-mcp", action, **params)`` so it automatically
benefits from the MCP registry's auto-discovery and stub fallback.

Supported actions (mirroring the Playwright MCP tool surface):
  navigate, click, type, fill, press_key, screenshot, snapshot,
  hover, select_option, wait_for, evaluate, close
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

from mcp.client import call_mcp_tool

# ---------------------------------------------------------------------------
# Supported action names
# ---------------------------------------------------------------------------

BROWSER_ACTIONS = frozenset(
    {
        "navigate",
        "click",
        "type",
        "fill",
        "press_key",
        "screenshot",
        "snapshot",
        "hover",
        "select_option",
        "wait_for",
        "evaluate",
        "close",
    }
)


# ---------------------------------------------------------------------------
# LangChain tool
# ---------------------------------------------------------------------------


@tool
def browser_action(action: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Perform a browser automation action via the Playwright MCP server.

    This tool gives agents full browser control for E2E testing, UI validation,
    and web-spec implementation.  It routes requests through the MCP registry
    so the Playwright MCP server is auto-discovered at runtime.

    Args:
        action: One of the supported Playwright MCP actions:
            ``navigate``, ``click``, ``type``, ``fill``, ``press_key``,
            ``screenshot``, ``snapshot``, ``hover``, ``select_option``,
            ``wait_for``, ``evaluate``, ``close``.
        params: Keyword arguments forwarded to the Playwright MCP tool as
            the action payload.  For example::

                browser_action("navigate", {"url": "https://example.com"})
                browser_action("click", {"ref": "e12", "element": "Submit"})
                browser_action("screenshot", {"filename": "result.png"})

    Returns:
        The decoded response from the Playwright MCP server, or a stub dict
        when the server is unreachable (useful for testing).

    Raises:
        ValueError: If *action* is not a recognised Playwright MCP action.
    """
    if action not in BROWSER_ACTIONS:
        raise ValueError(
            f"Unknown browser action {action!r}. "
            f"Supported actions: {sorted(BROWSER_ACTIONS)}"
        )
    return call_mcp_tool("playwright-mcp", action, **(params or {}))


# ---------------------------------------------------------------------------
# Ready-to-use LangGraph ToolNode
# ---------------------------------------------------------------------------

BROWSER_TOOLS = [browser_action]

browser_tool_node = ToolNode(BROWSER_TOOLS)
