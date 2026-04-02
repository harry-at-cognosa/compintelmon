from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ConversationMessages


class ConversationMessagesTable:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        conversation_id: int,
        role: str,
        content: str,
        message_type: str = "text",
        metadata_json: dict | None = None,
        status: str = "ok",
    ) -> ConversationMessages:
        msg = ConversationMessages(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_type=message_type,
            metadata_json=metadata_json or {},
            status=status,
        )
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def get_by_conversation(
        self, conversation_id: int, limit: int = 50, after_message_id: int = 0
    ) -> Sequence[ConversationMessages]:
        query = (
            select(ConversationMessages)
            .where(ConversationMessages.conversation_id == conversation_id)
        )
        if after_message_id > 0:
            query = query.where(ConversationMessages.message_id > after_message_id)
        result = await self.session.execute(
            query.order_by(ConversationMessages.created_at).limit(limit)
        )
        return result.scalars().all()

    async def update(self, message_id: int, **kwargs) -> ConversationMessages | None:
        result = await self.session.execute(
            select(ConversationMessages).where(ConversationMessages.message_id == message_id)
        )
        msg = result.scalar_one_or_none()
        if msg is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(msg, key):
                setattr(msg, key, value)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg
