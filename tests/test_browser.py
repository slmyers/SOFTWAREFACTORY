"""Tests for tools/browser.py — browser_action tool (issue #49)."""

from __future__ import annotations

import pytest

import mcp.client as mcp_client
from tools.browser import BROWSER_ACTIONS, BROWSER_TOOLS, browser_action


# ---------------------------------------------------------------------------
# browser_action — validation
# ---------------------------------------------------------------------------


def test_browser_action_rejects_unknown_action():
    with pytest.raises(ValueError, match="Unknown browser action"):
        browser_action.invoke({"action": "do_magic"})


def test_browser_action_lists_known_actions_in_error():
    try:
        browser_action.invoke({"action": "teleport"})
    except ValueError as exc:
        assert "Supported actions" in str(exc)


# ---------------------------------------------------------------------------
# browser_action — stub path (playwright-mcp not reachable)
# ---------------------------------------------------------------------------


def _raise_connection_error(*_a, **_kw):
    raise ConnectionError("playwright-mcp not running")


def test_browser_action_navigate_stub(monkeypatch):
    """navigate returns a stub dict when the server is unreachable."""
    monkeypatch.setattr(mcp_client, "_http_call", _raise_connection_error)
    result = browser_action.invoke({"action": "navigate", "params": {"url": "http://localhost:3001"}})
    assert result["stub"] is True
    assert result["server"] == "playwright-mcp"
    assert result["tool"] == "navigate"
    assert result["payload"] == {"url": "http://localhost:3001"}


def test_browser_action_screenshot_stub(monkeypatch):
    monkeypatch.setattr(mcp_client, "_http_call", _raise_connection_error)
    result = browser_action.invoke({"action": "screenshot", "params": {"filename": "out.png"}})
    assert result["stub"] is True
    assert result["tool"] == "screenshot"


def test_browser_action_snapshot_stub(monkeypatch):
    monkeypatch.setattr(mcp_client, "_http_call", _raise_connection_error)
    result = browser_action.invoke({"action": "snapshot", "params": {}})
    assert result["stub"] is True
    assert result["tool"] == "snapshot"


def test_browser_action_no_params_stub(monkeypatch):
    """params defaults to {} when omitted."""
    monkeypatch.setattr(mcp_client, "_http_call", _raise_connection_error)
    result = browser_action.invoke({"action": "close"})
    assert result["stub"] is True
    assert result["tool"] == "close"
    assert result["payload"] == {}


# ---------------------------------------------------------------------------
# browser_action — live path (http_call succeeds)
# ---------------------------------------------------------------------------


def test_browser_action_uses_http_when_available(monkeypatch):
    expected = {"url": "http://localhost:3001", "status": 200}
    monkeypatch.setattr(mcp_client, "_http_call", lambda *_a, **_kw: expected)
    result = browser_action.invoke({"action": "navigate", "params": {"url": "http://localhost:3001"}})
    assert result == expected


# ---------------------------------------------------------------------------
# Registry: playwright-mcp is registered
# ---------------------------------------------------------------------------


def test_playwright_mcp_in_registry():
    from mcp.client import get_server_url

    url = get_server_url("playwright-mcp")
    assert url is not None
    assert url.startswith("http")


# ---------------------------------------------------------------------------
# BROWSER_TOOLS list
# ---------------------------------------------------------------------------


def test_browser_tools_contains_browser_action():
    names = [t.name for t in BROWSER_TOOLS]
    assert "browser_action" in names


def test_all_documented_actions_are_in_frozenset():
    expected = {
        "navigate", "click", "type", "fill", "press_key",
        "screenshot", "snapshot", "hover", "select_option",
        "wait_for", "evaluate", "close",
    }
    assert expected == BROWSER_ACTIONS
