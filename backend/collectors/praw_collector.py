"""
Reddit collector using public JSON endpoints.
No API key required — uses Reddit's public .json search interface.
Rate-limited but sufficient for periodic competitive intelligence monitoring.
"""
import json
import httpx

from backend.collectors.base import (
    CollectionResult, compute_content_hash, register_collector,
)


@register_collector("praw")
async def collect(config: dict) -> CollectionResult:
    """Search Reddit using public JSON endpoints. No authentication needed."""

    # Build search query
    search_query = config.get("search_template", "")
    if not search_query:
        terms = config.get("reddit_search_terms", "")
        if isinstance(terms, list):
            search_query = " OR ".join(f'"{t}"' for t in terms)
        elif isinstance(terms, str) and terms:
            search_query = terms
        else:
            search_query = config.get("gsubject_name", "")

    if not search_query:
        return CollectionResult(status="error", error="No search query configured")

    sort = config.get("sort", "new")
    time_filter = config.get("time_filter", "day")
    max_results = min(config.get("max_results", 50), 100)  # Reddit caps at 100
    subreddits = config.get("subreddits", [])

    try:
        items = []
        async with httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": "CompIntelMon/0.1 (competitive intelligence monitor)"},
            follow_redirects=True,
        ) as client:
            if subreddits and isinstance(subreddits, list) and len(subreddits) > 0:
                # Search specific subreddits
                for sub_name in subreddits[:5]:
                    try:
                        url = f"https://www.reddit.com/r/{sub_name}/search.json"
                        params = {
                            "q": search_query,
                            "sort": sort,
                            "t": time_filter,
                            "limit": str(max_results),
                            "restrict_sr": "1",
                        }
                        resp = await client.get(url, params=params)
                        if resp.status_code == 200:
                            items.extend(_parse_listing(resp.json()))
                    except Exception:
                        continue
            else:
                # Search all of Reddit
                url = "https://www.reddit.com/search.json"
                params = {
                    "q": search_query,
                    "sort": sort,
                    "t": time_filter,
                    "limit": str(max_results),
                }
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    items = _parse_listing(resp.json())
                elif resp.status_code == 429:
                    return CollectionResult(
                        status="error",
                        error="Reddit rate limit hit. Try again later.",
                    )
                else:
                    return CollectionResult(
                        status="error",
                        error=f"Reddit returned HTTP {resp.status_code}",
                    )

        raw = json.dumps(items, default=str)
        content_hash = compute_content_hash(raw)

        return CollectionResult(
            status="ok",
            items=items,
            content_hash=content_hash,
            raw_content=raw,
        )

    except httpx.TimeoutException:
        return CollectionResult(status="error", error="Reddit request timed out")
    except Exception as e:
        return CollectionResult(status="error", error=f"Reddit error: {str(e)}")


def _parse_listing(data: dict) -> list[dict]:
    """Parse Reddit JSON listing response into structured items."""
    items = []
    children = data.get("data", {}).get("children", [])
    for child in children:
        post = child.get("data", {})
        if not post:
            continue
        items.append({
            "title": post.get("title", ""),
            "url": f"https://reddit.com{post.get('permalink', '')}",
            "subreddit": post.get("subreddit", ""),
            "author": post.get("author", "[deleted]"),
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "created_utc": post.get("created_utc", 0),
            "selftext": (post.get("selftext", "") or "")[:1000],
        })
    return items
