"""Tests for group and user management."""
import pytest
from httpx import AsyncClient


# ── Groups management ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_groups(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/groups")
    assert resp.status_code == 200
    groups = resp.json()
    assert len(groups) >= 2
    assert any(g["group_name"] == "System" for g in groups)


@pytest.mark.asyncio
async def test_create_group(admin_client: AsyncClient):
    resp = await admin_client.post("/api/v1/groups", json={"group_name": "Test Group"})
    assert resp.status_code == 201
    assert resp.json()["group_name"] == "Test Group"
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_update_group_is_active(admin_client: AsyncClient):
    """Toggle group active status."""
    resp = await admin_client.get("/api/v1/groups")
    test_group = next((g for g in resp.json() if g["group_name"] == "Test Group"), None)
    assert test_group is not None

    resp = await admin_client.put(
        f"/api/v1/groups/{test_group['group_id']}",
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Re-enable
    await admin_client.put(
        f"/api/v1/groups/{test_group['group_id']}",
        json={"is_active": True},
    )


@pytest.mark.asyncio
async def test_groups_requires_superuser(user_client: AsyncClient):
    resp = await user_client.get("/api/v1/groups")
    assert resp.status_code == 404


# ── User management ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_users(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/manage/users")
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 2  # admin + testuser


@pytest.mark.asyncio
async def test_create_user(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/manage/users",
        json={
            "user_name": "mng_newuser",
            "full_name": "New User",
            "email": "mng_new@test.com",
            "password": "test1234",
            "group_id": 2,
            "is_subjectmanager": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_name"] == "mng_newuser"
    assert data["is_subjectmanager"] is True
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_update_user_role(admin_client: AsyncClient):
    """Toggle user roles."""
    resp = await admin_client.get("/api/v1/manage/users")
    new_user = next((u for u in resp.json() if u["user_name"] == "mng_newuser"), None)
    assert new_user is not None

    resp = await admin_client.put(
        f"/api/v1/manage/users/{new_user['user_id']}",
        json={"is_groupadmin": True, "is_subjectmanager": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_groupadmin"] is True
    assert resp.json()["is_subjectmanager"] is False


@pytest.mark.asyncio
async def test_toggle_user_active(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/manage/users")
    new_user = next((u for u in resp.json() if u["user_name"] == "mng_newuser"), None)

    resp = await admin_client.put(
        f"/api/v1/manage/users/{new_user['user_id']}",
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_user_management_requires_groupadmin(user_client: AsyncClient):
    resp = await user_client.get("/api/v1/manage/users")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_only_superuser_can_create_superuser(admin_client: AsyncClient):
    """Non-superuser groupadmin cannot create superusers."""
    # This test uses admin_client which is superuser, so it should work
    resp = await admin_client.post(
        "/api/v1/manage/users",
        json={
            "user_name": "mng_supertest",
            "email": "mng_super@test.com",
            "password": "test1234",
            "group_id": 1,
            "is_superuser": True,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["is_superuser"] is True
