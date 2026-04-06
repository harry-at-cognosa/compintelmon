"""
Collection runner: orchestrates source collection.

Reads a source config, interpolates variables, dispatches to the correct
collector, records results in the database, and writes collected data to disk.
"""
import json
import os
from datetime import datetime, timezone

from backend.config import WORK_DIR
from backend.db.session import SqlAsyncSession
from backend.db.tables.subject_sources import SubjectSourcesTable
from backend.db.tables.subject_source_runs import SubjectSourceRunsTable
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.db.tables.group_settings import GroupSettingsTable
from backend.collectors.base import (
    COLLECTOR_REGISTRY,
    CollectionResult,
    interpolate_config,
    resolve_url,
)
# Import collectors to register them
import backend.collectors.httpx_collector  # noqa: F401
import backend.collectors.feedparser_collector  # noqa: F401
import backend.collectors.crawl4ai_collector  # noqa: F401
import backend.collectors.praw_collector  # noqa: F401
import backend.collectors.api_collector  # noqa: F401

from backend.services.logger_service import get_logger

log = get_logger("collection_runner")

DATA_DIR = os.path.join(WORK_DIR, "data")


async def run_collection(source_id: int) -> None:
    """Run collection for a single source. Designed for BackgroundTasks."""
    async with SqlAsyncSession() as session:
        try:
            await _run_collection_inner(session, source_id)
        except Exception as e:
            log.error("collection_failed", source_id=source_id, error=str(e))


async def _run_collection_inner(session, source_id: int) -> None:
    sources_table = SubjectSourcesTable(session)
    runs_table = SubjectSourceRunsTable(session)

    # Load source
    source = await sources_table.get_by_id(source_id)
    if source is None or source.deleted == 1:
        log.warning("source_not_found", source_id=source_id)
        return

    # Load subject metadata
    subjects_table = GroupSubjectsTable(session)
    subject = await subjects_table.get_by_id(source.gsubject_id)
    if subject is None:
        log.warning("subject_not_found", gsubject_id=source.gsubject_id)
        return

    subject_metadata = {
        "gsubject_name": subject.gsubject_name,
        "gsubject_type": subject.gsubject_type,
        "gsubject_id": str(subject.gsubject_id),
    }

    # Load group settings (for API keys like reddit_client_id, twitter_bearer_token)
    group_settings = {}
    settings_list = await GroupSettingsTable(session).get_all_for_group(subject.group_id)
    for gs in settings_list:
        group_settings[gs.name] = gs.value

    # Check if collector exists
    tool = source.collection_tool
    collector = COLLECTOR_REGISTRY.get(tool)

    if collector is None:
        # Unimplemented tool — mark as skipped
        run = await runs_table.create_run(source_id, status="skipped")
        await runs_table.update_run(
            run.run_id,
            finished_at=datetime.now(timezone.utc),
            status="skipped",
            error_detail=f"Collector '{tool}' not yet implemented",
        )
        await sources_table.update_source(
            source_id,
            last_collected_at=datetime.now(timezone.utc),
            last_status="skipped",
            last_status_text=f"Collector '{tool}' not yet implemented",
        )
        return

    # Check if required group settings are configured
    raw_config = source.collection_config or {}
    required_setting = raw_config.get("requires_group_setting")
    if required_setting and required_setting not in group_settings:
        run = await runs_table.create_run(source_id, status="error")
        error_msg = f"Missing group setting: {required_setting}"
        await runs_table.update_run(
            run.run_id, finished_at=datetime.now(timezone.utc),
            status="error", error_detail=error_msg,
        )
        await sources_table.update_source(
            source_id, last_collected_at=datetime.now(timezone.utc),
            last_status="error", last_status_text=error_msg,
        )
        return

    # Interpolate config (merge user_inputs + subject_metadata + group_settings)
    config = interpolate_config(
        raw_config,
        {**(source.user_inputs or {}), **group_settings},
        subject_metadata,
    )

    # Check if URL is resolved
    url = resolve_url(config)
    if not url and config.get("url_template"):
        run = await runs_table.create_run(source_id, status="error")
        error_msg = "Missing user_inputs — URL not configured"
        await runs_table.update_run(
            run.run_id,
            finished_at=datetime.now(timezone.utc),
            status="error",
            error_detail=error_msg,
        )
        await sources_table.update_source(
            source_id,
            last_collected_at=datetime.now(timezone.utc),
            last_status="error",
            last_status_text=error_msg,
        )
        return

    # Create run record
    run = await runs_table.create_run(source_id, status="running")

    # Execute collector
    try:
        result = await collector(config)
    except Exception as e:
        result = CollectionResult(status="error", error=str(e))

    now = datetime.now(timezone.utc)

    # Handle feedparser fallback
    if (
        result.status == "error"
        and result.error == "empty_feed_try_fallback"
        and config.get("fallback_tool")
    ):
        fallback_tool = config["fallback_tool"]
        fallback_collector = COLLECTOR_REGISTRY.get(fallback_tool)
        if fallback_collector:
            fallback_config = {**config, "url_template": config.get("fallback_url_template", "")}
            fallback_config["url_template"] = interpolate_config(
                {"url_template": fallback_config["url_template"]},
                source.user_inputs or {},
                subject_metadata,
            ).get("url_template", "")
            # Re-resolve URL for fallback
            fallback_url = fallback_config.get("url_template")
            if fallback_url and "{" not in fallback_url:
                fallback_config["url_template"] = fallback_url
                try:
                    result = await fallback_collector(fallback_config)
                except Exception as e:
                    result = CollectionResult(status="error", error=f"Fallback error: {str(e)}")

    # Save collected data to file
    if result.status == "ok" and result.raw_content:
        _save_collected_data(
            group_id=subject.group_id,
            gsubject_id=source.gsubject_id,
            category_key=source.category_key,
            run_id=run.run_id,
            result=result,
        )

    # Update run record
    await runs_table.update_run(
        run.run_id,
        finished_at=now,
        status=result.status,
        items_collected=len(result.items),
        error_detail=result.error,
        data_hash=result.content_hash or None,
    )

    # Update source status
    status_text = result.error or f"Collected {len(result.items)} items"
    if result.status == "no_change":
        status_text = "No changes detected"

    await sources_table.update_source(
        source_id,
        last_collected_at=now,
        last_status=result.status,
        last_status_text=status_text,
    )

    log.info(
        "collection_complete",
        source_id=source_id,
        tool=tool,
        status=result.status,
        items=len(result.items),
    )


def _save_collected_data(
    group_id: int,
    gsubject_id: int,
    category_key: str,
    run_id: int,
    result: CollectionResult,
) -> None:
    """Save collected data as a JSON file."""
    dir_path = os.path.join(DATA_DIR, str(group_id), str(gsubject_id))
    os.makedirs(dir_path, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    file_path = os.path.join(dir_path, f"{date_str}_{category_key}_{run_id}.json")
    data = {
        "run_id": run_id,
        "category_key": category_key,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": result.status,
        "content_hash": result.content_hash,
        "items": result.items,
        "raw_content": result.raw_content[:100000],  # cap at 100KB
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
