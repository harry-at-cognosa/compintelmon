from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.schemas import SubjectTypeRead, SubjectTypeCreate, SubjectTypeUpdate
from backend.db.tables.subject_types import SubjectTypesTable
from backend.auth.users import current_active_user

router_subject_types = APIRouter()


def _require_superuser(user: User):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser required")


@router_subject_types.get("/subject-types", response_model=list[SubjectTypeRead])
async def list_subject_types(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    return await SubjectTypesTable(session).get_all()


@router_subject_types.post("/subject-types", response_model=SubjectTypeRead, status_code=201)
async def create_subject_type(
    payload: SubjectTypeCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_superuser(user)
    return await SubjectTypesTable(session).create(
        name=payload.subj_type_name,
        desc=payload.subj_type_desc,
        enabled=payload.subj_type_enabled,
    )


@router_subject_types.put("/subject-types/{subj_type_id}", response_model=SubjectTypeRead)
async def update_subject_type(
    subj_type_id: int,
    payload: SubjectTypeUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_superuser(user)
    st = await SubjectTypesTable(session).update(
        subj_type_id,
        subj_type_name=payload.subj_type_name,
        subj_type_desc=payload.subj_type_desc,
        subj_type_enabled=payload.subj_type_enabled,
    )
    if st is None:
        raise HTTPException(status_code=404, detail="Subject type not found")
    return st
