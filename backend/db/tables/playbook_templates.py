from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PlaybookTemplates


class PlaybookTemplatesTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> Sequence[PlaybookTemplates]:
        result = await self.session.execute(
            select(PlaybookTemplates).order_by(PlaybookTemplates.subject_type, PlaybookTemplates.priority)
        )
        return result.scalars().all()

    async def get_by_subject_type(self, subject_type: str) -> Sequence[PlaybookTemplates]:
        result = await self.session.execute(
            select(PlaybookTemplates)
            .where(PlaybookTemplates.subject_type == subject_type)
            .order_by(PlaybookTemplates.priority)
        )
        return result.scalars().all()

    async def get_by_id(self, template_id: int) -> PlaybookTemplates | None:
        result = await self.session.execute(
            select(PlaybookTemplates).where(PlaybookTemplates.template_id == template_id)
        )
        return result.scalar_one_or_none()
