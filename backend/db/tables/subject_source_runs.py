from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import SubjectSourceRuns


class SubjectSourceRunsTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_source(self, source_id: int, limit: int = 20) -> Sequence[SubjectSourceRuns]:
        result = await self.session.execute(
            select(SubjectSourceRuns)
            .where(SubjectSourceRuns.source_id == source_id)
            .order_by(SubjectSourceRuns.started_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def create_run(self, source_id: int, status: str = "pending") -> SubjectSourceRuns:
        run = SubjectSourceRuns(source_id=source_id, status=status)
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run
