from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import SubjectTypes


class SubjectTypesTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, enabled_only: bool = False) -> Sequence[SubjectTypes]:
        query = select(SubjectTypes)
        if enabled_only:
            query = query.where(SubjectTypes.subj_type_enabled == True)
        result = await self.session.execute(query.order_by(SubjectTypes.subj_type_id))
        return result.scalars().all()

    async def get_by_id(self, subj_type_id: int) -> SubjectTypes | None:
        result = await self.session.execute(
            select(SubjectTypes).where(SubjectTypes.subj_type_id == subj_type_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> SubjectTypes | None:
        result = await self.session.execute(
            select(SubjectTypes).where(SubjectTypes.subj_type_name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, desc: str = "", enabled: bool = True) -> SubjectTypes:
        st = SubjectTypes(subj_type_name=name, subj_type_desc=desc, subj_type_enabled=enabled)
        self.session.add(st)
        await self.session.commit()
        await self.session.refresh(st)
        return st

    async def update(self, subj_type_id: int, **kwargs) -> SubjectTypes | None:
        st = await self.get_by_id(subj_type_id)
        if st is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(st, key):
                setattr(st, key, value)
        await self.session.commit()
        await self.session.refresh(st)
        return st
