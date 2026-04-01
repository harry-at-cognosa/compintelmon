from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.schemas import (
    PlaybookTemplateRead,
    SubjectSourceRead, SubjectSourceCreate, SubjectSourceUpdate,
)
from backend.db.tables.playbook_templates import PlaybookTemplatesTable
from backend.db.tables.subject_sources import SubjectSourcesTable
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.auth.users import current_active_user

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
