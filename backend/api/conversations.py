from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_get_session
from backend.db.models import User
from backend.db.schemas import (
    ConversationRead, ConversationCreate,
    ConversationMessageRead, SendMessageRequest, SendMessageResponse,
)
from backend.db.tables.conversations import ConversationsTable
from backend.db.tables.conversation_messages import ConversationMessagesTable
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.auth.users import current_active_user
from backend.services.chat_runner import run_chat_message

router_conversations = APIRouter()


def _require_subjectmanager_or_above(user: User):
    if not (user.is_subjectmanager or user.is_groupadmin or user.is_superuser):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


async def _get_subject_or_404(session: AsyncSession, gsubject_id: int, user: User):
    subject = await GroupSubjectsTable(session).get_by_id(gsubject_id)
    if subject is None or subject.deleted == 1:
        raise HTTPException(status_code=404, detail="Subject not found")
    if not user.is_superuser and subject.group_id != user.group_id:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router_conversations.post("/subjects/{gsubject_id}/conversations", response_model=ConversationRead, status_code=201)
async def create_conversation(
    gsubject_id: int,
    payload: ConversationCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_subjectmanager_or_above(user)
    await _get_subject_or_404(session, gsubject_id, user)
    return await ConversationsTable(session).create(
        gsubject_id=gsubject_id,
        user_id=user.user_id,
        conversation_type=payload.conversation_type,
        title=payload.title,
    )


@router_conversations.get("/subjects/{gsubject_id}/conversations", response_model=list[ConversationRead])
async def list_conversations(
    gsubject_id: int,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    await _get_subject_or_404(session, gsubject_id, user)
    return await ConversationsTable(session).get_by_subject(gsubject_id, limit=limit)


@router_conversations.get("/subjects/{gsubject_id}/conversations/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    gsubject_id: int,
    conversation_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    await _get_subject_or_404(session, gsubject_id, user)
    conv = await ConversationsTable(session).get_by_id(conversation_id)
    if conv is None or conv.gsubject_id != gsubject_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router_conversations.post(
    "/subjects/{gsubject_id}/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
)
async def send_message(
    gsubject_id: int,
    conversation_id: int,
    payload: SendMessageRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    _require_subjectmanager_or_above(user)
    await _get_subject_or_404(session, gsubject_id, user)

    conv = await ConversationsTable(session).get_by_id(conversation_id)
    if conv is None or conv.gsubject_id != gsubject_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Create user message
    user_msg = await ConversationMessagesTable(session).create(
        conversation_id=conversation_id,
        role="user",
        content=payload.content,
    )

    # Trigger background processing
    background_tasks.add_task(run_chat_message, conversation_id, user_msg.message_id)

    return SendMessageResponse(
        message_id=user_msg.message_id,
        status="sent",
        message="Message sent, processing...",
    )


@router_conversations.get(
    "/subjects/{gsubject_id}/conversations/{conversation_id}/messages",
    response_model=list[ConversationMessageRead],
)
async def list_messages(
    gsubject_id: int,
    conversation_id: int,
    limit: int = Query(50, ge=1, le=200),
    after_message_id: int = Query(0, ge=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(async_get_session),
):
    await _get_subject_or_404(session, gsubject_id, user)

    conv = await ConversationsTable(session).get_by_id(conversation_id)
    if conv is None or conv.gsubject_id != gsubject_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return await ConversationMessagesTable(session).get_by_conversation(
        conversation_id, limit=limit, after_message_id=after_message_id
    )
