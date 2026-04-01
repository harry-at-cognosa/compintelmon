from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.schemas import GroupRead, GroupCreate, GroupUpdate
from backend.db.tables.api_groups import ApiGroupsTable
from backend.auth.users import current_active_user

router_groups = APIRouter()


def _require_superuser(user: User):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router_groups.get("/groups", response_model=list[GroupRead])
async def list_groups(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_superuser(user)
    return await ApiGroupsTable(session).get_all_not_deleted()


@router_groups.post("/groups", response_model=GroupRead, status_code=201)
async def create_group(
    payload: GroupCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_superuser(user)
    return await ApiGroupsTable(session).create_group(payload.group_name)


@router_groups.put("/groups/{group_id}", response_model=GroupRead)
async def update_group(
    group_id: int,
    payload: GroupUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_superuser(user)
    if payload.group_name is None:
        raise HTTPException(status_code=400, detail="group_name required")
    group = await ApiGroupsTable(session).update_group(group_id, payload.group_name)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router_groups.delete("/groups/{group_id}", status_code=204)
async def delete_group(
    group_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_superuser(user)
    if group_id in (1, 2):
        raise HTTPException(status_code=400, detail="Cannot delete system groups")
    ok = await ApiGroupsTable(session).soft_delete_group(group_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Group not found")
