"""
Test fixtures for CompIntelMon backend.

Uses a separate test database (compintelmon_test).
Uses NullPool to avoid asyncpg connection contention in tests.
"""
import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Override database URL BEFORE importing backend modules
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/compintelmon_test",
)
TEST_DB_SYNC_URL = TEST_DB_URL.replace("+asyncpg", "+psycopg2")

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["DATABASE_SYNC_URL"] = TEST_DB_SYNC_URL

# Patch the session module to use NullPool before anything else imports it
import backend.db.session as session_mod

test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

# Replace the module-level engine and session factory
session_mod.sql_async_engine = test_engine
session_mod.SqlAsyncSession = TestSession

from backend.db import Base
from backend.db.models import ApiGroups, ApiSettings, PlaybookTemplates, User
from backend.auth.users import password_helper
from backend.db.playbook_defaults import PLAYBOOK_TEMPLATE_DEFAULTS


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables and seed test data."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSession() as session:
        session.add_all([
            ApiGroups(group_id=1, group_name="System"),
            ApiGroups(group_id=2, group_name="Default Group"),
        ])
        await session.flush()

        session.add(User(
            user_id=1,
            id=uuid.uuid4(),
            email="admin@localhost",
            user_name="admin",
            full_name="System Administrator",
            hashed_password=password_helper.hash("admin"),
            group_id=1,
            is_active=True,
            is_superuser=True,
            is_verified=True,
            is_groupadmin=True,
            is_subjectmanager=True,
        ))

        session.add(User(
            user_id=2,
            id=uuid.uuid4(),
            email="user@localhost",
            user_name="testuser",
            full_name="Test User",
            hashed_password=password_helper.hash("testpass"),
            group_id=2,
            is_active=True,
            is_superuser=False,
            is_verified=True,
            is_groupadmin=False,
            is_subjectmanager=False,
        ))

        session.add_all([
            ApiSettings(name="app_title", value="CompIntel Monitor"),
            ApiSettings(name="navbar_color", value="slate"),
            ApiSettings(name="instance_label", value="TEST"),
        ])

        # Seed playbook templates
        for tpl_data in PLAYBOOK_TEMPLATE_DEFAULTS:
            session.add(PlaybookTemplates(**tpl_data))

        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


def _get_app():
    """Get the FastAPI app with routers wired up."""
    from backend.app import app
    from backend.api import api_router

    existing_paths = {getattr(r, "path", "") for r in app.routes}
    if "/api/v1/users/me" not in existing_paths:
        app.include_router(api_router)

    return app


async def _login(app, username: str, password: str) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/auth/jwt/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
        return resp.json()["access_token"]


@pytest_asyncio.fixture
async def client():
    """Unauthenticated async HTTP client."""
    app = _get_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_client():
    """Authenticated client as admin (superuser)."""
    app = _get_app()
    token = await _login(app, "admin", "admin")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def user_client():
    """Authenticated client as regular user."""
    app = _get_app()
    token = await _login(app, "testuser", "testpass")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac
