"""MCP client with server registry and unified tool-call interface."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Server registry
# ---------------------------------------------------------------------------

# Well-known MCP server names mapped to their base URLs.
# Auto-discovery can override these at runtime via environment variables or
# by calling `register_server` / `discover_servers`.
_REGISTRY: Dict[str, str] = {
    "genai-toolbox": "http://localhost:5000",
    "mcp-obsidian": "http://localhost:5001",
    "playwright-mcp": "http://localhost:3000",
}


def register_server(name: str, url: str) -> None:
    """Register (or update) an MCP server entry in the in-process registry.

    Args:
        name: Logical server name (e.g. ``"genai-toolbox"``).
        url:  Base URL of the server (e.g. ``"http://localhost:5000"``).
              Must use the ``http`` or ``https`` scheme.
    """
    if not name:
        raise ValueError("Server name must not be empty.")
    if not url:
        raise ValueError("Server URL must not be empty.")
    if not url.startswith(("http://", "https://")):
        raise ValueError("Server URL must use http or https scheme.")
    _REGISTRY[name] = url


def discover_servers() -> Dict[str, str]:
    """Auto-discover running MCP servers.

    Discovery order (later steps can override earlier ones):

    1. Built-in defaults already in ``_REGISTRY``.
    2. Environment variables of the form ``MCP_SERVER_<NAME>=<URL>`` where
       ``<NAME>`` is the upper-cased server name with hyphens replaced by
       underscores.  E.g. ``MCP_SERVER_GENAI_TOOLBOX=http://host:5000``.

    Returns:
        The current registry snapshot after applying env-var overrides.
    """
    prefix = "MCP_SERVER_"
    for key, value in os.environ.items():
        if key.startswith(prefix):
            raw_name = key[len(prefix):]
            # Convert GENAI_TOOLBOX -> genai-toolbox
            name = raw_name.lower().replace("_", "-")
            if name and value and value.startswith(("http://", "https://")):
                _REGISTRY[name] = value
    return dict(_REGISTRY)


def get_server_url(name: str) -> Optional[str]:
    """Return the URL for a registered MCP server, or *None* if unknown."""
    discover_servers()
    return _REGISTRY.get(name)


# ---------------------------------------------------------------------------
# Unified tool-call interface
# ---------------------------------------------------------------------------


def call_mcp_tool(
    server: str,
    tool: str,
    /,
    **kwargs: Any,
) -> Any:
    """Invoke *tool* on the named MCP *server*.

    This is the single entry-point for all MCP tool calls in SOFTWAREFACTORY.
    The implementation is intentionally thin: it resolves the server URL from
    the registry, builds a request payload, and dispatches it.  When a real
    HTTP transport is available it delegates to ``_http_call``; otherwise it
    falls back to a stub that is useful for testing and local development.

    Args:
        server: Logical server name (e.g. ``"genai-toolbox"``).
        tool:   Tool / endpoint name (e.g. ``"query"``).
        **kwargs: Arbitrary keyword arguments forwarded as the tool payload.

    Returns:
        The decoded response from the MCP server, or a stub dict when the
        server is not reachable.

    Raises:
        ValueError: If *server* is not registered.
    """
    url = get_server_url(server)
    if url is None:
        raise ValueError(
            f"MCP server {server!r} is not registered. "
            "Call register_server() or set MCP_SERVER_<NAME> env var."
        )

    try:
        return _http_call(url, tool, kwargs)
    except (ImportError, OSError, ConnectionError, TimeoutError):
        return _stub_call(server, tool, kwargs)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _http_call(base_url: str, tool: str, payload: Dict[str, Any]) -> Any:
    """Attempt a real HTTP POST to the MCP server.

    Requires the ``httpx`` or ``requests`` package.  Raises ``ImportError``
    or a connection error if neither is available or the server is down.
    """
    endpoint = f"{base_url.rstrip('/')}/tools/{tool}"
    try:
        import httpx  # type: ignore[import]

        response = httpx.post(endpoint, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except ImportError:
        pass

    import urllib.request
    import json as _json

    data = _json.dumps(payload).encode()
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return _json.loads(resp.read())


def _stub_call(server: str, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deterministic stub response when the server is unreachable."""
    return {
        "stub": True,
        "server": server,
        "tool": tool,
        "payload": payload,
    }
