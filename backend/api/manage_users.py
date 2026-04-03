"""User management API for groupadmin+ and superusers."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.schemas import UserManageRead, UserManageCreate, UserManageUpdate
from backend.auth.users import current_active_user, password_helper

router_manage_users = APIRouter()


def _require_groupadmin_or_above(user: User):
    if not (user.is_groupadmin or user.is_superuser):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router_manage_users.get("/manage/users", response_model=list[UserManageRead])
async def list_users(
    group_id: int | None = Query(None),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """List users. Superusers see all, groupadmins see their group."""
    _require_groupadmin_or_above(user)
    query = select(User).where(User.deleted == 0)
    if user.is_superuser and group_id is not None:
        query = query.where(User.group_id == group_id)
    elif not user.is_superuser:
        query = query.where(User.group_id == user.group_id)
    result = await session.execute(query.order_by(User.user_id))
    return result.scalars().all()


@router_manage_users.post("/manage/users", response_model=UserManageRead, status_code=201)
async def create_user(
    payload: UserManageCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """Create a user. Only superusers can create superusers."""
    _require_groupadmin_or_above(user)

    # Groupadmins can only create users in their own group
    if not user.is_superuser and payload.group_id != user.group_id:
        raise HTTPException(status_code=400, detail="Can only create users in your own group")

    # Only superusers can create superusers
    if payload.is_superuser and not user.is_superuser:
        raise HTTPException(status_code=400, detail="Only superusers can create superusers")

    new_user = User(
        id=uuid.uuid4(),
        user_name=payload.user_name,
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=password_helper.hash(payload.password),
        group_id=payload.group_id,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
        is_groupadmin=payload.is_groupadmin,
        is_subjectmanager=payload.is_subjectmanager,
        is_verified=True,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


@router_manage_users.put("/manage/users/{user_id}", response_model=UserManageRead)
async def update_user(
    user_id: int,
    payload: UserManageUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    """Update a user. Groupadmins can only manage their group's users."""
    _require_groupadmin_or_above(user)

    result = await session.execute(select(User).where(User.user_id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Groupadmins can only manage their own group
    if not user.is_superuser and target.group_id != user.group_id:
        raise HTTPException(status_code=404, detail="User not found")

    # Only superusers can grant/revoke superuser
    if payload.is_superuser is not None and not user.is_superuser:
        raise HTTPException(status_code=400, detail="Only superusers can change superuser status")

    # Apply updates
    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.email is not None:
        target.email = payload.email
    if payload.group_id is not None:
        if not user.is_superuser:
            raise HTTPException(status_code=400, detail="Only superusers can change group")
        target.group_id = payload.group_id
    if payload.is_active is not None:
        target.is_active = payload.is_active
    if payload.is_superuser is not None:
        target.is_superuser = payload.is_superuser
    if payload.is_groupadmin is not None:
        target.is_groupadmin = payload.is_groupadmin
    if payload.is_subjectmanager is not None:
        target.is_subjectmanager = payload.is_subjectmanager

    await session.commit()
    await session.refresh(target)
    return target
