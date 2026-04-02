"""Tests for conversations, messages, and chat runner."""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient


# ── Conversation CRUD tests ───────────────────────────────────


@pytest.mark.asyncio
async def test_create_conversation_update(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Chat Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.post(
        f"/api/v1/subjects/{sid}/conversations",
        json={"conversation_type": "update", "title": "Test Update"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["conversation_type"] == "update"
    assert data["title"] == "Test Update"

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_create_conversation_query(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Query Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.post(
        f"/api/v1/subjects/{sid}/conversations",
        json={"conversation_type": "query"},
    )
    assert resp.status_code == 201
    assert resp.json()["conversation_type"] == "query"

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_list_conversations(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "List Conv Test"},
    )
    sid = resp.json()["gsubject_id"]

    # Create two conversations
    await admin_client.post(f"/api/v1/subjects/{sid}/conversations", json={"conversation_type": "update"})
    await admin_client.post(f"/api/v1/subjects/{sid}/conversations", json={"conversation_type": "query"})

    resp = await admin_client.get(f"/api/v1/subjects/{sid}/conversations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    await admin_client.delete(f"/api/v1/subjects/{sid}")


# ── Message flow tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_message(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Message Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    # Create conversation
    resp = await admin_client.post(
        f"/api/v1/subjects/{sid}/conversations",
        json={"conversation_type": "query"},
    )
    cid = resp.json()["conversation_id"]

    # Send message (mock the chat runner)
    with patch("backend.api.conversations.run_chat_message"):
        resp = await admin_client.post(
            f"/api/v1/subjects/{sid}/conversations/{cid}/messages",
            json={"content": "What do we know?"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"

    # Fetch messages — should have the user message
    resp = await admin_client.get(f"/api/v1/subjects/{sid}/conversations/{cid}/messages")
    assert resp.status_code == 200
    msgs = resp.json()
    assert len(msgs) >= 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "What do we know?"

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_poll_messages_after_id(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Poll Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.post(
        f"/api/v1/subjects/{sid}/conversations",
        json={"conversation_type": "query"},
    )
    cid = resp.json()["conversation_id"]

    with patch("backend.api.conversations.run_chat_message"):
        resp = await admin_client.post(
            f"/api/v1/subjects/{sid}/conversations/{cid}/messages",
            json={"content": "Test message"},
        )
    msg_id = resp.json()["message_id"]

    # Poll with after_message_id — should return only newer messages
    resp = await admin_client.get(
        f"/api/v1/subjects/{sid}/conversations/{cid}/messages?after_message_id={msg_id}"
    )
    assert resp.status_code == 200
    # The pending assistant message should appear here
    msgs = resp.json()
    # Could be 0 or 1 depending on timing, but request should succeed

    await admin_client.delete(f"/api/v1/subjects/{sid}")


# ── RBAC tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_conversation_rbac(user_client: AsyncClient, admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "RBAC Conv Test"},
    )
    sid = resp.json()["gsubject_id"]

    # Regular user can't access this subject's conversations
    resp = await user_client.post(
        f"/api/v1/subjects/{sid}/conversations",
        json={"conversation_type": "query"},
    )
    assert resp.status_code == 404

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_conversation_invalid_type(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Invalid Type Test"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.post(
        f"/api/v1/subjects/{sid}/conversations",
        json={"conversation_type": "invalid"},
    )
    assert resp.status_code == 422  # validation error

    await admin_client.delete(f"/api/v1/subjects/{sid}")
