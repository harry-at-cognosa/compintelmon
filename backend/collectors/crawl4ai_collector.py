"""
Web crawler/extractor using crawl4ai.
Covers: corporate websites, careers pages, documentation, review sites.
"""
from backend.collectors.base import (
    CollectionResult, compute_content_hash, register_collector, resolve_url,
)


@register_collector("crawl4ai")
async def collect(config: dict) -> CollectionResult:
    url = resolve_url(config)
    if not url:
        return CollectionResult(
            status="error",
            error="No URL resolved from config (missing user_inputs?)",
        )

    timeout = config.get("timeout_seconds", 30)

    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        browser_config = BrowserConfig(headless=True)
        run_config = CrawlerRunConfig(
            page_timeout=timeout * 1000,  # milliseconds
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)

        if not result.success:
            return CollectionResult(
                status="error",
                error=f"Crawl failed for {url}: {result.error_message or 'unknown error'}",
            )

        content = result.markdown or result.cleaned_html or ""
        if not content:
            return CollectionResult(
                status="error",
                error=f"No content extracted from {url}",
            )

        content_hash = compute_content_hash(content)

        return CollectionResult(
            status="ok",
            items=[{
                "url": url,
                "content_length": len(content),
                "title": getattr(result, "title", ""),
            }],
            content_hash=content_hash,
            raw_content=content,
        )

    except ImportError:
        return CollectionResult(
            status="error",
            error="crawl4ai not installed or browser not set up. Run: crawl4ai-setup",
        )
    except Exception as e:
        return CollectionResult(status="error", error=f"Error crawling {url}: {str(e)}")
