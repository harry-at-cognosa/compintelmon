from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Reports


class ReportsTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, analysis_id: int, gsubject_id: int, report_type: str = "battlecard", title: str = ""
    ) -> Reports:
        report = Reports(
            analysis_id=analysis_id,
            gsubject_id=gsubject_id,
            report_type=report_type,
            title=title,
            status="pending",
        )
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_by_id(self, report_id: int) -> Reports | None:
        result = await self.session.execute(
            select(Reports).where(Reports.report_id == report_id)
        )
        return result.scalar_one_or_none()

    async def get_by_subject(self, gsubject_id: int, limit: int = 10) -> Sequence[Reports]:
        result = await self.session.execute(
            select(Reports)
            .where(Reports.gsubject_id == gsubject_id)
            .order_by(Reports.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_analysis(self, analysis_id: int) -> Sequence[Reports]:
        result = await self.session.execute(
            select(Reports)
            .where(Reports.analysis_id == analysis_id)
            .order_by(Reports.created_at.desc())
        )
        return result.scalars().all()

    async def update(self, report_id: int, **kwargs) -> Reports | None:
        report = await self.get_by_id(report_id)
        if report is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(report, key):
                setattr(report, key, value)
        await self.session.commit()
        await self.session.refresh(report)
        return report
