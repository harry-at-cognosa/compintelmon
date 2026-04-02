from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_get_session
from backend.db.models import User
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
