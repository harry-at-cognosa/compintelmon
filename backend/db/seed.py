"""Idempotent seed: inserts default data only if tables are empty."""
import asyncio

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import DEFAULT_ADMIN_PASSWORD
from backend.db.session import SqlAsyncSession
from backend.db.models import ApiGroups, ApiSettings, PlaybookTemplates, User
from backend.auth.users import password_helper
from backend.db.playbook_defaults import PLAYBOOK_TEMPLATE_DEFAULTS


async def _seed(session: AsyncSession):
    # Check if groups already seeded
    count = await session.scalar(select(func.count()).select_from(ApiGroups))
    if count and count > 0:
        print("[seed] Data already exists, skipping seed.")
        return

    print("[seed] Seeding default data...")

    # Groups
    system_group = ApiGroups(group_id=1, group_name="System")
    default_group = ApiGroups(group_id=2, group_name="Default Group")
    session.add_all([system_group, default_group])
    await session.flush()

    # Admin user
    import uuid
    admin = User(
        user_id=1,
        id=uuid.uuid4(),
        email="admin@localhost",
        user_name="admin",
        full_name="System Administrator",
        hashed_password=password_helper.hash(DEFAULT_ADMIN_PASSWORD),
        group_id=1,
        is_active=True,
        is_superuser=True,
        is_verified=True,
        is_groupadmin=True,
        is_subjectmanager=True,
    )
    session.add(admin)

    # Global settings
    settings = [
        ApiSettings(name="app_title", value="CompIntel Monitor"),
        ApiSettings(name="navbar_color", value="slate"),
        ApiSettings(name="instance_label", value="DEV"),
    ]
    session.add_all(settings)

    await session.commit()
    print("[seed] Default data seeded successfully.")


async def _seed_playbook_templates(session: AsyncSession):
    """Seed playbook templates if table is empty."""
    count = await session.scalar(select(func.count()).select_from(PlaybookTemplates))
    if count and count > 0:
        print(f"[seed] Playbook templates already exist ({count} records), skipping.")
        return

    print(f"[seed] Seeding {len(PLAYBOOK_TEMPLATE_DEFAULTS)} playbook templates...")
    for tpl_data in PLAYBOOK_TEMPLATE_DEFAULTS:
        session.add(PlaybookTemplates(**tpl_data))
    await session.commit()
    print("[seed] Playbook templates seeded successfully.")


async def run_seed():
    async with SqlAsyncSession() as session:
        await _seed(session)
    async with SqlAsyncSession() as session:
        await _seed_playbook_templates(session)


def run_seed_sync():
    asyncio.run(run_seed())
