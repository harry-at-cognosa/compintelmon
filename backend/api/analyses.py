from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import ANTHROPIC_API_KEY
from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.schemas import (
    AnalysisRead, AnalyzeResponse,
    ReportRead, GenerateReportRequest, GenerateReportResponse,
)
from backend.db.tables.analyses import AnalysesTable
from backend.db.tables.reports import ReportsTable
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.auth.users import current_active_user
from backend.services.analysis_runner import run_analysis
from backend.services.report_runner import run_report

router_analyses = APIRouter()


def _require_subjectmanager_or_above(user: User):
    if not (user.is_subjectmanager or user.is_groupadmin or user.is_superuser):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


async def _get_subject_or_404(session: AsyncSession, gsubject_id: int, user: User):
    subject = await GroupSubjectsTable(session).get_by_id(gsubject_id)
    if subject is None or subject.deleted == 1:
        raise HTTPException(status_code=404, detail="Subject not found")
    if not user.is_superuser and subject.group_id != user.group_id:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


# ── Analyses ──────────────────────────────────────────────────


@router_analyses.post("/subjects/{gsubject_id}/analyze", response_model=AnalyzeResponse)
async def analyze_subject(
    gsubject_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """Trigger Fusion analysis for a subject's collected data."""
    _require_subjectmanager_or_above(user)
    await _get_subject_or_404(session, gsubject_id, user)

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not configured")

    background_tasks.add_task(run_analysis, gsubject_id)
    return AnalyzeResponse(analysis_id=0, status="started", message="Analysis started")


@router_analyses.get("/subjects/{gsubject_id}/analyses", response_model=list[AnalysisRead])
async def list_analyses(
    gsubject_id: int,
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    await _get_subject_or_404(session, gsubject_id, user)
    return await AnalysesTable(session).get_by_subject(gsubject_id, limit=limit)


@router_analyses.get("/subjects/{gsubject_id}/analyses/{analysis_id}", response_model=AnalysisRead)
async def get_analysis(
    gsubject_id: int,
    analysis_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    await _get_subject_or_404(session, gsubject_id, user)
    analysis = await AnalysesTable(session).get_by_id(analysis_id)
    if analysis is None or analysis.gsubject_id != gsubject_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


# ── Reports ───────────────────────────────────────────────────


@router_analyses.post(
    "/subjects/{gsubject_id}/analyses/{analysis_id}/report",
    response_model=GenerateReportResponse,
)
async def generate_report(
    gsubject_id: int,
    analysis_id: int,
    payload: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """Generate a report from an analysis."""
    _require_subjectmanager_or_above(user)
    await _get_subject_or_404(session, gsubject_id, user)

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not configured")

    analysis = await AnalysesTable(session).get_by_id(analysis_id)
    if analysis is None or analysis.gsubject_id != gsubject_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.status != "ok":
        raise HTTPException(status_code=400, detail="Analysis not complete")

    background_tasks.add_task(run_report, analysis_id, gsubject_id, payload.report_type)
    return GenerateReportResponse(report_id=0, status="started", message="Report generation started")


@router_analyses.get("/subjects/{gsubject_id}/reports", response_model=list[ReportRead])
async def list_reports(
    gsubject_id: int,
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    await _get_subject_or_404(session, gsubject_id, user)
    return await ReportsTable(session).get_by_subject(gsubject_id, limit=limit)


@router_analyses.get("/subjects/{gsubject_id}/reports/{report_id}", response_model=ReportRead)
async def get_report(
    gsubject_id: int,
    report_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    await _get_subject_or_404(session, gsubject_id, user)
    report = await ReportsTable(session).get_by_id(report_id)
    if report is None or report.gsubject_id != gsubject_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
