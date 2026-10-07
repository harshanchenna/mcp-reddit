# AGENTS.md

Guide for coding agents (Claude Code, Codex, etc.) and human contributors working in this repo.

## What this is

An MCP (Model Context Protocol) server over Reddit's public, unauthenticated `.json` API — nine
tools for browsing, searching, and reading subreddits, posts, comment threads, and user profiles.
No OAuth or API key needed. Single-package Python project (PyPI distribution name
`harshanchenna-mcp-reddit`; `mcp-reddit` was already taken on PyPI by an unrelated package).

## How to navigate it

- `src/mcp_reddit/server.py` — the entire server: all nine tool definitions, the HTTP client, and
  the retry/backoff logic for Reddit's rate limits.
- `pyproject.toml` — dependencies (`mcp[cli]`, `requests`) and the `mcp-reddit` console script.
- `README.md` — install instructions, the full tool table, and configuration/rate-limit notes;
  keep it in sync with any new tool or behavior change.
- `server.json` — manifest for the official MCP registry.

## Build, test, lint

```bash
uv sync --extra dev                      # install deps into .venv
uv run pytest                            # run the test suite
uv run mcp-reddit                        # run the server (stdio transport)
```

**Resolved issue (was open 2026-09-27):** `pyproject.toml` now pins `mcp[cli]<2.0.0`, so a fresh
`uv sync` no longer free-resolves into the `mcp>=2.0` `FastMCP` rename that broke
`from mcp.server.fastmcp import FastMCP`. `uv.lock` is still not committed; if the pin is ever
loosened, re-verify `uv run python -c "import mcp_reddit.server"` after `uv sync`.

A `pytest` suite covers tool registration and the formatting/retry helpers (`dev` optional-dependency
group). Extend it alongside any new tool or retry-logic change.

## Standards this repo owns

- Stay on Reddit's public JSON API — no OAuth flow, no API credentials.
- Keep the retry/backoff behavior (429 handling, `Retry-After`) centralized in the one HTTP
  helper in `src/mcp_reddit/server.py`, not duplicated per tool.
- Any new tool must be documented in the `README.md` tools table in the same change.

## PR, review, and commit rules

- Branch → PR → full `/code-review` before merge.
- Merge commits, not squash.
- No `Co-Authored-By` or other AI-attribution lines in commits.
- Secrets: none are needed for this server's normal operation; if any are ever added, they live
  only in `.env`, never committed.

Keep this file and the README current when structure or commands change.
