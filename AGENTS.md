# AGENTS.md

Guide for coding agents (Claude Code, Codex, etc.) and human contributors working in this repo.

## What this is

An MCP (Model Context Protocol) server over Reddit's public, unauthenticated `.json` API — nine
tools for browsing, searching, and reading subreddits, posts, comment threads, and user profiles.
No OAuth or API key needed. Single-file Python project.

## How to navigate it

- `server.py` — the entire server: all nine tool definitions, the HTTP client, and the
  retry/backoff logic for Reddit's rate limits.
- `pyproject.toml` — dependencies (`mcp[cli]`, `requests`) and the `mcp-reddit` console script.
- `README.md` — install instructions, the full tool table, and configuration/rate-limit notes;
  keep it in sync with any new tool or behavior change.

## Build, test, lint

```bash
uv sync                                  # install deps into .venv
uv run mcp-reddit                        # run the server (stdio transport)
```

**Known issue (verified 2026-09-27):** there is no committed `uv.lock`, so a fresh `uv sync`
free-resolves `mcp` and can land on `mcp>=2.0`, which renamed `FastMCP` and breaks the
`from mcp.server.fastmcp import FastMCP` import in `server.py`. Until `pyproject.toml` pins
`mcp<2.0` (or a working `uv.lock` is committed), verify `uv run python -c "import server"`
succeeds after `uv sync` before relying on the server.

There is no automated test suite or linter configured yet. This is a single file with real
retry/backoff logic worth covering — add `pytest` (as a `dev` optional-dependency group) if you
extend it.

## Standards this repo owns

- Stay on Reddit's public JSON API — no OAuth flow, no API credentials.
- Keep the retry/backoff behavior (429 handling, `Retry-After`) centralized in the one HTTP
  helper in `server.py`, not duplicated per tool.
- Any new tool must be documented in the `README.md` tools table in the same change.

## PR, review, and commit rules

- Branch → PR → full `/code-review` before merge.
- Merge commits, not squash.
- No `Co-Authored-By` or other AI-attribution lines in commits.
- Secrets: none are needed for this server's normal operation; if any are ever added, they live
  only in `.env`, never committed.

Keep this file and the README current when structure or commands change.
