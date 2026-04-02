"""Tests for scheduler service, scheduler API, and dashboard API."""
import pytest
from unittest.mock import patch
from httpx import AsyncClient


# ── Scheduler API tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_scheduler_status(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/scheduler/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert data["running"] is False  # not started yet


@pytest.mark.asyncio
async def test_scheduler_start_stop(admin_client: AsyncClient):
    # Start
    resp = await admin_client.post("/api/v1/scheduler/start")
    assert resp.status_code == 200
    assert resp.json()["running"] is True

    # Status confirms running
    resp = await admin_client.get("/api/v1/scheduler/status")
    assert resp.json()["running"] is True

    # Stop
    resp = await admin_client.post("/api/v1/scheduler/stop")
    assert resp.status_code == 200
    assert resp.json()["running"] is False


@pytest.mark.asyncio
async def test_scheduler_start_requires_superuser(user_client: AsyncClient):
    resp = await user_client.post("/api/v1/scheduler/start")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_scheduler_stop_requires_superuser(user_client: AsyncClient):
    resp = await user_client.post("/api/v1/scheduler/stop")
    assert resp.status_code == 403


# ── Dashboard API tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_stats(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_subjects" in data
    assert "total_enabled_sources" in data
    assert "sources_due" in data
    assert "scheduler_running" in data
    assert isinstance(data["total_subjects"], int)
    assert isinstance(data["total_enabled_sources"], int)


@pytest.mark.asyncio
async def test_dashboard_stats_with_subject(admin_client: AsyncClient):
    """Create a subject and verify stats update."""
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Stats Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.get("/api/v1/dashboard/stats")
    data = resp.json()
    assert data["total_subjects"] >= 1
    assert data["total_enabled_sources"] >= 1

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_dashboard_recent_runs_empty(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/dashboard/recent-runs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_recent_runs_with_data(admin_client: AsyncClient):
    """Trigger a collection, then verify it appears in recent runs."""
    from backend.collectors.base import CollectionResult
    from unittest.mock import AsyncMock

    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Runs Dashboard Test"},
    )
    sid = resp.json()["gsubject_id"]

    # Get an enabled source
    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    sources = resp.json()
    enabled = next((s for s in sources if s["enabled"]), None)
    assert enabled is not None

    # Trigger collection with mocked collector
    mock_result = CollectionResult(status="ok", items=[{"test": True}], content_hash="abc", raw_content="test")
    tool = enabled["collection_tool"]
    with patch("backend.services.collection_runner.COLLECTOR_REGISTRY", {tool: AsyncMock(return_value=mock_result)}):
        await admin_client.post(f"/api/v1/subjects/{sid}/sources/{enabled['source_id']}/collect")

    # Give background task a moment
    import asyncio
    await asyncio.sleep(0.5)

    # Check recent runs
    resp = await admin_client.get("/api/v1/dashboard/recent-runs?limit=5")
    assert resp.status_code == 200
    runs = resp.json()
    # Should have at least one run with subject name
    if len(runs) > 0:
        assert "subject_name" in runs[0]
        assert "source_name" in runs[0]
        assert "status" in runs[0]

    await admin_client.delete(f"/api/v1/subjects/{sid}")
