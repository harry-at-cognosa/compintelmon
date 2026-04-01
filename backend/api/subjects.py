from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.schemas import SubjectRead, SubjectCreate, SubjectUpdate
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.auth.users import current_active_user

router_subjects = APIRouter()


def _require_subjectmanager_or_above(user: User):
    if not (user.is_subjectmanager or user.is_groupadmin or user.is_superuser):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router_subjects.get("/subjects", response_model=list[SubjectRead])
async def list_subjects(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """List subjects for the current user's group."""
    return await GroupSubjectsTable(session).get_by_group(user.group_id)


@router_subjects.get("/subjects/{gsubject_id}", response_model=SubjectRead)
async def get_subject(
    gsubject_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    subject = await GroupSubjectsTable(session).get_by_id(gsubject_id)
    if subject is None or subject.deleted == 1:
        raise HTTPException(status_code=404, detail="Subject not found")
    if not user.is_superuser and subject.group_id != user.group_id:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router_subjects.post("/subjects", response_model=SubjectRead, status_code=201)
async def create_subject(
    payload: SubjectCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_subjectmanager_or_above(user)
    return await GroupSubjectsTable(session).create_subject(
        group_id=user.group_id,
        gsubject_name=payload.gsubject_name,
        gsubject_type=payload.gsubject_type,
        enabled=payload.enabled,
    )


@router_subjects.put("/subjects/{gsubject_id}", response_model=SubjectRead)
async def update_subject(
    gsubject_id: int,
    payload: SubjectUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_subjectmanager_or_above(user)
    subject = await GroupSubjectsTable(session).get_by_id(gsubject_id)
    if subject is None or subject.deleted == 1:
        raise HTTPException(status_code=404, detail="Subject not found")
    if not user.is_superuser and subject.group_id != user.group_id:
        raise HTTPException(status_code=404, detail="Subject not found")
    updated = await GroupSubjectsTable(session).update_subject(
        gsubject_id,
        gsubject_name=payload.gsubject_name,
        gsubject_type=payload.gsubject_type,
        enabled=payload.enabled,
    )
    return updated


@router_subjects.delete("/subjects/{gsubject_id}", status_code=204)
async def delete_subject(
    gsubject_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_subjectmanager_or_above(user)
    subject = await GroupSubjectsTable(session).get_by_id(gsubject_id)
    if subject is None or subject.deleted == 1:
        raise HTTPException(status_code=404, detail="Subject not found")
    if not user.is_superuser and subject.group_id != user.group_id:
        raise HTTPException(status_code=404, detail="Subject not found")
    await GroupSubjectsTable(session).soft_delete_subject(gsubject_id)
