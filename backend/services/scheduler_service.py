"""
Scheduler service: APScheduler-based periodic collection dispatcher.

Checks for due sources every SCHEDULER_CHECK_INTERVAL_SECONDS and dispatches
collection tasks. Manual start/stop via API (not auto-start).
"""
import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.config import SCHEDULER_CHECK_INTERVAL_SECONDS
from backend.db.session import SqlAsyncSession
from backend.db.tables.subject_sources import SubjectSourcesTable
from backend.services.collection_runner import run_collection
from backend.services.logger_service import get_logger

log = get_logger("scheduler")


class SchedulerService:
    def __init__(self):
        self._scheduler: AsyncIOScheduler | None = None
        self._in_flight: set[int] = set()

    @property
    def is_running(self) -> bool:
        return self._scheduler is not None and self._scheduler.running

    @property
    def next_check_time(self) -> datetime | None:
        if not self.is_running or not self._scheduler:
            return None
        job = self._scheduler.get_job("check_due_sources")
        return job.next_run_time if job else None

    def start(self):
        if self.is_running:
            return
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._check_and_dispatch,
            "interval",
            seconds=SCHEDULER_CHECK_INTERVAL_SECONDS,
            id="check_due_sources",
            replace_existing=True,
        )
        self._scheduler.start()
        log.info("scheduler_started", interval=SCHEDULER_CHECK_INTERVAL_SECONDS)

    def stop(self):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            self._in_flight.clear()
            log.info("scheduler_stopped")

    async def _check_and_dispatch(self):
        """Periodic job: find due sources and dispatch collection tasks."""
        async with SqlAsyncSession() as session:
            sources = await SubjectSourcesTable(session).get_all_due_sources()

        dispatched = 0
        for source in sources:
            if source.source_id not in self._in_flight:
                self._in_flight.add(source.source_id)
                asyncio.create_task(self._run_and_track(source.source_id))
                dispatched += 1

        if dispatched > 0 or len(sources) > 0:
            log.info(
                "scheduler_check",
                due=len(sources),
                dispatched=dispatched,
                in_flight=len(self._in_flight),
            )

    async def _run_and_track(self, source_id: int):
        """Run collection and remove from in-flight set when done."""
        try:
            await run_collection(source_id)
        finally:
            self._in_flight.discard(source_id)


# Module-level singleton
scheduler = SchedulerService()
