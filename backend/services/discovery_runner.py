"""
Discovery runner: orchestrates CrewAI Signal Discovery Agent.

Loads a subject's sources, builds the discovery request,
calls the agent, and updates user_inputs on each source.
"""
import asyncio

from backend.db.session import SqlAsyncSession
from backend.db.tables.subject_sources import SubjectSourcesTable
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.db.tables.playbook_templates import PlaybookTemplatesTable
from backend.services.logger_service import get_logger

log = get_logger("discovery_runner")


async def run_discovery(gsubject_id: int) -> None:
    """Run auto-discovery for a subject's sources. Designed for BackgroundTasks."""
    async with SqlAsyncSession() as session:
        try:
            await _run_discovery_inner(session, gsubject_id)
        except Exception as e:
            log.error("discovery_failed", gsubject_id=gsubject_id, error=str(e))
            # Try to update subject status on failure
            try:
                async with SqlAsyncSession() as err_session:
                    await GroupSubjectsTable(err_session).update_subject(
                        gsubject_id,
                        gsubject_status="warning",
                        gsubject_status_text=f"Discovery failed: {str(e)[:200]}",
                    )
            except Exception:
                pass


async def _run_discovery_inner(session, gsubject_id: int) -> None:
    subjects_table = GroupSubjectsTable(session)
    sources_table = SubjectSourcesTable(session)
    templates_table = PlaybookTemplatesTable(session)

    # Load subject
    subject = await subjects_table.get_by_id(gsubject_id)
    if subject is None:
        log.warning("subject_not_found", gsubject_id=gsubject_id)
        return

    subject_name = subject.gsubject_name
    subject_type = subject.gsubject_type.value if hasattr(subject.gsubject_type, "value") else str(subject.gsubject_type)

    # Update status to discovering
    await subjects_table.update_subject(
        gsubject_id,
        gsubject_status="info",
        gsubject_status_text="Auto-discovery running...",
    )

    # Load sources that need discovery (empty user_inputs and have a template)
    all_sources = await sources_table.get_by_subject(gsubject_id)
    sources_needing_discovery = []
    for source in all_sources:
        # Skip sources that already have user_inputs configured
        if source.user_inputs and any(v for v in source.user_inputs.values() if v):
            continue
        # Skip sources without a template (custom sources)
        if source.template_id is None:
            continue
        sources_needing_discovery.append(source)

    if not sources_needing_discovery:
        await subjects_table.update_subject(
            gsubject_id,
            gsubject_status="ok",
            gsubject_status_text="All sources already configured",
        )
        return

    # Build sources_info for the agent
    sources_info = []
    for source in sources_needing_discovery:
        template = await templates_table.get_by_id(source.template_id)
        schema = template.user_inputs_schema if template else {}
        sources_info.append({
            "source_id": source.source_id,
            "category_key": source.category_key,
            "category_name": source.category_name,
            "user_inputs_schema": schema,
        })

    # Run the CrewAI agent (sync call wrapped in thread)
    from backend.agents.signal_discovery import run_discovery as agent_run_discovery

    log.info("discovery_starting", subject=subject_name, sources=len(sources_info))

    try:
        result = await asyncio.to_thread(
            agent_run_discovery, subject_name, subject_type, sources_info
        )
    except Exception as e:
        await subjects_table.update_subject(
            gsubject_id,
            gsubject_status="warning",
            gsubject_status_text=f"Discovery agent error: {str(e)[:200]}",
        )
        log.error("agent_error", subject=subject_name, error=str(e))
        return

    # Apply discovered values to sources
    filled_count = 0
    for source in sources_needing_discovery:
        discovered = result.get(source.category_key)
        if discovered and isinstance(discovered, dict):
            await sources_table.update_source(
                source.source_id,
                user_inputs=discovered,
            )
            filled_count += 1
            log.info(
                "source_discovered",
                source_id=source.source_id,
                category=source.category_key,
                inputs=discovered,
            )

    total = len(sources_needing_discovery)
    await subjects_table.update_subject(
        gsubject_id,
        gsubject_status="ok",
        gsubject_status_text=f"Discovery complete: {filled_count} of {total} sources configured",
    )

    log.info(
        "discovery_complete",
        subject=subject_name,
        filled=filled_count,
        total=total,
    )
