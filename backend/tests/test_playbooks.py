import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_playbook_templates_list(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/playbook-templates")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 55


@pytest.mark.asyncio
async def test_playbook_templates_filter_by_type(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/playbook-templates?subject_type=company")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 19
    assert all(t["subject_type"] == "company" for t in data)


@pytest.mark.asyncio
async def test_playbook_templates_filter_product(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/playbook-templates?subject_type=product")
    assert resp.status_code == 200
    assert len(resp.json()) == 12


@pytest.mark.asyncio
async def test_subject_creation_provisions_sources(admin_client: AsyncClient):
    """Creating a company subject should auto-provision 19 sources."""
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Playbook Test Corp"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["sources_provisioned"] == 19
    sid = data["gsubject_id"]

    # Verify sources actually exist
    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert len(sources) == 19

    # Check that sources have expected fields from templates
    website_main = next((s for s in sources if s["category_key"] == "website_main"), None)
    assert website_main is not None
    assert website_main["enabled"] is True
    assert website_main["frequency_minutes"] == 360
    assert website_main["collection_tool"] == "crawl4ai"
    assert website_main["template_id"] is not None
    assert website_main["last_status"] == "pending"

    # Clean up
    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_product_subject_provisions_12_sources(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "product", "gsubject_name": "Test Product"},
    )
    assert resp.status_code == 201
    assert resp.json()["sources_provisioned"] == 12
    sid = resp.json()["gsubject_id"]
    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_source_update(admin_client: AsyncClient):
    """Can disable a source and change its frequency."""
    # Create subject
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Update Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    # Get sources
    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    sources = resp.json()
    source = sources[0]
    source_id = source["source_id"]

    # Disable it
    resp = await admin_client.put(
        f"/api/v1/subjects/{sid}/sources/{source_id}",
        json={"enabled": False, "frequency_minutes": 1440},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False
    assert resp.json()["frequency_minutes"] == 1440

    # Verify persistence
    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    updated = next(s for s in resp.json() if s["source_id"] == source_id)
    assert updated["enabled"] is False
    assert updated["frequency_minutes"] == 1440

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_source_create_custom(admin_client: AsyncClient):
    """Can add a custom source not from a template."""
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "topic", "gsubject_name": "Custom Source Test"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.post(
        f"/api/v1/subjects/{sid}/sources",
        json={
            "category_key": "custom_feed",
            "category_name": "My Custom RSS Feed",
            "collection_tool": "feedparser",
            "frequency_minutes": 720,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category_key"] == "custom_feed"
    assert data["template_id"] is None
    assert data["frequency_minutes"] == 720

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_source_delete(admin_client: AsyncClient):
    """Soft-deleting a source removes it from the list."""
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "Delete Source Test"},
    )
    sid = resp.json()["gsubject_id"]

    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    sources = resp.json()
    source_id = sources[0]["source_id"]
    original_count = len(sources)

    resp = await admin_client.delete(f"/api/v1/subjects/{sid}/sources/{source_id}")
    assert resp.status_code == 204

    resp = await admin_client.get(f"/api/v1/subjects/{sid}/sources")
    assert len(resp.json()) == original_count - 1

    await admin_client.delete(f"/api/v1/subjects/{sid}")


@pytest.mark.asyncio
async def test_source_rbac_regular_user(user_client: AsyncClient, admin_client: AsyncClient):
    """Regular user cannot create sources."""
    # Admin creates a subject in group 1
    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "company", "gsubject_name": "RBAC Test Corp"},
    )
    sid = resp.json()["gsubject_id"]

    # Regular user (group 2) cannot access this subject's sources
    resp = await user_client.get(f"/api/v1/subjects/{sid}/sources")
    assert resp.status_code == 404

    await admin_client.delete(f"/api/v1/subjects/{sid}")
