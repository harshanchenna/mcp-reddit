"""MCP server exposing Reddit public JSON API tools."""

from __future__ import annotations

import os
import time
import urllib.parse
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_USER_AGENT = "mcp-reddit/1.0 (https://github.com/harshanchenna/mcp-reddit)"
USER_AGENT = os.environ.get("REDDIT_USER_AGENT", _DEFAULT_USER_AGENT)

mcp = FastMCP(
    "reddit",
    instructions=(
        "Search and browse Reddit using the public JSON API. "
        "Subreddit names should be provided without the r/ prefix. "
        "Post URLs can be full URLs or Reddit permalinks (e.g. /r/sub/comments/...)."
    ),
)

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # seconds


def _reddit_get(url: str, params: dict[str, Any] | None = None) -> Any:
    """GET request to Reddit's JSON API with retry on 429 and clear error messages."""
    for attempt in range(_MAX_RETRIES):
        try:
            resp = _session.get(url, params=params, timeout=15)
        except requests.ConnectionError as exc:
            raise RuntimeError(f"Network error reaching Reddit: {exc}") from exc
        except requests.Timeout:
            raise RuntimeError("Request to Reddit timed out after 15 seconds.")

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 429:
            # Honour Retry-After if present, otherwise exponential backoff
            retry_after = float(resp.headers.get("Retry-After", _RETRY_BASE_DELAY * (2 ** attempt)))
            if attempt < _MAX_RETRIES - 1:
                time.sleep(retry_after)
                continue
            raise RuntimeError(
                f"Reddit rate limit exceeded (429). Retry after {retry_after:.0f}s."
            )

        if resp.status_code == 404:
            raise RuntimeError(f"Not found (404): {url}")

        if resp.status_code == 403:
            raise RuntimeError(
                f"Access forbidden (403) — subreddit may be private or quarantined: {url}"
            )

        # Generic HTTP error
        raise RuntimeError(f"HTTP {resp.status_code} from Reddit: {resp.text[:200]}")

    # Should never reach here
    raise RuntimeError("Exhausted retries.")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_post(p: dict[str, Any]) -> str:
    """Format a post dict into a readable string."""
    return (
        f"Title: {p.get('title', '(no title)')}\n"
        f"Score: {p.get('score', 0)} | Comments: {p.get('num_comments', 0)}\n"
        f"Author: {p.get('author', '[deleted]')}\n"
        f"Subreddit: r/{p.get('subreddit', '?')}\n"
        f"URL: https://reddit.com{p['permalink']}\n"
        f"---"
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def fetch_reddit_hot_threads(subreddit: str, limit: int = 10) -> str:
    """Fetch hot posts from a subreddit.

    Args:
        subreddit: Name of the subreddit (without r/ prefix), e.g. 'MachineLearning'.
        limit: Number of posts to fetch (default: 10, max: 100).
    """
    limit = max(1, min(limit, 100))
    try:
        data = _reddit_get(
            f"https://www.reddit.com/r/{subreddit}/hot.json",
            params={"limit": limit},
        )
        posts = [_fmt_post(c["data"]) for c in data["data"]["children"]]
        return "\n\n".join(posts) if posts else "No posts found."
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def fetch_reddit_new(subreddit: str, limit: int = 10) -> str:
    """Fetch the newest posts from a subreddit.

    Args:
        subreddit: Name of the subreddit (without r/ prefix).
        limit: Number of posts to fetch (default: 10, max: 100).
    """
    limit = max(1, min(limit, 100))
    try:
        data = _reddit_get(
            f"https://www.reddit.com/r/{subreddit}/new.json",
            params={"limit": limit},
        )
        posts = [_fmt_post(c["data"]) for c in data["data"]["children"]]
        return "\n\n".join(posts) if posts else "No posts found."
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def fetch_reddit_top(subreddit: str, time_filter: str = "week", limit: int = 10) -> str:
    """Fetch top posts from a subreddit with an optional time filter.

    Args:
        subreddit: Name of the subreddit (without r/ prefix).
        time_filter: Time period — one of: hour, day, week, month, year, all (default: week).
        limit: Number of posts to fetch (default: 10, max: 100).
    """
    valid_filters = {"hour", "day", "week", "month", "year", "all"}
    if time_filter not in valid_filters:
        return f"Error: time_filter must be one of {sorted(valid_filters)}."
    limit = max(1, min(limit, 100))
    try:
        data = _reddit_get(
            f"https://www.reddit.com/r/{subreddit}/top.json",
            params={"t": time_filter, "limit": limit},
        )
        posts = [_fmt_post(c["data"]) for c in data["data"]["children"]]
        return "\n\n".join(posts) if posts else "No posts found."
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def fetch_reddit_post_content(url: str, comment_limit: int = 10) -> str:
    """Fetch a Reddit post's content and top-level comments.

    Args:
        url: Full Reddit post URL or permalink (e.g. /r/MachineLearning/comments/...).
        comment_limit: Number of top comments to include (default: 10, max: 100).
    """
    comment_limit = max(1, min(comment_limit, 100))
    try:
        if url.startswith("/"):
            url = f"https://www.reddit.com{url}"
        if not url.endswith(".json"):
            url = url.rstrip("/") + ".json"

        data = _reddit_get(url, params={"limit": comment_limit})

        post = data[0]["data"]["children"][0]["data"]
        selftext = post.get("selftext", "(no text)")
        result = (
            f"Title: {post['title']}\n"
            f"Score: {post.get('score', 0)} | Comments: {post.get('num_comments', 0)}\n"
            f"Author: {post.get('author', '[deleted]')}\n"
            f"Subreddit: r/{post.get('subreddit', '?')}\n"
            f"Selftext: {selftext[:2000]}\n"
            f"\n--- Top Comments ---\n"
        )

        for c in data[1]["data"]["children"][:comment_limit]:
            if c["kind"] != "t1":
                continue
            cd = c["data"]
            result += (
                f"\n[{cd.get('score', 0)} pts] {cd.get('author', '[deleted]')}:\n"
                f"{cd.get('body', '')[:500]}\n"
            )

        return result
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def fetch_comment_thread(permalink: str, depth: int = 5, limit: int = 20) -> str:
    """Deep-load a specific comment thread by permalink.

    Useful for reading a focused discussion chain rather than the full post.

    Args:
        permalink: Reddit permalink (e.g. /r/sub/comments/abc123/post_title/def456/).
                   Can be a full URL or a path starting with /r/.
        depth: How many levels of nested replies to fetch (default: 5).
        limit: Max number of top-level comments to include (default: 20, max: 100).
    """
    limit = max(1, min(limit, 100))
    depth = max(1, min(depth, 10))
    try:
        if permalink.startswith("http"):
            url = permalink.rstrip("/") + ".json"
        elif permalink.startswith("/"):
            url = f"https://www.reddit.com{permalink.rstrip('/')}.json"
        else:
            url = f"https://www.reddit.com/{permalink.rstrip('/')}.json"

        data = _reddit_get(url, params={"depth": depth, "limit": limit})

        post = data[0]["data"]["children"][0]["data"]
        result = (
            f"Post: {post.get('title', '(no title)')}\n"
            f"Score: {post.get('score', 0)}\n"
            f"---\n\n"
        )

        def _render_comments(children: list[dict[str, Any]], indent: int = 0) -> str:
            lines = []
            prefix = "  " * indent
            for c in children:
                if c.get("kind") != "t1":
                    continue
                cd = c["data"]
                author = cd.get("author", "[deleted]")
                score = cd.get("score", 0)
                body = cd.get("body", "").strip()[:600]
                lines.append(f"{prefix}[{score} pts] {author}:\n{prefix}{body}")
                replies_data = cd.get("replies") or {}
                if isinstance(replies_data, dict):
                    nested = replies_data.get("data", {}).get("children", [])
                    if nested:
                        lines.append(_render_comments(nested, indent + 1))
            return "\n".join(lines)

        result += _render_comments(data[1]["data"]["children"])
        return result
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def search_reddit(query: str, subreddit: str = "", limit: int = 10) -> str:
    """Search Reddit for posts matching a query.

    Args:
        query: Search query string.
        subreddit: Optional subreddit to restrict search to (without r/ prefix).
                   Leave empty to search all of Reddit.
        limit: Number of results to return (default: 10, max: 100).
    """
    limit = max(1, min(limit, 100))
    try:
        if subreddit:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params: dict[str, Any] = {
                "q": query,
                "restrict_sr": "1",
                "sort": "relevance",
                "limit": limit,
            }
        else:
            url = "https://www.reddit.com/search.json"
            params = {"q": query, "sort": "relevance", "limit": limit}

        data = _reddit_get(url, params=params)
        posts = [_fmt_post(c["data"]) for c in data["data"]["children"]]
        return "\n\n".join(posts) if posts else "No results found."
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def search_subreddits(query: str, limit: int = 10) -> str:
    """Find subreddits by topic or keyword.

    Args:
        query: Topic or keyword to search for (e.g. 'machine learning', 'homelab').
        limit: Number of subreddits to return (default: 10, max: 100).
    """
    limit = max(1, min(limit, 100))
    try:
        data = _reddit_get(
            "https://www.reddit.com/subreddits/search.json",
            params={"q": query, "limit": limit},
        )
        results = []
        for child in data["data"]["children"]:
            s = child["data"]
            subscribers = s.get("subscribers", 0)
            sub_str = f"{subscribers:,}" if subscribers else "?"
            results.append(
                f"r/{s.get('display_name', '?')}\n"
                f"Subscribers: {sub_str}\n"
                f"Description: {(s.get('public_description') or '(no description)').strip()[:200]}\n"
                f"URL: https://reddit.com{s.get('url', '')}\n"
                f"---"
            )
        return "\n\n".join(results) if results else "No subreddits found."
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def get_subreddit_info(subreddit: str) -> str:
    """Get metadata for a subreddit: subscriber count, description, rules, and creation date.

    Args:
        subreddit: Name of the subreddit (without r/ prefix).
    """
    try:
        data = _reddit_get(f"https://www.reddit.com/r/{subreddit}/about.json")
        s = data["data"]

        import datetime
        created_ts = s.get("created_utc", 0)
        created_date = datetime.datetime.utcfromtimestamp(created_ts).strftime("%Y-%m-%d") if created_ts else "?"

        subscribers = s.get("subscribers", 0)
        active = s.get("active_user_count", "?")

        result = (
            f"r/{s.get('display_name', subreddit)}\n"
            f"Subscribers: {subscribers:,}\n"
            f"Active users: {active}\n"
            f"Created: {created_date}\n"
            f"Type: {s.get('subreddit_type', '?')}\n"
            f"NSFW: {s.get('over18', False)}\n"
            f"\nDescription:\n{(s.get('public_description') or '(none)').strip()}\n"
        )

        # Fetch rules
        try:
            rules_data = _reddit_get(f"https://www.reddit.com/r/{subreddit}/about/rules.json")
            rules = rules_data.get("rules", [])
            if rules:
                result += "\nRules:\n"
                for i, rule in enumerate(rules[:10], 1):
                    result += f"  {i}. {rule.get('short_name', rule.get('description', ''))}\n"
        except Exception:
            pass  # Rules are optional — don't fail the whole tool

        return result
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def get_user_profile(username: str, include_posts: bool = True) -> str:
    """Get a Reddit user's profile: karma, account age, and recent posts.

    Args:
        username: Reddit username (without u/ prefix).
        include_posts: Whether to include recent posts (default: True).
    """
    try:
        import datetime

        data = _reddit_get(f"https://www.reddit.com/user/{username}/about.json")
        u = data["data"]

        created_ts = u.get("created_utc", 0)
        created_date = datetime.datetime.utcfromtimestamp(created_ts).strftime("%Y-%m-%d") if created_ts else "?"
        account_age_days = int((time.time() - created_ts) / 86400) if created_ts else 0

        result = (
            f"u/{u.get('name', username)}\n"
            f"Link karma: {u.get('link_karma', 0):,}\n"
            f"Comment karma: {u.get('comment_karma', 0):,}\n"
            f"Created: {created_date} ({account_age_days} days ago)\n"
            f"Verified email: {u.get('has_verified_email', False)}\n"
            f"NSFW profile: {u.get('over_18', False)}\n"
        )

        if include_posts:
            try:
                posts_data = _reddit_get(
                    f"https://www.reddit.com/user/{username}/submitted.json",
                    params={"limit": 5},
                )
                posts = posts_data["data"]["children"]
                if posts:
                    result += "\nRecent posts:\n"
                    for child in posts:
                        p = child["data"]
                        result += (
                            f"  - [{p.get('score', 0)} pts] r/{p.get('subreddit', '?')}: "
                            f"{p.get('title', '(no title)')[:100]}\n"
                            f"    https://reddit.com{p.get('permalink', '')}\n"
                        )
            except Exception:
                pass  # Posts are optional — don't fail the whole tool

        return result
    except Exception as exc:
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
