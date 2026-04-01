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

    async def get_by_id(self, run_id: int) -> SubjectSourceRuns | None:
        result = await self.session.execute(
            select(SubjectSourceRuns).where(SubjectSourceRuns.run_id == run_id)
        )
        return result.scalar_one_or_none()

    async def create_run(self, source_id: int, status: str = "pending") -> SubjectSourceRuns:
        run = SubjectSourceRuns(source_id=source_id, status=status)
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def update_run(self, run_id: int, **kwargs) -> SubjectSourceRuns | None:
        run = await self.get_by_id(run_id)
        if run is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(run, key):
                setattr(run, key, value)
        await self.session.commit()
        await self.session.refresh(run)
        return run
