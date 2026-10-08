"""Smoke tests: the server imports, exposes its tools, and its HTTP helper
retries/errors correctly, all without making real network calls."""

from __future__ import annotations

import asyncio

import pytest

from mcp_reddit import server

EXPECTED_TOOLS = {
    "fetch_reddit_hot_threads",
    "fetch_reddit_new",
    "fetch_reddit_top",
    "fetch_reddit_post_content",
    "fetch_comment_thread",
    "search_reddit",
    "search_subreddits",
    "get_subreddit_info",
    "get_user_profile",
}


def test_all_tools_are_registered() -> None:
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS <= names


def test_fmt_post_basic() -> None:
    post = {
        "title": "Hello world",
        "score": 42,
        "num_comments": 3,
        "author": "someone",
        "subreddit": "test",
        "permalink": "/r/test/comments/abc/hello_world/",
    }
    out = server._fmt_post(post)
    assert "Hello world" in out
    assert "Score: 42" in out
    assert "r/test" in out
    assert "https://reddit.com/r/test/comments/abc/hello_world/" in out


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = str(payload)

    def json(self):
        return self._payload


def test_reddit_get_returns_json_on_200(monkeypatch) -> None:
    monkeypatch.setattr(server._session, "get", lambda *a, **k: _FakeResponse(200, {"ok": True}))
    assert server._reddit_get("https://example.invalid") == {"ok": True}


def test_reddit_get_raises_on_404(monkeypatch) -> None:
    monkeypatch.setattr(server._session, "get", lambda *a, **k: _FakeResponse(404))
    with pytest.raises(RuntimeError, match="404"):
        server._reddit_get("https://example.invalid")


def test_reddit_get_raises_on_403(monkeypatch) -> None:
    monkeypatch.setattr(server._session, "get", lambda *a, **k: _FakeResponse(403))
    with pytest.raises(RuntimeError, match="403"):
        server._reddit_get("https://example.invalid")


def test_reddit_get_retries_then_raises_on_persistent_429(monkeypatch) -> None:
    monkeypatch.setattr(server, "_RETRY_BASE_DELAY", 0.0)
    monkeypatch.setattr(server.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(
        server._session, "get", lambda *a, **k: _FakeResponse(429, headers={"Retry-After": "0"})
    )
    with pytest.raises(RuntimeError, match="rate limit"):
        server._reddit_get("https://example.invalid")


def test_main_entry_point_exists() -> None:
    assert callable(server.main)
