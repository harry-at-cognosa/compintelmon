from collections.abc import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import GroupSubjects, GSubjectTypeEnum


class GroupSubjectsTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_all(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(GroupSubjects).where(GroupSubjects.deleted == 0)
        )
        return result.scalar() or 0

    async def get_by_group(self, group_id: int) -> Sequence[GroupSubjects]:
        result = await self.session.execute(
            select(GroupSubjects)
            .where(GroupSubjects.group_id == group_id, GroupSubjects.deleted == 0)
            .order_by(GroupSubjects.gsubject_seqn)
        )
        return result.scalars().all()

    async def get_by_id(self, gsubject_id: int) -> GroupSubjects | None:
        result = await self.session.execute(
            select(GroupSubjects).where(GroupSubjects.gsubject_id == gsubject_id)
        )
        return result.scalar_one_or_none()

    async def _next_seqn(self, group_id: int) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(GroupSubjects.gsubject_seqn), 0))
            .where(GroupSubjects.group_id == group_id)
        )
        return (result.scalar() or 0) + 1

    async def create_subject(
        self, group_id: int, gsubject_name: str, gsubject_type: str, enabled: bool = True
    ) -> GroupSubjects:
        seqn = await self._next_seqn(group_id)
        subject = GroupSubjects(
            group_id=group_id,
            gsubject_seqn=seqn,
            gsubject_name=gsubject_name,
            gsubject_type=GSubjectTypeEnum(gsubject_type),
            enabled=enabled,
        )
        self.session.add(subject)
        await self.session.commit()
        await self.session.refresh(subject)
        return subject

    async def update_subject(self, gsubject_id: int, **kwargs) -> GroupSubjects | None:
        subject = await self.get_by_id(gsubject_id)
        if subject is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(subject, key):
                if key == "gsubject_type":
                    value = GSubjectTypeEnum(value)
                setattr(subject, key, value)
        await self.session.commit()
        await self.session.refresh(subject)
        return subject

    async def soft_delete_subject(self, gsubject_id: int) -> bool:
        subject = await self.get_by_id(gsubject_id)
        if subject is None:
            return False
        subject.deleted = 1
        await self.session.commit()
        return True
