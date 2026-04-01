from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.schemas import (
    PlaybookTemplateRead,
    SubjectSourceRead, SubjectSourceCreate, SubjectSourceUpdate,
    SubjectSourceRunRead, CollectResponse, CollectAllResponse,
    DiscoverResponse,
)
from backend.db.tables.playbook_templates import PlaybookTemplatesTable
from backend.db.tables.subject_sources import SubjectSourcesTable
from backend.db.tables.subject_source_runs import SubjectSourceRunsTable
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.auth.users import current_active_user
from backend.config import ANTHROPIC_API_KEY
from backend.services.collection_runner import run_collection
from backend.services.discovery_runner import run_discovery

router_sources = APIRouter()


def _require_subjectmanager_or_above(user: User):
    if not (user.is_subjectmanager or user.is_groupadmin or user.is_superuser):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


async def _get_subject_or_404(session: AsyncSession, gsubject_id: int, user: User):
    """Fetch subject, enforce group isolation."""
    subject = await GroupSubjectsTable(session).get_by_id(gsubject_id)
    if subject is None or subject.deleted == 1:
        raise HTTPException(status_code=404, detail="Subject not found")
    if not user.is_superuser and subject.group_id != user.group_id:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


# ── Playbook Templates ────────────────────────────────────────


@router_sources.get("/playbook-templates", response_model=list[PlaybookTemplateRead])
async def list_templates(
    subject_type: str | None = Query(None, description="Filter by subject type"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    table = PlaybookTemplatesTable(session)
    if subject_type:
        return await table.get_by_subject_type(subject_type)
    return await table.get_all()


# ── Subject Sources ───────────────────────────────────────────


@router_sources.get("/subjects/{gsubject_id}/sources", response_model=list[SubjectSourceRead])
async def list_sources(
    gsubject_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    await _get_subject_or_404(session, gsubject_id, user)
    return await SubjectSourcesTable(session).get_by_subject(gsubject_id)


@router_sources.put("/subjects/{gsubject_id}/sources/{source_id}", response_model=SubjectSourceRead)
async def update_source(
    gsubject_id: int,
    source_id: int,
    payload: SubjectSourceUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_subjectmanager_or_above(user)
    await _get_subject_or_404(session, gsubject_id, user)

    source = await SubjectSourcesTable(session).get_by_id(source_id)
    if source is None or source.deleted == 1 or source.gsubject_id != gsubject_id:
        raise HTTPException(status_code=404, detail="Source not found")

    updated = await SubjectSourcesTable(session).update_source(
        source_id,
        enabled=payload.enabled,
        frequency_minutes=payload.frequency_minutes,
        user_inputs=payload.user_inputs,
    )
    return updated


@router_sources.post("/subjects/{gsubject_id}/sources", response_model=SubjectSourceRead, status_code=201)
async def create_custom_source(
    gsubject_id: int,
    payload: SubjectSourceCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_subjectmanager_or_above(user)
    await _get_subject_or_404(session, gsubject_id, user)

    return await SubjectSourcesTable(session).create_source(
        gsubject_id=gsubject_id,
        category_key=payload.category_key,
        category_name=payload.category_name,
        collection_tool=payload.collection_tool,
        enabled=payload.enabled,
        frequency_minutes=payload.frequency_minutes,
        collection_config=payload.collection_config,
        signal_instructions=payload.signal_instructions,
        user_inputs=payload.user_inputs,
    )


@router_sources.delete("/subjects/{gsubject_id}/sources/{source_id}", status_code=204)
async def delete_source(
    gsubject_id: int,
    source_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_subjectmanager_or_above(user)
    await _get_subject_or_404(session, gsubject_id, user)

    source = await SubjectSourcesTable(session).get_by_id(source_id)
    if source is None or source.deleted == 1 or source.gsubject_id != gsubject_id:
        raise HTTPException(status_code=404, detail="Source not found")

    await SubjectSourcesTable(session).soft_delete_source(source_id)


# ── Collection Runs ──────────────────────────────────────────


@router_sources.post(
    "/subjects/{gsubject_id}/sources/{source_id}/collect",
    response_model=CollectResponse,
)
async def collect_source(
    gsubject_id: int,
    source_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """Trigger collection for a single source."""
    _require_subjectmanager_or_above(user)
    await _get_subject_or_404(session, gsubject_id, user)

    source = await SubjectSourcesTable(session).get_by_id(source_id)
    if source is None or source.deleted == 1 or source.gsubject_id != gsubject_id:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.enabled:
        raise HTTPException(status_code=400, detail="Source is disabled")

    background_tasks.add_task(run_collection, source_id)
    return CollectResponse(run_id=0, status="started", message="Collection started")


@router_sources.post(
    "/subjects/{gsubject_id}/collect-all",
    response_model=CollectAllResponse,
)
async def collect_all(
    gsubject_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """Trigger collection for all enabled sources of a subject."""
    _require_subjectmanager_or_above(user)
    await _get_subject_or_404(session, gsubject_id, user)

    sources = await SubjectSourcesTable(session).get_enabled_by_subject(gsubject_id)
    runs = []
    for source in sources:
        background_tasks.add_task(run_collection, source.source_id)
        runs.append(CollectResponse(
            run_id=0, status="started", message=f"Started: {source.category_name}"
        ))

    return CollectAllResponse(
        runs=runs,
        message=f"Started {len(runs)} collections",
    )


@router_sources.post(
    "/subjects/{gsubject_id}/discover",
    response_model=DiscoverResponse,
)
async def discover_sources(
    gsubject_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """Trigger auto-discovery of source URLs for a subject using CrewAI."""
    _require_subjectmanager_or_above(user)
    await _get_subject_or_404(session, gsubject_id, user)

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not configured in .env")

    background_tasks.add_task(run_discovery, gsubject_id)
    return DiscoverResponse(status="started", message="Auto-discovery started")


@router_sources.get(
    "/subjects/{gsubject_id}/sources/{source_id}/runs",
    response_model=list[SubjectSourceRunRead],
)
async def list_runs(
    gsubject_id: int,
    source_id: int,
    limit: int = Query(10, ge=1, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """List recent collection runs for a source."""
    await _get_subject_or_404(session, gsubject_id, user)

    source = await SubjectSourcesTable(session).get_by_id(source_id)
    if source is None or source.deleted == 1 or source.gsubject_id != gsubject_id:
        raise HTTPException(status_code=404, detail="Source not found")

    return await SubjectSourceRunsTable(session).get_by_source(source_id, limit=limit)


@router_sources.get(
    "/subjects/{gsubject_id}/sources/{source_id}/runs/{run_id}",
    response_model=SubjectSourceRunRead,
)
async def get_run(
    gsubject_id: int,
    source_id: int,
    run_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """Get a specific collection run."""
    await _get_subject_or_404(session, gsubject_id, user)

    run = await SubjectSourceRunsTable(session).get_by_id(run_id)
    if run is None or run.source_id != source_id:
        raise HTTPException(status_code=404, detail="Run not found")

    return run
