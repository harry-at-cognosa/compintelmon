from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Conversations


class ConversationsTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, gsubject_id: int, user_id: int, conversation_type: str, title: str = ""
    ) -> Conversations:
        conv = Conversations(
            gsubject_id=gsubject_id,
            user_id=user_id,
            conversation_type=conversation_type,
            title=title,
        )
        self.session.add(conv)
        await self.session.commit()
        await self.session.refresh(conv)
        return conv

    async def get_by_id(self, conversation_id: int) -> Conversations | None:
        result = await self.session.execute(
            select(Conversations).where(Conversations.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_subject(self, gsubject_id: int, limit: int = 20) -> Sequence[Conversations]:
        result = await self.session.execute(
            select(Conversations)
            .where(Conversations.gsubject_id == gsubject_id)
            .order_by(Conversations.updated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update(self, conversation_id: int, **kwargs) -> Conversations | None:
        conv = await self.get_by_id(conversation_id)
        if conv is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(conv, key):
                setattr(conv, key, value)
        await self.session.commit()
        await self.session.refresh(conv)
        return conv
