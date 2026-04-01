import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webapp_options_no_auth(client: AsyncClient):
    """webapp_options is public — no auth required."""
    resp = await client.get("/api/v1/webapp_options")
    assert resp.status_code == 200
    data = resp.json()
    names = [s["name"] for s in data]
    assert "app_title" in names
    assert "navbar_color" in names
    assert "instance_label" in names


@pytest.mark.asyncio
async def test_settings_list_as_superuser(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_settings_list_as_regular_user(user_client: AsyncClient):
    """Regular users cannot access global settings."""
    resp = await user_client.get("/api/v1/settings")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_settings_upsert_as_superuser(admin_client: AsyncClient):
    resp = await admin_client.put(
        "/api/v1/settings",
        json={"name": "test_setting", "value": "test_value"},
    )
    assert resp.status_code == 200
    assert resp.json()["value"] == "test_value"
