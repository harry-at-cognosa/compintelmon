from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.schemas import UsersMe
from backend.db.tables.api_groups import ApiGroupsTable
from backend.auth.users import current_active_user

router_users = APIRouter()


@router_users.get("/users/me", response_model=UsersMe)
async def users_me(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    group_obj = await ApiGroupsTable(session).get_group_by_group_id(user.group_id)
    group_name = group_obj.group_name if group_obj else "Unknown"
    return UsersMe(**user.__dict__, group_name=group_name)
