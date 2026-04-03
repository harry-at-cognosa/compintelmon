import os
import shutil

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import ANTHROPIC_API_KEY, WORK_DIR
from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.tables.group_settings import GroupSettingsTable
from backend.auth.users import current_active_user
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.db.tables.subject_sources import SubjectSourcesTable
from backend.db.tables.subject_source_runs import SubjectSourceRunsTable
from backend.services.scheduler_service import scheduler
from backend.db.schemas import DashboardStats, RecentRunRead

router_dashboard = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router_dashboard.get("/stats", response_model=DashboardStats)
async def get_stats(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    subjects_count = await GroupSubjectsTable(session).count_all()
    enabled_count = await SubjectSourcesTable(session).count_enabled()
    due_count = await SubjectSourcesTable(session).count_due()
    return DashboardStats(
        total_subjects=subjects_count,
        total_enabled_sources=enabled_count,
        sources_due=due_count,
        scheduler_running=scheduler.is_running,
    )


@router_dashboard.get("/recent-runs", response_model=list[RecentRunRead])
async def get_recent_runs(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    return await SubjectSourceRunsTable(session).get_recent_runs_global(limit=limit)


class HealthCheck(BaseModel):
    name: str
    status: str  # "ok", "warning", "error"
    detail: str


class SystemHealth(BaseModel):
    checks: list[HealthCheck]


@router_dashboard.get("/health", response_model=SystemHealth)
async def get_health(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    checks = []

    # PostgreSQL
    try:
        await session.execute(text("SELECT 1"))
        checks.append(HealthCheck(name="PostgreSQL", status="ok", detail="Connected"))
    except Exception as e:
        checks.append(HealthCheck(name="PostgreSQL", status="error", detail=str(e)[:100]))

    # Anthropic API Key
    if ANTHROPIC_API_KEY and len(ANTHROPIC_API_KEY) > 10:
        checks.append(HealthCheck(name="Anthropic API Key", status="ok", detail=f"Configured (ends ...{ANTHROPIC_API_KEY[-4:]})"))
    elif ANTHROPIC_API_KEY:
        checks.append(HealthCheck(name="Anthropic API Key", status="warning", detail="Key seems too short"))
    else:
        checks.append(HealthCheck(name="Anthropic API Key", status="error", detail="Not configured in .env"))

    # Chromium (for crawl4ai)
    try:
        import subprocess
        result = subprocess.run(["which", "chromium"], capture_output=True, timeout=5)
        # Also check playwright's chromium
        playwright_path = os.path.expanduser("~/Library/Caches/ms-playwright")
        if os.path.isdir(playwright_path) and any("chromium" in d for d in os.listdir(playwright_path)):
            checks.append(HealthCheck(name="Chromium (crawl4ai)", status="ok", detail="Playwright Chromium installed"))
        elif result.returncode == 0:
            checks.append(HealthCheck(name="Chromium (crawl4ai)", status="ok", detail="System Chromium found"))
        else:
            checks.append(HealthCheck(name="Chromium (crawl4ai)", status="warning", detail="Not found — run: python3 -m playwright install chromium"))
    except Exception:
        checks.append(HealthCheck(name="Chromium (crawl4ai)", status="warning", detail="Could not check"))

    # Reddit API credentials
    group_settings = await GroupSettingsTable(session).get_all_for_group(user.group_id)
    gs_map = {gs.name: gs.value for gs in group_settings}
    if gs_map.get("reddit_client_id") and gs_map.get("reddit_client_secret"):
        checks.append(HealthCheck(name="Reddit API", status="ok", detail="Credentials configured"))
    else:
        missing = []
        if not gs_map.get("reddit_client_id"):
            missing.append("reddit_client_id")
        if not gs_map.get("reddit_client_secret"):
            missing.append("reddit_client_secret")
        checks.append(HealthCheck(name="Reddit API", status="warning", detail=f"Missing: {', '.join(missing)}"))

    # Data directory
    data_dir = os.path.join(WORK_DIR, "data")
    if os.path.isdir(data_dir):
        total, used, free = shutil.disk_usage(data_dir)
        free_gb = free / (1024 ** 3)
        status = "ok" if free_gb > 1 else "warning"
        checks.append(HealthCheck(name="Data Storage", status=status, detail=f"{free_gb:.1f} GB free"))
    else:
        checks.append(HealthCheck(name="Data Storage", status="ok", detail="data/ directory will be created on first collection"))

    return SystemHealth(checks=checks)
