# mcp-reddit

MCP server for Reddit's public JSON API — browse posts, search threads, inspect subreddits and users.
Part of the `trellis-mcp-servers` collection.

## Tools

| Tool | Description |
|------|-------------|
| `fetch_reddit_hot_threads` | Hot posts from a subreddit |
| `fetch_reddit_new` | Newest posts from a subreddit |
| `fetch_reddit_top` | Top posts with configurable time filter (hour/day/week/month/year/all) |
| `fetch_reddit_post_content` | Post body + top-level comments |
| `fetch_comment_thread` | Deep-load a specific comment chain by permalink |
| `search_reddit` | Search posts within a subreddit or across all of Reddit |
| `search_subreddits` | Find subreddits by topic or keyword |
| `get_subreddit_info` | Subscriber count, description, rules, creation date |
| `get_user_profile` | Karma, account age, and recent posts for a user |

## Usage

### Install

```bash
uv sync
```

### Run (stdio transport for Claude Code)

```bash
uv run --with-editable . mcp-reddit
```

### Add to Claude Code

```bash
claude mcp add reddit -- ~/.local/bin/uv run --with-editable /home/harshu/projects/trellis-mcp-servers/reddit mcp-reddit
```

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `REDDIT_USER_AGENT` | `mcp-reddit/1.0 (https://github.com/harshanchenna/mcp-reddit)` | User-Agent header sent to Reddit |

Reddit's public JSON API requires a descriptive User-Agent string.
Set `REDDIT_USER_AGENT` to override the default if you want to identify your instance:

```bash
export REDDIT_USER_AGENT="my-app/1.0 (by /u/my-reddit-user)"
```

## Rate limits

Reddit's public API allows roughly 60 requests/minute without OAuth.
The server automatically retries on 429 responses (up to 3 attempts) with exponential backoff,
honouring `Retry-After` headers when present.

## Notes

- All tools use Reddit's unauthenticated `.json` API — no OAuth token required.
- `limit` parameters accept values up to 100 (Reddit's actual maximum).
- Subreddit names and usernames should be provided **without** the `r/` or `u/` prefix.
- Private or quarantined subreddits will return a clear 403 error.
