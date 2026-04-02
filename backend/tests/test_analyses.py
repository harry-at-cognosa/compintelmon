"""Tests for analyses, reports, and group settings delete."""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient


# ── Analysis API tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_endpoint_returns_started(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Analysis Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    with patch("backend.api.analyses.run_analysis"):
        resp = await admin_client.post(f"/api/v1/subjects/{sid}/analyze")
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_analyze_requires_api_key(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "No Key Analysis"},
    )
    sid = resp.json()["gsubject_id"]

    with patch("backend.api.analyses.ANTHROPIC_API_KEY", ""):
        resp = await admin_client.post(f"/api/v1/subjects/{sid}/analyze")
    assert resp.status_code == 400

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_analyze_rbac(user_client: AsyncClient, admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "RBAC Analysis Test"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await user_client.post(f"/api/v1/subjects/{sid}/analyze")
    assert resp.status_code == 404

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_list_analyses_empty(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "List Analyses Test"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.get(f"/api/v1/subjects/{sid}/analyses")
    assert resp.status_code == 200
    assert resp.json() == []

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_analysis_lifecycle(admin_client: AsyncClient):
    """Create analysis directly via DB, verify it appears in API."""
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Lifecycle Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    # Create analysis directly
    from backend.db.session import SqlAsyncSession
    from backend.db.tables.analyses import AnalysesTable

    async with SqlAsyncSession() as session:
        at = AnalysesTable(session)
        analysis = await at.create(sid, "full")
        await at.update(
            analysis.analysis_id,
            status="ok",
            summary="Test summary",
            key_findings=[{"category": "web", "finding": "test finding", "severity": "high", "source_key": "website_main"}],
            signals=[{"signal_type": "test", "description": "test signal", "confidence": "medium", "source_key": "website_main"}],
            sources_analyzed=["website_main"],
        )
        aid = analysis.analysis_id

    # List
    resp = await admin_client.get(f"/api/v1/subjects/{sid}/analyses")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Get single
    resp = await admin_client.get(f"/api/v1/subjects/{sid}/analyses/{aid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == "Test summary"
    assert len(data["key_findings"]) == 1
    assert len(data["signals"]) == 1

    await admin_client.delete(f"/api/v1/subjects/{sid}")


# ── Report API tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_report_endpoint(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Report Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    # Create a completed analysis
    from backend.db.session import SqlAsyncSession
    from backend.db.tables.analyses import AnalysesTable

    async with SqlAsyncSession() as session:
        at = AnalysesTable(session)
        analysis = await at.create(sid, "full")
        await at.update(analysis.analysis_id, status="ok", summary="Test")
        aid = analysis.analysis_id

    with patch("backend.api.analyses.run_report"):
        resp = await admin_client.post(
            f"/api/v1/subjects/{sid}/analyses/{aid}/report",
            json={"report_type": "battlecard"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_list_reports_empty(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Reports List Test"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.get(f"/api/v1/subjects/{sid}/reports")
    assert resp.status_code == 200
    assert resp.json() == []

    await admin_client.delete(f"/api/v1/subjects/{sid}")


# ── Group Settings DELETE test ────────────────────────────────


@pytest.mark.asyncio
async def test_group_settings_delete(admin_client: AsyncClient):
    """Test the new DELETE endpoint for group settings."""
    # Create a setting
    resp = await admin_client.put(
        "/api/v1/group_settings/1",
        json={"name": "test_delete_setting", "value": "test_value"},
    )
    assert resp.status_code == 200

    # Delete it
    resp = await admin_client.delete("/api/v1/group_settings/1/test_delete_setting")
    assert resp.status_code == 204

    # Verify it's gone
    resp = await admin_client.get("/api/v1/group_settings/1")
    names = [s["name"] for s in resp.json()]
    assert "test_delete_setting" not in names
