from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ApiGroups


class ApiGroupsTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_group_by_group_id(self, group_id: int) -> ApiGroups | None:
        result = await self.session.execute(
            select(ApiGroups).where(ApiGroups.group_id == group_id)
        )
        return result.scalar_one_or_none()

    async def get_all_not_deleted(self) -> Sequence[ApiGroups]:
        result = await self.session.execute(
            select(ApiGroups).where(ApiGroups.deleted == 0).order_by(ApiGroups.group_id)
        )
        return result.scalars().all()

    async def create_group(self, group_name: str) -> ApiGroups:
        group = ApiGroups(group_name=group_name)
        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)
        return group

    async def update_group(self, group_id: int, group_name: str) -> ApiGroups | None:
        group = await self.get_group_by_group_id(group_id)
        if group is None:
            return None
        group.group_name = group_name
        await self.session.commit()
        await self.session.refresh(group)
        return group

    async def soft_delete_group(self, group_id: int) -> bool:
        group = await self.get_group_by_group_id(group_id)
        if group is None:
            return False
        group.deleted = 1
        await self.session.commit()
        return True
