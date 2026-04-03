from collections.abc import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import GroupSubjects, SubjectTypes


class GroupSubjectsTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _resolve_type_id(self, type_name: str) -> int:
        """Resolve a subject type name to its FK ID."""
        result = await self.session.execute(
            select(SubjectTypes.subj_type_id).where(SubjectTypes.subj_type_name == type_name)
        )
        type_id = result.scalar_one_or_none()
        if type_id is None:
            raise ValueError(f"Unknown subject type: {type_name}")
        return type_id

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
        type_id = await self._resolve_type_id(gsubject_type)
        seqn = await self._next_seqn(group_id)
        subject = GroupSubjects(
            group_id=group_id,
            gsubject_seqn=seqn,
            gsubject_name=gsubject_name,
            gsubject_type_id=type_id,
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
                    # Resolve name to FK ID
                    subject.gsubject_type_id = await self._resolve_type_id(value)
                    continue
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
