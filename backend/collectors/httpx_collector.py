"""
HTTP collector using httpx. Fetches a URL and returns the response content.
Covers: website pages, status pages, API endpoints, news searches.
"""
import httpx

from backend.collectors.base import (
    CollectionResult, compute_content_hash, register_collector, resolve_url,
)


@register_collector("httpx")
async def collect(config: dict) -> CollectionResult:
    url = resolve_url(config)
    if not url:
        return CollectionResult(
            status="error",
            error="No URL resolved from config (missing user_inputs?)",
        )

    timeout = config.get("timeout_seconds", 30)
    previous_hash = config.get("previous_hash", "")

    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True,
            headers={"User-Agent": "CompIntelMon/0.1"}
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        content = resp.text
        content_hash = compute_content_hash(content)

        if previous_hash and content_hash == previous_hash:
            return CollectionResult(
                status="no_change",
                content_hash=content_hash,
                raw_content=content,
            )

        return CollectionResult(
            status="ok",
            items=[{
                "url": url,
                "status_code": resp.status_code,
                "content_type": resp.headers.get("content-type", ""),
                "content_length": len(content),
            }],
            content_hash=content_hash,
            raw_content=content,
        )

    except httpx.TimeoutException:
        return CollectionResult(status="error", error=f"Timeout after {timeout}s fetching {url}")
    except httpx.HTTPStatusError as e:
        return CollectionResult(status="error", error=f"HTTP {e.response.status_code} from {url}")
    except Exception as e:
        return CollectionResult(status="error", error=f"Error fetching {url}: {str(e)}")
