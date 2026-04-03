"""
Chat runner: orchestrates ad-hoc update and query conversations.
"""
import asyncio
import json
import os
from datetime import datetime, timezone

from backend.db.session import SqlAsyncSession
from backend.db.tables.conversations import ConversationsTable
from backend.db.tables.conversation_messages import ConversationMessagesTable
from backend.db.tables.subject_sources import SubjectSourcesTable
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.services.data_utils import (
    load_latest_collected_data, save_data_file,
    get_subject_data_dir, get_existing_data_summary,
)
from backend.services.logger_service import get_logger

log = get_logger("chat_runner")


async def run_chat_message(conversation_id: int, user_message_id: int) -> None:
    """Process a user chat message. Designed for BackgroundTasks."""
    async with SqlAsyncSession() as session:
        try:
            await _run_chat_message_inner(session, conversation_id, user_message_id)
        except Exception as e:
            log.error("chat_message_failed", conversation_id=conversation_id, error=str(e))
            # Try to mark the assistant message as error
            try:
                async with SqlAsyncSession() as err_session:
                    msgs_table = ConversationMessagesTable(err_session)
                    msgs = await msgs_table.get_by_conversation(conversation_id, limit=50)
                    pending = [m for m in msgs if m.role == "assistant" and m.status == "pending"]
                    for m in pending:
                        await msgs_table.update(m.message_id, status="error", content=f"Error: {str(e)[:500]}")
            except Exception:
                pass


async def _run_chat_message_inner(session, conversation_id: int, user_message_id: int) -> None:
    convs_table = ConversationsTable(session)
    msgs_table = ConversationMessagesTable(session)
    subjects_table = GroupSubjectsTable(session)

    # Load conversation and user message
    conv = await convs_table.get_by_id(conversation_id)
    if conv is None:
        return

    msgs = await msgs_table.get_by_conversation(conversation_id, limit=50)
    user_msg = next((m for m in msgs if m.message_id == user_message_id), None)
    if user_msg is None:
        return

    # Load subject
    subject = await subjects_table.get_by_id(conv.gsubject_id)
    if subject is None:
        return

    subject_name = subject.gsubject_name
    subject_type = subject.gsubject_type
    data_dir = get_subject_data_dir(subject.group_id, subject.gsubject_id)

    # Create pending assistant message
    assistant_msg = await msgs_table.create(
        conversation_id=conversation_id,
        role="assistant",
        content="Processing...",
        status="pending",
    )

    if conv.conversation_type == "update":
        await _handle_update(
            session, subject, subject_name, subject_type, data_dir,
            user_msg.content, assistant_msg.message_id, msgs_table,
        )
    elif conv.conversation_type == "query":
        await _handle_query(
            session, subject, subject_name, subject_type, data_dir,
            user_msg.content, assistant_msg.message_id, msgs_table,
        )

    # Update conversation timestamp
    await convs_table.update(conversation_id, updated_at=datetime.now(timezone.utc))


async def _handle_update(
    session, subject, subject_name, subject_type, data_dir,
    user_content, assistant_message_id, msgs_table,
):
    """Handle an update-mode message: save data."""
    from backend.agents.adhoc_update import run_adhoc_update

    existing_summary = get_existing_data_summary(data_dir)

    log.info("chat_update_starting", subject=subject_name)

    try:
        result = await asyncio.to_thread(
            run_adhoc_update, subject_name, subject_type, user_content, existing_summary
        )
    except Exception as e:
        await msgs_table.update(
            assistant_message_id,
            content=f"Error processing update: {str(e)[:500]}",
            status="error",
        )
        return

    # Save data file if there's data to save
    metadata = {}
    if result.get("saved_data"):
        file_data = {
            "category_key": "adhoc_update",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
            "content_hash": "",
            "items": [result["saved_data"]],
            "raw_content": json.dumps(result["saved_data"], default=str),
        }
        file_path = save_data_file(
            group_id=subject.group_id,
            gsubject_id=subject.gsubject_id,
            category_key="adhoc_update",
            item_id=assistant_message_id,
            data=file_data,
        )
        metadata["file_saved"] = file_path
        log.info("chat_update_saved", subject=subject_name, file=file_path)

    await msgs_table.update(
        assistant_message_id,
        content=result.get("response_text", "Update processed."),
        message_type=result.get("message_type", "text"),
        metadata_json=metadata,
        status="ok",
    )


async def _handle_query(
    session, subject, subject_name, subject_type, data_dir,
    user_content, assistant_message_id, msgs_table,
):
    """Handle a query-mode message: answer from collected data."""
    from backend.agents.adhoc_query import run_adhoc_query

    # Load collected data for all sources
    sources_table = SubjectSourcesTable(session)
    sources = await sources_table.get_by_subject(subject.gsubject_id)

    sources_data = []
    for source in sources:
        if not source.enabled:
            continue
        content = load_latest_collected_data(data_dir, source.category_key)
        if content:
            sources_data.append({
                "category_key": source.category_key,
                "category_name": source.category_name,
                "raw_content": content,
            })

    # Also load any adhoc_update files
    adhoc_content = load_latest_collected_data(data_dir, "adhoc_update")
    if adhoc_content:
        sources_data.append({
            "category_key": "adhoc_update",
            "category_name": "User-provided Intelligence",
            "raw_content": adhoc_content,
        })

    log.info("chat_query_starting", subject=subject_name, sources=len(sources_data))

    try:
        answer = await asyncio.to_thread(
            run_adhoc_query, subject_name, subject_type, user_content, sources_data
        )
    except Exception as e:
        await msgs_table.update(
            assistant_message_id,
            content=f"Error processing query: {str(e)[:500]}",
            status="error",
        )
        return

    await msgs_table.update(
        assistant_message_id,
        content=answer,
        status="ok",
    )

    log.info("chat_query_complete", subject=subject_name)
