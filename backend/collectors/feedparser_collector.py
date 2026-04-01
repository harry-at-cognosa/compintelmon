"""
RSS/Atom feed collector using feedparser.
Covers: blog feeds, press releases, newsletters.
"""
import json

import feedparser

from backend.collectors.base import (
    CollectionResult, compute_content_hash, register_collector, resolve_url,
)


@register_collector("feedparser")
async def collect(config: dict) -> CollectionResult:
    url = resolve_url(config)
    if not url:
        return CollectionResult(
            status="error",
            error="No URL resolved from config (missing user_inputs?)",
        )

    max_entries = config.get("max_entries", 20)

    try:
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            # Feed parsing failed completely
            has_fallback = config.get("fallback_tool") and config.get("fallback_url_template")
            if has_fallback:
                return CollectionResult(
                    status="error",
                    error="empty_feed_try_fallback",
                )
            return CollectionResult(
                status="error",
                error=f"Failed to parse feed at {url}: {str(feed.bozo_exception)}",
            )

        if not feed.entries:
            has_fallback = config.get("fallback_tool") and config.get("fallback_url_template")
            if has_fallback:
                return CollectionResult(
                    status="error",
                    error="empty_feed_try_fallback",
                )
            return CollectionResult(
                status="ok",
                items=[],
                content_hash=compute_content_hash(""),
                raw_content="",
            )

        items = []
        for entry in feed.entries[:max_entries]:
            items.append({
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": getattr(entry, "published", ""),
                "summary": getattr(entry, "summary", "")[:500],
            })

        raw = json.dumps(items, default=str)
        content_hash = compute_content_hash(raw)

        return CollectionResult(
            status="ok",
            items=items,
            content_hash=content_hash,
            raw_content=raw,
        )

    except Exception as e:
        return CollectionResult(status="error", error=f"Error parsing feed {url}: {str(e)}")
