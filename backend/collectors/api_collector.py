"""
API-based collector for public JSON endpoints.
Handles: GitHub, Hacker News, SEC EDGAR, Wikipedia, USPTO PatentsView.
Each API has its own handler function dispatched by the 'api' field in collection_config.
"""
import json
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import httpx

from backend.collectors.base import (
    CollectionResult, compute_content_hash, register_collector,
)

USER_AGENT = "CompIntelMon/0.1 (competitive-intelligence-monitor; contact: admin@compintelmon.local)"

# API handler registry
_API_HANDLERS: dict[str, callable] = {}


def api_handler(name: str):
    def decorator(func):
        _API_HANDLERS[name] = func
        return func
    return decorator


@register_collector("api")
async def collect(config: dict) -> CollectionResult:
    """Dispatch to the appropriate API handler based on config['api']."""
    api_name = config.get("api", "")
    handler = _API_HANDLERS.get(api_name)
    if not handler:
        return CollectionResult(status="error", error=f"Unknown API: {api_name}")
    return await handler(config)


# ── GitHub ────────────────────────────────────────────────────


@api_handler("github")
async def _github(config: dict) -> CollectionResult:
    org = config.get("github_org", "") or config.get("gsubject_name", "")
    if not org:
        return CollectionResult(status="error", error="No github_org configured")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }
    token = config.get("github_token", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            # Try as org first, fall back to user search
            resp = await client.get(f"https://api.github.com/orgs/{quote(org)}/repos?sort=updated&per_page=10")
            if resp.status_code == 404:
                resp = await client.get(f"https://api.github.com/search/repositories?q=org:{quote(org)}&sort=updated&per_page=10")
                if resp.status_code == 200:
                    data = resp.json()
                    repos = data.get("items", [])
                else:
                    return CollectionResult(status="error", error=f"GitHub: HTTP {resp.status_code}")
            elif resp.status_code == 200:
                repos = resp.json()
            else:
                return CollectionResult(status="error", error=f"GitHub: HTTP {resp.status_code}")

        items = [{
            "name": r.get("full_name", ""),
            "description": (r.get("description") or "")[:200],
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "updated_at": r.get("updated_at", ""),
            "language": r.get("language", ""),
            "url": r.get("html_url", ""),
        } for r in repos[:10]]

        raw = json.dumps(items, default=str)
        return CollectionResult(status="ok", items=items, content_hash=compute_content_hash(raw), raw_content=raw)
    except Exception as e:
        return CollectionResult(status="error", error=f"GitHub error: {str(e)}")


# ── Hacker News (Algolia API) ─────────────────────────────────


@api_handler("hn_algolia")
async def _hacker_news(config: dict) -> CollectionResult:
    query = config.get("hn_search_terms", "") or config.get("gsubject_name", "")
    if not query:
        return CollectionResult(status="error", error="No search terms configured")

    max_results = min(config.get("max_results", 20), 50)
    # Search last 7 days by default
    since = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())

    try:
        async with httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={
                    "query": query,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{since}",
                    "hitsPerPage": str(max_results),
                },
            )
            resp.raise_for_status()
            data = resp.json()

        hits = data.get("hits", [])
        items = [{
            "title": h.get("title", ""),
            "url": h.get("url", ""),
            "hn_url": f"https://news.ycombinator.com/item?id={h.get('objectID', '')}",
            "points": h.get("points", 0),
            "num_comments": h.get("num_comments", 0),
            "author": h.get("author", ""),
            "created_at": h.get("created_at", ""),
        } for h in hits]

        raw = json.dumps(items, default=str)
        return CollectionResult(status="ok", items=items, content_hash=compute_content_hash(raw), raw_content=raw)
    except Exception as e:
        return CollectionResult(status="error", error=f"Hacker News error: {str(e)}")


# ── SEC EDGAR ─────────────────────────────────────────────────


