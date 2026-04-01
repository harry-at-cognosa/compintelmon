import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_subjects_list_empty(user_client: AsyncClient):
    """Regular user sees empty subject list for their group."""
    resp = await user_client.get("/api/v1/subjects")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_subject_create_as_regular_user(user_client: AsyncClient):
    """Regular users cannot create subjects."""
    resp = await user_client.post(
        "/api/v1/subjects",
        json={"gsubject_name": "Test Co", "gsubject_type": "company"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_subject_crud_as_admin(admin_client: AsyncClient):
    """Superuser can create, read, update, and delete subjects."""
    # Create
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_name": "Acme Corp", "gsubject_type": "company"},
    )
    assert resp.status_code == 201
    subject = resp.json()
    assert subject["gsubject_name"] == "Acme Corp"
    assert subject["gsubject_type"] == "company"
    assert subject["enabled"] is True
    sid = subject["gsubject_id"]

    # Read
    resp = await admin_client.get(f"/api/v1/subjects/{sid}")
    assert resp.status_code == 200
    assert resp.json()["gsubject_name"] == "Acme Corp"

    # Update
    resp = await admin_client.put(
        f"/api/v1/subjects/{sid}",
        json={"gsubject_name": "Acme Corp Updated"},
    )
    assert resp.status_code == 200
    assert resp.json()["gsubject_name"] == "Acme Corp Updated"

    # Delete (soft)
    resp = await admin_client.delete(f"/api/v1/subjects/{sid}")
    assert resp.status_code == 204

    # Verify it's gone from list
    resp = await admin_client.get("/api/v1/subjects")
    assert resp.status_code == 200
    ids = [s["gsubject_id"] for s in resp.json()]
    assert sid not in ids
