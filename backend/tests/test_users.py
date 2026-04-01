import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_users_me(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/users/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_name"] == "admin"
    assert data["email"] == "admin@localhost"
    assert data["group_name"] == "System"
    assert data["is_superuser"] is True
    assert data["is_groupadmin"] is True
    assert data["is_subjectmanager"] is True


@pytest.mark.asyncio
async def test_users_me_regular_user(user_client: AsyncClient):
    resp = await user_client.get("/api/v1/users/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_name"] == "testuser"
    assert data["is_superuser"] is False
    assert data["is_groupadmin"] is False
    assert data["is_subjectmanager"] is False


@pytest.mark.asyncio
async def test_users_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401
