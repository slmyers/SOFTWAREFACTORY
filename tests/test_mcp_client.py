"""Tests for mcp/client.py."""

import pytest

import mcp.client as client
from mcp import call_mcp_tool, discover_servers, get_server_url, register_server


# ---------------------------------------------------------------------------
# register_server
# ---------------------------------------------------------------------------


def test_register_server_adds_entry(monkeypatch):
    original = dict(client._REGISTRY)
    try:
        register_server("my-server", "http://localhost:9999")
        assert client._REGISTRY["my-server"] == "http://localhost:9999"
    finally:
        client._REGISTRY.clear()
        client._REGISTRY.update(original)


def test_register_server_updates_existing(monkeypatch):
    original = dict(client._REGISTRY)
    try:
        register_server("genai-toolbox", "http://localhost:9000")
        assert client._REGISTRY["genai-toolbox"] == "http://localhost:9000"
    finally:
        client._REGISTRY.clear()
        client._REGISTRY.update(original)


def test_register_server_rejects_empty_name():
    with pytest.raises(ValueError, match="name"):
        register_server("", "http://localhost:5000")


def test_register_server_rejects_empty_url():
    with pytest.raises(ValueError, match="URL"):
        register_server("my-server", "")


def test_register_server_rejects_invalid_scheme():
    with pytest.raises(ValueError, match="scheme"):
        register_server("my-server", "ftp://localhost:5000")





def test_discover_servers_returns_dict():
    result = discover_servers()
    assert isinstance(result, dict)
    assert "genai-toolbox" in result


def test_discover_servers_reads_env_var(monkeypatch):
    original = dict(client._REGISTRY)
    monkeypatch.setenv("MCP_SERVER_MY_CUSTOM", "http://custom:1234")
    try:
        result = discover_servers()
        assert result.get("my-custom") == "http://custom:1234"
    finally:
        client._REGISTRY.clear()
        client._REGISTRY.update(original)
        client._REGISTRY.pop("my-custom", None)


# ---------------------------------------------------------------------------
# get_server_url
# ---------------------------------------------------------------------------


def test_get_server_url_known():
    url = get_server_url("genai-toolbox")
    assert url is not None
    assert url.startswith("http")


def test_get_server_url_unknown():
    url = get_server_url("does-not-exist-xyz")
    assert url is None


# ---------------------------------------------------------------------------
# call_mcp_tool – stub path (server not reachable)
# ---------------------------------------------------------------------------


def test_call_mcp_tool_unknown_server():
    with pytest.raises(ValueError, match="not registered"):
        call_mcp_tool("no-such-server", "ping")


def _raise_connection_error(*_a, **_kw):
    raise ConnectionError("refused")


def test_call_mcp_tool_returns_stub_when_unreachable(monkeypatch):
    """When the server is registered but unreachable, a stub dict is returned."""
    monkeypatch.setattr(client, "_http_call", _raise_connection_error)
    result = call_mcp_tool("genai-toolbox", "query", q="test")
    assert result["stub"] is True
    assert result["server"] == "genai-toolbox"
    assert result["tool"] == "query"
    assert result["payload"] == {"q": "test"}


def test_call_mcp_tool_genai_toolbox_stub(monkeypatch):
    """Definition of done: call_mcp_tool('genai-toolbox', 'query', ...) works."""
    monkeypatch.setattr(client, "_http_call", _raise_connection_error)
    result = call_mcp_tool("genai-toolbox", "query", sql="SELECT 1")
    assert result["stub"] is True
    assert result["server"] == "genai-toolbox"
    assert result["tool"] == "query"


# ---------------------------------------------------------------------------
# call_mcp_tool – live path (http_call succeeds)
# ---------------------------------------------------------------------------


def test_call_mcp_tool_uses_http_when_available(monkeypatch):
    expected = {"rows": [{"id": 1}]}
    monkeypatch.setattr(client, "_http_call", lambda *_a, **_kw: expected)
    result = call_mcp_tool("genai-toolbox", "query", sql="SELECT 1")
    assert result == expected
