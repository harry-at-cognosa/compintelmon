"""Tests for subject types CRUD and playbook template CRUD/clone."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_subject_types(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/subject-types")
    assert resp.status_code == 200
    types = resp.json()
    assert len(types) == 4
    names = [t["subj_type_name"] for t in types]
    assert "company" in names
    assert "product" in names
    assert "service" in names
    assert "topic" in names


@pytest.mark.asyncio
async def test_create_subject_type(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/subject-types",
        json={"subj_type_name": "industry", "subj_type_desc": "Industry verticals"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["subj_type_name"] == "industry"
    assert data["subj_type_enabled"] is True


@pytest.mark.asyncio
async def test_update_subject_type(admin_client: AsyncClient):
    # Get the industry type we just created
    resp = await admin_client.get("/api/v1/subject-types")
    industry = next((t for t in resp.json() if t["subj_type_name"] == "industry"), None)
    assert industry is not None

    resp = await admin_client.put(
        f"/api/v1/subject-types/{industry['subj_type_id']}",
        json={"subj_type_desc": "Industry vertical monitoring"},
    )
    assert resp.status_code == 200
    assert resp.json()["subj_type_desc"] == "Industry vertical monitoring"


@pytest.mark.asyncio
async def test_create_subject_type_requires_superuser(user_client: AsyncClient):
    resp = await user_client.post(
        "/api/v1/subject-types",
        json={"subj_type_name": "test_type"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_subject_with_new_type(admin_client: AsyncClient):
    """Creating a subject with a custom type works."""
    # Get the industry type
    resp = await admin_client.get("/api/v1/subject-types")
    industry = next((t for t in resp.json() if t["subj_type_name"] == "industry"), None)
    assert industry is not None

    resp = await admin_client.post(
        "/api/v1/subjects",
        json={"gsubject_type": "industry", "gsubject_name": "Test Industry Subject"},
    )
    assert resp.status_code == 201
    # No templates for industry type yet, so 0 sources provisioned
    assert resp.json()["sources_provisioned"] == 0

    await admin_client.delete(f"/api/v1/subjects/{resp.json()['gsubject_id']}")


@pytest.mark.asyncio
async def test_create_playbook_template(admin_client: AsyncClient):
    """Superuser can create a new playbook template."""
    resp = await admin_client.get("/api/v1/subject-types")
    industry = next((t for t in resp.json() if t["subj_type_name"] == "industry"), None)
    assert industry is not None

    resp = await admin_client.post(
        "/api/v1/playbook-templates",
        json={
            "subject_type_id": industry["subj_type_id"],
            "category_key": "industry_news",
            "category_name": "Industry News",
            "category_group": "news",
            "collection_tool": "httpx",
            "description": "Monitor industry news",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["category_key"] == "industry_news"
    assert resp.json()["subject_type"] == "industry"


@pytest.mark.asyncio
async def test_update_playbook_template(admin_client: AsyncClient):
    """Superuser can edit an existing template."""
    resp = await admin_client.get("/api/v1/playbook-templates?subject_type=company")
    templates = resp.json()
    assert len(templates) > 0
    tpl = templates[0]

    resp = await admin_client.put(
        f"/api/v1/playbook-templates/{tpl['template_id']}",
        json={"description": "Updated description"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description"


@pytest.mark.asyncio
async def test_clone_playbook_template(admin_client: AsyncClient):
    """Clone a template from company to industry."""
    resp = await admin_client.get("/api/v1/subject-types")
    industry = next((t for t in resp.json() if t["subj_type_name"] == "industry"), None)

    resp = await admin_client.get("/api/v1/playbook-templates?subject_type=company")
    company_tpl = resp.json()[0]

    resp = await admin_client.post(
        f"/api/v1/playbook-templates/{company_tpl['template_id']}/clone",
        json={
            "target_subject_type_id": industry["subj_type_id"],
            "new_category_key": f"ind_{company_tpl['category_key']}",
        },
    )
    assert resp.status_code == 201
    clone = resp.json()
    assert clone["subject_type"] == "industry"
    assert clone["category_name"] == company_tpl["category_name"]
