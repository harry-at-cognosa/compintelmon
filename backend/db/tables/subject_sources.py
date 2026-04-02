from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import extract, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import SubjectSources
from backend.db.tables.playbook_templates import PlaybookTemplatesTable


class SubjectSourcesTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_subject(self, gsubject_id: int) -> Sequence[SubjectSources]:
        result = await self.session.execute(
            select(SubjectSources)
            .where(SubjectSources.gsubject_id == gsubject_id, SubjectSources.deleted == 0)
            .order_by(SubjectSources.source_id)
        )
        return result.scalars().all()

    async def get_enabled_by_subject(self, gsubject_id: int) -> Sequence[SubjectSources]:
        result = await self.session.execute(
            select(SubjectSources)
            .where(
                SubjectSources.gsubject_id == gsubject_id,
                SubjectSources.deleted == 0,
                SubjectSources.enabled == True,
            )
            .order_by(SubjectSources.source_id)
        )
        return result.scalars().all()

    async def get_all_due_sources(self) -> Sequence[SubjectSources]:
        """Get all enabled sources that are due for collection (across all subjects)."""
        now = func.now()
        result = await self.session.execute(
            select(SubjectSources)
            .where(
                SubjectSources.deleted == 0,
                SubjectSources.enabled == True,
                or_(
                    SubjectSources.last_collected_at.is_(None),
                    extract("epoch", now - SubjectSources.last_collected_at)
                    >= SubjectSources.frequency_minutes * 60,
                ),
            )
        )
        return result.scalars().all()

    async def count_enabled(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(SubjectSources)
            .where(SubjectSources.deleted == 0, SubjectSources.enabled == True)
        )
        return result.scalar() or 0

    async def count_due(self) -> int:
        now = func.now()
        result = await self.session.execute(
            select(func.count())
            .select_from(SubjectSources)
            .where(
                SubjectSources.deleted == 0,
                SubjectSources.enabled == True,
                or_(
                    SubjectSources.last_collected_at.is_(None),
                    extract("epoch", now - SubjectSources.last_collected_at)
                    >= SubjectSources.frequency_minutes * 60,
                ),
            )
        )
        return result.scalar() or 0

    async def get_by_id(self, source_id: int) -> SubjectSources | None:
        result = await self.session.execute(
            select(SubjectSources).where(SubjectSources.source_id == source_id)
        )
        return result.scalar_one_or_none()

    async def create_source(
        self,
        gsubject_id: int,
        category_key: str,
        category_name: str,
        collection_tool: str,
        enabled: bool = True,
        frequency_minutes: int = 360,
        collection_config: dict | None = None,
        signal_instructions: str = "",
        user_inputs: dict | None = None,
    ) -> SubjectSources:
        source = SubjectSources(
            gsubject_id=gsubject_id,
            category_key=category_key,
            category_name=category_name,
            collection_tool=collection_tool,
            enabled=enabled,
            frequency_minutes=frequency_minutes,
            collection_config=collection_config or {},
            signal_instructions=signal_instructions,
            user_inputs=user_inputs or {},
        )
        self.session.add(source)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def update_source(self, source_id: int, **kwargs) -> SubjectSources | None:
        source = await self.get_by_id(source_id)
        if source is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(source, key):
                setattr(source, key, value)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def soft_delete_source(self, source_id: int) -> bool:
        source = await self.get_by_id(source_id)
        if source is None:
            return False
        source.deleted = 1
        await self.session.commit()
        return True

    async def provision_from_templates(self, gsubject_id: int, subject_type: str) -> int:
        """Load matching playbook templates and create source rows. Returns count."""
        templates = await PlaybookTemplatesTable(self.session).get_by_subject_type(subject_type)
        sources = []
        for t in templates:
            sources.append(SubjectSources(
                gsubject_id=gsubject_id,
                template_id=t.template_id,
                category_key=t.category_key,
                category_name=t.category_name,
                enabled=t.default_enabled,
                frequency_minutes=t.default_frequency_minutes,
                collection_tool=t.collection_tool,
                collection_config=t.collection_config,
                signal_instructions=t.signal_instructions,
                user_inputs={},
            ))
        self.session.add_all(sources)
        await self.session.commit()
        return len(sources)
