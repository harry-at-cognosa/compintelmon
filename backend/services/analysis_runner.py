"""
Analysis runner: orchestrates Fusion agent to analyze collected data for a subject.
"""
import asyncio
import glob
import json
import os

from backend.config import WORK_DIR
from backend.db.session import SqlAsyncSession
from backend.db.tables.analyses import AnalysesTable
from backend.db.tables.subject_sources import SubjectSourcesTable
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.services.logger_service import get_logger

log = get_logger("analysis_runner")

DATA_DIR = os.path.join(WORK_DIR, "data")


async def run_analysis(gsubject_id: int) -> None:
    """Run Fusion analysis for a subject. Designed for BackgroundTasks."""
    async with SqlAsyncSession() as session:
        try:
            await _run_analysis_inner(session, gsubject_id)
        except Exception as e:
            log.error("analysis_failed", gsubject_id=gsubject_id, error=str(e))


async def _run_analysis_inner(session, gsubject_id: int) -> None:
    subjects_table = GroupSubjectsTable(session)
    sources_table = SubjectSourcesTable(session)
    analyses_table = AnalysesTable(session)

    # Load subject
    subject = await subjects_table.get_by_id(gsubject_id)
    if subject is None:
        return

    subject_name = subject.gsubject_name
    subject_type = subject.gsubject_type.value if hasattr(subject.gsubject_type, "value") else str(subject.gsubject_type)

    # Load sources
    sources = await sources_table.get_by_subject(gsubject_id)
    if not sources:
        return

    # Create analysis record
    analysis = await analyses_table.create(gsubject_id, analysis_type="full")

    # Load latest collected data for each source
    sources_data = []
    sources_analyzed = []
    data_dir = os.path.join(DATA_DIR, str(subject.group_id), str(gsubject_id))

    for source in sources:
        if not source.enabled:
            continue
        # Find latest data file for this source
        content = _load_latest_collected_data(data_dir, source.category_key)
        if content:
            sources_data.append({
                "category_key": source.category_key,
                "category_name": source.category_name,
                "signal_instructions": source.signal_instructions or "",
                "raw_content": content,
            })
            sources_analyzed.append(source.category_key)

    if not sources_data:
        await analyses_table.update(
            analysis.analysis_id,
            status="error",
            error_detail="No collected data found for any source",
        )
        return

    # Update status to running
    await analyses_table.update(analysis.analysis_id, status="running")

    # Run Fusion agent
    from backend.agents.fusion_analysis import run_fusion_analysis

    log.info("analysis_starting", subject=subject_name, sources=len(sources_data))

    try:
        result = await asyncio.to_thread(
            run_fusion_analysis, subject_name, subject_type, sources_data
        )
    except Exception as e:
        await analyses_table.update(
            analysis.analysis_id,
            status="error",
            error_detail=f"Fusion agent error: {str(e)[:500]}",
        )
        log.error("fusion_error", subject=subject_name, error=str(e))
        return

    # Save results
    await analyses_table.update(
        analysis.analysis_id,
        summary=result.get("summary", ""),
        key_findings=result.get("key_findings", []),
        signals=result.get("signals", []),
        raw_analysis=json.dumps(result, default=str),
        sources_analyzed=sources_analyzed,
        status="ok",
    )

    log.info(
        "analysis_complete",
        subject=subject_name,
        findings=len(result.get("key_findings", [])),
        signals=len(result.get("signals", [])),
    )


def _load_latest_collected_data(data_dir: str, category_key: str) -> str | None:
    """Load the most recent collected data file for a source category."""
    if not os.path.isdir(data_dir):
        return None

    pattern = os.path.join(data_dir, f"*_{category_key}_*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    if not files:
        return None

    try:
        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("raw_content", "")
    except (json.JSONDecodeError, OSError):
        return None
