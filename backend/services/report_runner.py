"""
Report runner: orchestrates Quill agent to generate reports from analyses.
"""
import asyncio
import os
from datetime import datetime, timezone

from backend.config import WORK_DIR
from backend.db.session import SqlAsyncSession
from backend.db.tables.analyses import AnalysesTable
from backend.db.tables.reports import ReportsTable
from backend.db.tables.group_subjects import GroupSubjectsTable
from backend.db.tables.group_settings import GroupSettingsTable
from backend.services.logger_service import get_logger

log = get_logger("report_runner")

DATA_DIR = os.path.join(WORK_DIR, "data")


async def run_report(analysis_id: int, gsubject_id: int, report_type: str = "battlecard") -> None:
    """Run Quill report generation. Designed for BackgroundTasks."""
    async with SqlAsyncSession() as session:
        try:
            await _run_report_inner(session, analysis_id, gsubject_id, report_type)
        except Exception as e:
            log.error("report_failed", analysis_id=analysis_id, error=str(e))


async def _run_report_inner(
    session, analysis_id: int, gsubject_id: int, report_type: str
) -> None:
    analyses_table = AnalysesTable(session)
    reports_table = ReportsTable(session)
    subjects_table = GroupSubjectsTable(session)

    # Load analysis
    analysis = await analyses_table.get_by_id(analysis_id)
    if analysis is None or analysis.status != "ok":
        return

    # Load subject
    subject = await subjects_table.get_by_id(gsubject_id)
    if subject is None:
        return

    subject_name = subject.gsubject_name
    subject_type = subject.gsubject_type.value if hasattr(subject.gsubject_type, "value") else str(subject.gsubject_type)

    # Create report record
    report = await reports_table.create(
        analysis_id=analysis_id,
        gsubject_id=gsubject_id,
        report_type=report_type,
    )

    # Update status to running
    await reports_table.update(report.report_id, status="running")

    # Build analysis data for the agent
    analysis_data = {
        "summary": analysis.summary,
        "key_findings": analysis.key_findings,
        "signals": analysis.signals,
    }

    # Run Quill agent
    from backend.agents.quill_report import run_quill_report

    log.info("report_starting", subject=subject_name, report_type=report_type)

    try:
        result = await asyncio.to_thread(
            run_quill_report, subject_name, subject_type, analysis_data, report_type
        )
    except Exception as e:
        await reports_table.update(
            report.report_id,
            status="error",
            error_detail=f"Quill agent error: {str(e)[:500]}",
        )
        log.error("quill_error", subject=subject_name, error=str(e))
        return

    # Save results
    await reports_table.update(
        report.report_id,
        title=result.get("title", ""),
        content_markdown=result.get("content_markdown", ""),
        status="ok",
    )

    # Check if markdown file output is enabled
    settings_table = GroupSettingsTable(session)
    md_setting = await settings_table.get_one(subject.group_id, "enable_markdown_reports")
    if md_setting and md_setting.value.lower() == "true":
        _save_markdown_file(
            group_id=subject.group_id,
            gsubject_id=gsubject_id,
            report_type=report_type,
            report_id=report.report_id,
            content=result.get("content_markdown", ""),
        )

    log.info("report_complete", subject=subject_name, report_type=report_type, title=result.get("title", ""))


def _save_markdown_file(
    group_id: int,
    gsubject_id: int,
    report_type: str,
    report_id: int,
    content: str,
) -> None:
    """Save report as a markdown file."""
    dir_path = os.path.join(DATA_DIR, str(group_id), str(gsubject_id), "reports")
    os.makedirs(dir_path, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    file_path = os.path.join(dir_path, f"{date_str}_{report_type}_{report_id}.md")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
