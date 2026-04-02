from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Analyses


class AnalysesTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, gsubject_id: int, analysis_type: str = "full") -> Analyses:
        analysis = Analyses(gsubject_id=gsubject_id, analysis_type=analysis_type, status="pending")
        self.session.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)
        return analysis

    async def get_by_id(self, analysis_id: int) -> Analyses | None:
        result = await self.session.execute(
            select(Analyses).where(Analyses.analysis_id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def get_by_subject(self, gsubject_id: int, limit: int = 10) -> Sequence[Analyses]:
        result = await self.session.execute(
            select(Analyses)
            .where(Analyses.gsubject_id == gsubject_id)
            .order_by(Analyses.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update(self, analysis_id: int, **kwargs) -> Analyses | None:
        analysis = await self.get_by_id(analysis_id)
        if analysis is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(analysis, key):
                setattr(analysis, key, value)
        await self.session.commit()
        await self.session.refresh(analysis)
        return analysis
