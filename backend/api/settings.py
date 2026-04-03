from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.schemas import SettingRead, SettingUpdate, GroupSettingRead, GroupSettingUpdate
from backend.db.tables.api_settings import ApiSettingsTable
from backend.db.tables.group_settings import GroupSettingsTable
from backend.auth.users import current_active_user, current_active_user_or_none

router_settings = APIRouter()


def _require_superuser(user: User):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def _require_groupadmin_or_above(user: User):
    if not (user.is_groupadmin or user.is_superuser):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


# ── Public: webapp options (no auth required for login page theming) ──

@router_settings.get("/webapp_options", response_model=list[SettingRead])
async def webapp_options(
    session: AsyncSession = Depends(async_get_session),
):
    """Public endpoint for frontend theming and dashboard display."""
    return await ApiSettingsTable(session).get_by_names(
        ["app_title", "navbar_color", "instance_label", "dashboard_title", "dashboard_top", "sw_ver", "db_ver"]
    )


# ── Global settings (superuser only) ──

@router_settings.get("/settings", response_model=list[SettingRead])
async def list_settings(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_superuser(user)
    return await ApiSettingsTable(session).get_all()


@router_settings.put("/settings", response_model=SettingRead)
async def upsert_setting(
    payload: SettingUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_superuser(user)
    return await ApiSettingsTable(session).upsert(payload.name, payload.value)


# ── Group settings (groupadmin+) ──

@router_settings.get("/group_settings/{group_id}", response_model=list[GroupSettingRead])
async def list_group_settings(
    group_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_groupadmin_or_above(user)
    if not user.is_superuser and user.group_id != group_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await GroupSettingsTable(session).get_all_for_group(group_id)


@router_settings.put("/group_settings/{group_id}", response_model=GroupSettingRead)
async def upsert_group_setting(
    group_id: int,
    payload: GroupSettingUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_groupadmin_or_above(user)
    if not user.is_superuser and user.group_id != group_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await GroupSettingsTable(session).upsert(group_id, payload.name, payload.value)


@router_settings.delete("/group_settings/{group_id}/{name}", status_code=204)
async def delete_group_setting(
    group_id: int,
    name: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_groupadmin_or_above(user)
    if not user.is_superuser and user.group_id != group_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    ok = await GroupSettingsTable(session).delete(group_id, name)
    if not ok:
        raise HTTPException(status_code=404, detail="Setting not found")
