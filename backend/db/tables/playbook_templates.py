from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PlaybookTemplates, SubjectTypes


class PlaybookTemplatesTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _resolve_type_id(self, type_name: str) -> int:
        result = await self.session.execute(
            select(SubjectTypes.subj_type_id).where(SubjectTypes.subj_type_name == type_name)
        )
        type_id = result.scalar_one_or_none()
        if type_id is None:
            raise ValueError(f"Unknown subject type: {type_name}")
        return type_id

    async def get_all(self) -> Sequence[PlaybookTemplates]:
        result = await self.session.execute(
            select(PlaybookTemplates).order_by(PlaybookTemplates.subject_type_id, PlaybookTemplates.priority)
        )
        return result.scalars().all()

    async def get_by_subject_type(self, subject_type: str) -> Sequence[PlaybookTemplates]:
        type_id = await self._resolve_type_id(subject_type)
        result = await self.session.execute(
            select(PlaybookTemplates)
            .where(PlaybookTemplates.subject_type_id == type_id)
            .order_by(PlaybookTemplates.priority)
        )
        return result.scalars().all()

    async def get_by_subject_type_id(self, subject_type_id: int) -> Sequence[PlaybookTemplates]:
        result = await self.session.execute(
            select(PlaybookTemplates)
            .where(PlaybookTemplates.subject_type_id == subject_type_id)
            .order_by(PlaybookTemplates.priority)
        )
        return result.scalars().all()

    async def get_by_id(self, template_id: int) -> PlaybookTemplates | None:
        result = await self.session.execute(
            select(PlaybookTemplates).where(PlaybookTemplates.template_id == template_id)
        )
        return result.scalar_one_or_none()

    async def create_template(self, **kwargs) -> PlaybookTemplates:
        tpl = PlaybookTemplates(**kwargs)
        self.session.add(tpl)
        await self.session.commit()
        await self.session.refresh(tpl)
        return tpl

    async def update_template(self, template_id: int, **kwargs) -> PlaybookTemplates | None:
        tpl = await self.get_by_id(template_id)
        if tpl is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(tpl, key):
                setattr(tpl, key, value)
        await self.session.commit()
        await self.session.refresh(tpl)
        return tpl

    async def clone_template(self, template_id: int, target_type_id: int, new_category_key: str | None = None) -> PlaybookTemplates | None:
        """Clone a template to a different subject type."""
        source = await self.get_by_id(template_id)
        if source is None:
            return None
        clone = PlaybookTemplates(
            subject_type_id=target_type_id,
            category_key=new_category_key or source.category_key,
            category_name=source.category_name,
            category_group=source.category_group,
            description=source.description,
            default_enabled=source.default_enabled,
            default_frequency_minutes=source.default_frequency_minutes,
            collection_tool=source.collection_tool,
            collection_config=source.collection_config,
            signal_instructions=source.signal_instructions,
            user_inputs_schema=source.user_inputs_schema,
            priority=source.priority,
        )
        self.session.add(clone)
        await self.session.commit()
        await self.session.refresh(clone)
        return clone
