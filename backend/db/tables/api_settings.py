from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ApiSettings


class ApiSettingsTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> Sequence[ApiSettings]:
        result = await self.session.execute(
            select(ApiSettings).order_by(ApiSettings.name)
        )
        return result.scalars().all()

    async def get_by_name(self, name: str) -> ApiSettings | None:
        result = await self.session.execute(
            select(ApiSettings).where(ApiSettings.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_names(self, names: list[str]) -> Sequence[ApiSettings]:
        result = await self.session.execute(
            select(ApiSettings).where(ApiSettings.name.in_(names))
        )
        return result.scalars().all()

    async def upsert(self, name: str, value: str) -> ApiSettings:
        existing = await self.get_by_name(name)
        if existing:
            existing.value = value
        else:
            existing = ApiSettings(name=name, value=value)
            self.session.add(existing)
        await self.session.commit()
        return existing
