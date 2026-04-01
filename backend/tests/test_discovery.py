"""Tests for the CrewAI Signal Discovery Agent and discovery runner."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient

from backend.agents.signal_discovery import _parse_discovery_result, _build_prompt


# ── Unit tests: parsing and prompt ────────────────────────────


def test_parse_discovery_result_clean_json():
    raw = '{"website_main": {"website_url": "https://stripe.com"}, "website_blog": {"blog_url": "https://stripe.com/blog"}}'
    result = _parse_discovery_result(raw)
    assert result["website_main"]["website_url"] == "https://stripe.com"
    assert result["website_blog"]["blog_url"] == "https://stripe.com/blog"


def test_parse_discovery_result_with_markdown():
    raw = '```json\n{"website_main": {"website_url": "https://acme.com"}}\n```'
    result = _parse_discovery_result(raw)
    assert result["website_main"]["website_url"] == "https://acme.com"


def test_parse_discovery_result_with_nulls():
    raw = '{"website_main": {"website_url": "https://acme.com"}, "regulatory_sec": {"sec_cik": null, "ticker_symbol": null}}'
    result = _parse_discovery_result(raw)
    assert "website_main" in result
    assert "regulatory_sec" not in result  # all null values filtered out


def test_parse_discovery_result_garbage():
    raw = "I couldn't find any URLs for this company."
    result = _parse_discovery_result(raw)
    assert result == {}


def test_build_prompt_includes_sources():
    sources_info = [
        {
            "source_id": 1,
            "category_key": "website_main",
            "category_name": "Corporate Website",
            "user_inputs_schema": {
                "type": "object",
                "required": ["website_url"],
                "properties": {"website_url": {"type": "string", "title": "Company Website URL"}},
            },
        },
    ]
    prompt = _build_prompt("Acme Corp", "company", sources_info)
    assert "Acme Corp" in prompt
    assert "website_main" in prompt
    assert "Corporate Website" in prompt
    assert "website_url" in prompt


# ── Integration tests: API endpoint ──────────────────────────


@pytest.mark.asyncio
async def test_discover_endpoint_returns_started(admin_client: AsyncClient):
    """POST discover triggers background task and returns started."""
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Discover Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    with patch("backend.api.sources.run_discovery"):
        resp = await admin_client.post(f"/api/v1/subjects/{sid}/discover")
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_discover_endpoint_requires_api_key(admin_client: AsyncClient):
    """Without ANTHROPIC_API_KEY, discover returns 400."""
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "No Key Test"},
    )
    sid = resp.json()["gsubject_id"]

    with patch("backend.api.sources.ANTHROPIC_API_KEY", ""):
        resp = await admin_client.post(f"/api/v1/subjects/{sid}/discover")
    assert resp.status_code == 400
    assert "ANTHROPIC_API_KEY" in resp.json()["detail"]

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_discover_endpoint_rbac(user_client: AsyncClient, admin_client: AsyncClient):
    """Regular user cannot trigger discovery."""
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "RBAC Discover Test"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await user_client.post(f"/api/v1/subjects/{sid}/discover")
    assert resp.status_code == 404

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_discovery_updates_user_inputs(admin_client: AsyncClient):
    """End-to-end: mock agent, verify sources get populated."""
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "E2E Discover Corp"},
    )
    sid = resp.json()["gsubject_id"]

    # Verify sources start with empty user_inputs
    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    sources = resp.json()
    assert all(not s["user_inputs"] for s in sources)

    # Mock the agent to return known values
    mock_result = {
        "website_main": {"website_url": "https://e2e-discover.com"},
        "website_blog": {"blog_url": "https://e2e-discover.com/blog"},
        "social_twitter": {"twitter_handle": "e2ediscover"},
    }

    with patch(
        "backend.services.discovery_runner.run_discovery",
    ) as mock_agent_run:
        # We need to actually run the inner function with mocked agent
        pass

    # For this test, directly call the runner with a mocked agent
    from backend.services.discovery_runner import _run_discovery_inner
    from backend.db.session import SqlAsyncSession

    with patch("backend.agents.signal_discovery.run_discovery", return_value=mock_result):
        async with SqlAsyncSession() as session:
            await _run_discovery_inner(session, sid)

    # Verify sources got updated
    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    sources = resp.json()
    website_main = next((s for s in sources if s["category_key"] == "website_main"), None)
    assert website_main is not None
    assert website_main["user_inputs"].get("website_url") == "https://e2e-discover.com"

    blog = next((s for s in sources if s["category_key"] == "website_blog"), None)
    assert blog is not None
    assert blog["user_inputs"].get("blog_url") == "https://e2e-discover.com/blog"

    await admin_client.delete(f"/api/v1/subjects/{sid}")
