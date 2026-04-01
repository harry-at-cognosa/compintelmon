"""Tests for the collection engine: collectors, runner, and API endpoints."""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient

from backend.collectors.base import (
    CollectionResult,
    interpolate_config,
    compute_content_hash,
    resolve_url,
)


# ── Unit tests: base utilities ────────────────────────────────


def test_interpolate_config():
    config = {"url_template": "{website_url}/blog", "tool": "crawl4ai"}
    user_inputs = {"website_url": "https://acme.com"}
    result = interpolate_config(config, user_inputs)
    assert result["url_template"] == "https://acme.com/blog"
    assert result["tool"] == "crawl4ai"


def test_interpolate_config_with_subject_metadata():
    config = {"search_template": '"{gsubject_name}"'}
    result = interpolate_config(config, {}, {"gsubject_name": "Acme Corp"})
    assert result["search_template"] == '"Acme Corp"'


def test_interpolate_config_missing_key():
    config = {"url_template": "{missing_url}"}
    result = interpolate_config(config, {})
    assert result["url_template"] == "{missing_url}"  # left as-is


def test_compute_content_hash():
    h1 = compute_content_hash("hello")
    h2 = compute_content_hash("hello")
    h3 = compute_content_hash("world")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # sha256 hex


def test_resolve_url_ok():
    assert resolve_url({"url_template": "https://acme.com"}) == "https://acme.com"


def test_resolve_url_unresolved():
    assert resolve_url({"url_template": "{website_url}"}) is None


def test_resolve_url_missing():
    assert resolve_url({}) is None


# ── Unit tests: httpx collector ───────────────────────────────


@pytest.mark.asyncio
async def test_httpx_collector_success():
    from backend.collectors.httpx_collector import collect

    mock_response = AsyncMock()
    mock_response.text = "<html>Hello World</html>"
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.raise_for_status = lambda: None

    with patch("backend.collectors.httpx_collector.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await collect({"url_template": "https://example.com", "timeout_seconds": 10})

    assert result.status == "ok"
    assert len(result.items) == 1
    assert result.content_hash != ""


@pytest.mark.asyncio
async def test_httpx_collector_no_url():
    from backend.collectors.httpx_collector import collect
    result = await collect({"url_template": "{missing}"})
    assert result.status == "error"
    assert "No URL" in (result.error or "")


# ── Unit tests: feedparser collector ──────────────────────────


@pytest.mark.asyncio
async def test_feedparser_collector_success():
    from backend.collectors.feedparser_collector import collect

    mock_feed = type("Feed", (), {
        "bozo": False,
        "entries": [
            type("Entry", (), {"title": "Post 1", "link": "https://example.com/1", "published": "2026-01-01", "summary": "Summary 1"})(),
            type("Entry", (), {"title": "Post 2", "link": "https://example.com/2", "published": "2026-01-02", "summary": "Summary 2"})(),
        ],
    })()

    with patch("backend.collectors.feedparser_collector.feedparser.parse", return_value=mock_feed):
        result = await collect({"url_template": "https://example.com/feed.xml"})

    assert result.status == "ok"
    assert len(result.items) == 2
    assert result.items[0]["title"] == "Post 1"


@pytest.mark.asyncio
async def test_feedparser_collector_empty_with_fallback():
    from backend.collectors.feedparser_collector import collect

    mock_feed = type("Feed", (), {"bozo": False, "entries": []})()

    with patch("backend.collectors.feedparser_collector.feedparser.parse", return_value=mock_feed):
        result = await collect({
            "url_template": "https://example.com/feed.xml",
            "fallback_tool": "crawl4ai",
            "fallback_url_template": "{blog_url}",
        })

    assert result.status == "error"
    assert result.error == "empty_feed_try_fallback"


# ── Integration tests: API endpoints ─────────────────────────


@pytest.mark.asyncio
async def test_collect_single_source(admin_client: AsyncClient):
    """Create a subject, then collect a single source."""
    # Create subject
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Collect Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    # Get sources and find one with httpx tool
    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    sources = resp.json()
    httpx_source = next((s for s in sources if s["collection_tool"] == "httpx"), None)
    assert httpx_source is not None

    # Mock the collector to avoid real HTTP
    mock_result = CollectionResult(
        status="ok", items=[{"url": "test"}], content_hash="abc123", raw_content="test content"
    )
    with patch("backend.services.collection_runner.COLLECTOR_REGISTRY", {"httpx": AsyncMock(return_value=mock_result)}):
        resp = await admin_client.post(
            f"/api/v1/subjects/{sid}/sources/{httpx_source['source_id']}/collect"
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"

    # Clean up
    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_collect_disabled_source_returns_400(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Disabled Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    sources = resp.json()
    # Disable a source first
    source = sources[0]
    await admin_client.put(
        f"/api/v1/subjects/{sid}/sources/{source['source_id']}",
        json={"enabled": False},
    )

    resp = await admin_client.post(
        f"/api/v1/subjects/{sid}/sources/{source['source_id']}/collect"
    )
    assert resp.status_code == 400

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_collect_all(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "topic", "gsubject_name": "Collect All Test"},
    )
    sid = resp.json()["gsubject_id"]

    with patch("backend.services.collection_runner.COLLECTOR_REGISTRY", {}):
        resp = await admin_client.post(f"/api/v1/subjects/{sid}/collect-all")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["runs"]) > 0

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_list_runs_empty(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Runs Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    source = resp.json()[0]

    resp = await admin_client.get(
        f"/api/v1/subjects/{sid}/sources/{source['source_id']}/runs"
    )
    assert resp.status_code == 200
    assert resp.json() == []

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_collect_rbac(user_client: AsyncClient, admin_client: AsyncClient):
    """Regular user cannot trigger collection."""
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "RBAC Collect Test"},
    )
    sid = resp.json()["gsubject_id"]

    # Regular user can't access this subject (different group)
    resp = await user_client.post(f"/api/v1/subjects/{sid}/collect-all")
    assert resp.status_code == 404

    await admin_client.delete(f"/api/v1/subjects/{sid}")
