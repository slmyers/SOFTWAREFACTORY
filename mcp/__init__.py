"""MCP package – client and server registry for SOFTWAREFACTORY."""

from .client import (
    call_mcp_tool,
    discover_servers,
    get_server_url,
    register_server,
)

__all__ = [
    "call_mcp_tool",
    "discover_servers",
    "get_server_url",
    "register_server",
]