@api_handler("edgar")
async def _sec_edgar(config: dict) -> CollectionResult:
    query = config.get("sec_company_name", "") or config.get("ticker_symbol", "") or config.get("gsubject_name", "")
    if not query:
        return CollectionResult(status="error", error="No company name or ticker configured")

    forms = config.get("forms", "10-K,10-Q,8-K")

    try:
        async with httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(
                "https://efts.sec.gov/LATEST/search-index",
                params={
                    "q": f'"{query}"',
                    "forms": forms,
                    "dateRange": "custom",
                    "startdt": (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d"),
                    "enddt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                },
            )
            if resp.status_code != 200:
                return CollectionResult(status="error", error=f"EDGAR: HTTP {resp.status_code}")
            data = resp.json()

        filings = data.get("hits", {}).get("hits", [])
        items = []
        for f in filings[:20]:
            src = f.get("_source", {})
            display_names = src.get("display_names", [])
            root_forms = src.get("root_forms", [])
            items.append({
                "filing_type": root_forms[0] if root_forms else "",
                "entity": display_names[0] if display_names else "",
                "filed_at": src.get("file_date", ""),
                "url": f"https://www.sec.gov/Archives/edgar/data/{f.get('_id', '')}",
            })

        raw = json.dumps(items, default=str)
        return CollectionResult(status="ok", items=items, content_hash=compute_content_hash(raw), raw_content=raw)
    except Exception as e:
        return CollectionResult(status="error", error=f"EDGAR error: {str(e)}")


# ── Wikipedia ─────────────────────────────────────────────────


@api_handler("wikipedia")
async def _wikipedia(config: dict) -> CollectionResult:
    pages = config.get("wikipedia_pages", [])
    if isinstance(pages, str):
        pages = [pages]
    if not pages:
        # Try to find a page by subject name
        subject = config.get("gsubject_name", "")
        if subject:
            pages = [subject.replace(" ", "_")]
        else:
            return CollectionResult(status="error", error="No Wikipedia pages configured")

    try:
        items = []
        async with httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}) as client:
            for page_title in pages[:5]:
                resp = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "titles": page_title,
                        "prop": "revisions|extracts",
                        "rvprop": "timestamp|comment|user",
                        "rvlimit": "10",
                        "exintro": "true",
                        "explaintext": "true",
                        "format": "json",
                    },
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                pages_data = data.get("query", {}).get("pages", {})
                for page_id, page in pages_data.items():
                    if page_id == "-1":
                        continue  # page not found
                    extract = page.get("extract", "")[:500]
                    revisions = page.get("revisions", [])
                    items.append({
                        "title": page.get("title", ""),
                        "extract": extract,
                        "url": f"https://en.wikipedia.org/wiki/{quote(page.get('title', ''))}",
                        "recent_revisions": len(revisions),
                        "last_edited": revisions[0].get("timestamp", "") if revisions else "",
                        "last_editor": revisions[0].get("user", "") if revisions else "",
                    })

        raw = json.dumps(items, default=str)
        return CollectionResult(status="ok", items=items, content_hash=compute_content_hash(raw), raw_content=raw)
    except Exception as e:
        return CollectionResult(status="error", error=f"Wikipedia error: {str(e)}")


# ── USPTO PatentsView ─────────────────────────────────────────


@api_handler("patents")
async def _patents(config: dict) -> CollectionResult:
    assignee = config.get("patent_assignee_name", "") or config.get("gsubject_name", "")
    if not assignee:
        return CollectionResult(status="error", error="No patent assignee name configured")

    try:
        # Use Google Patents search (public, no auth)
        async with httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            resp = await client.get(
                f"https://patents.google.com/xhr/query",
                params={
                    "url": f"assignee={quote(assignee)}&oq={quote(assignee)}&num=20&sort=new",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", {}).get("cluster", [])
                items = []
                for cluster in results:
                    for result in cluster.get("result", []):
                        patent = result.get("patent", {})
                        items.append({
                            "patent_id": patent.get("publication_number", ""),
                            "title": patent.get("title", ""),
                            "date": patent.get("filing_date", ""),
                            "url": f"https://patents.google.com/patent/{patent.get('publication_number', '')}",
                        })
                raw = json.dumps(items[:20], default=str)
                return CollectionResult(status="ok", items=items[:20], content_hash=compute_content_hash(raw), raw_content=raw)
            else:
                return CollectionResult(status="error", error=f"Google Patents: HTTP {resp.status_code}")
    except Exception as e:
        return CollectionResult(status="error", error=f"Patents error: {str(e)}")


# ── Google News (via RSS) ─────────────────────────────────────


@api_handler("google_news")
async def _google_news(config: dict) -> CollectionResult:
    """Search Google News via their RSS feed (returns XML, parsed as items)."""
    query = config.get("news_search_terms", "") or config.get("gsubject_name", "")
    if isinstance(query, list):
        query = " ".join(query)
    if not query:
        return CollectionResult(status="error", error="No news search terms configured")

    try:
        import feedparser

        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)

        items = []
        for entry in feed.entries[:20]:
            items.append({
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": getattr(entry, "published", ""),
                "source": getattr(entry, "source", {}).get("title", "") if hasattr(entry, "source") else "",
                "summary": (getattr(entry, "summary", "") or "")[:300],
            })

        raw = json.dumps(items, default=str)
        return CollectionResult(status="ok", items=items, content_hash=compute_content_hash(raw), raw_content=raw)
    except Exception as e:
        return CollectionResult(status="error", error=f"Google News error: {str(e)}")
