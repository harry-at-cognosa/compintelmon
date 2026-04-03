"""
Reddit collector using PRAW (Python Reddit API Wrapper).
Searches Reddit for mentions of a subject.
Requires reddit_client_id and reddit_client_secret in group_settings.
"""
import json
from functools import partial

from backend.collectors.base import (
    CollectionResult, compute_content_hash, register_collector,
)


def _collect_sync(config: dict) -> CollectionResult:
    """Synchronous Reddit collection (PRAW is sync-only)."""
    try:
        import praw
    except ImportError:
        return CollectionResult(status="error", error="praw not installed")

    client_id = config.get("reddit_client_id", "")
    client_secret = config.get("reddit_client_secret", "")

    if not client_id or not client_secret:
        return CollectionResult(
            status="error",
            error="Missing reddit_client_id or reddit_client_secret in group settings",
        )

    # Build search query
    search_query = config.get("search_template", "")
    if not search_query:
        # Try reddit_search_terms from user_inputs
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
    max_results = config.get("max_results", 50)
    subreddits = config.get("subreddits", [])

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="CompIntelMon/0.1",
        )

        items = []
        if subreddits and isinstance(subreddits, list) and len(subreddits) > 0:
            # Search specific subreddits
            for sub_name in subreddits[:5]:  # limit to 5 subreddits
                try:
                    subreddit = reddit.subreddit(sub_name)
                    for submission in subreddit.search(
                        search_query, sort=sort, time_filter=time_filter, limit=max_results
                    ):
                        items.append(_submission_to_dict(submission))
                except Exception:
                    continue
        else:
            # Search all of Reddit
            for submission in reddit.subreddit("all").search(
                search_query, sort=sort, time_filter=time_filter, limit=max_results
            ):
                items.append(_submission_to_dict(submission))

        raw = json.dumps(items, default=str)
        content_hash = compute_content_hash(raw)

        return CollectionResult(
            status="ok",
            items=items,
            content_hash=content_hash,
            raw_content=raw,
        )

    except Exception as e:
        return CollectionResult(status="error", error=f"Reddit API error: {str(e)}")


def _submission_to_dict(submission) -> dict:
    return {
        "title": submission.title,
        "url": f"https://reddit.com{submission.permalink}",
        "subreddit": str(submission.subreddit),
        "author": str(submission.author) if submission.author else "[deleted]",
        "score": submission.score,
        "num_comments": submission.num_comments,
        "created_utc": submission.created_utc,
        "selftext": (submission.selftext or "")[:1000],
    }


@register_collector("praw")
async def collect(config: dict) -> CollectionResult:
    """Async wrapper around synchronous PRAW calls."""
    import asyncio
    return await asyncio.to_thread(_collect_sync, config)
