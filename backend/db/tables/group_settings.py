from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import GroupSettings


class GroupSettingsTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_for_group(self, group_id: int) -> Sequence[GroupSettings]:
        result = await self.session.execute(
            select(GroupSettings)
            .where(GroupSettings.group_id == group_id)
            .order_by(GroupSettings.name)
        )
        return result.scalars().all()

    async def get_one(self, group_id: int, name: str) -> GroupSettings | None:
        result = await self.session.execute(
            select(GroupSettings)
            .where(GroupSettings.group_id == group_id, GroupSettings.name == name)
        )
        return result.scalar_one_or_none()

    async def upsert(self, group_id: int, name: str, value: str) -> GroupSettings:
        existing = await self.get_one(group_id, name)
        if existing:
            existing.value = value
        else:
            existing = GroupSettings(group_id=group_id, name=name, value=value)
            self.session.add(existing)
        await self.session.commit()
        return existing

    async def delete(self, group_id: int, name: str) -> bool:
        existing = await self.get_one(group_id, name)
        if existing is None:
            return False
        await self.session.delete(existing)
        await self.session.commit()
        return True
