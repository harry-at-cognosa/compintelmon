import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_by_username(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": "admin", "password": "admin"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_by_email(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": "admin@localhost", "password": "admin"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": "admin", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": "nobody", "password": "nopass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 400
