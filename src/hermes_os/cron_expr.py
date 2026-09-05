"""cron.py — Cron-style job scheduling.

Provides ``CronExpression`` for parsing standard cron expressions,
``CronJob`` for defining a named cron job with a task, and ``CronTab``
for managing and dispatching a set of cron jobs.

Usage::

    cron_tab = CronTab()

    async def backup():
        print("backing up")

    job = CronJob(name="backup", schedule="0 2 * * *", task=backup)
    cron_tab.add(job)
    await cron_tab.start()
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cron expression parser
# ---------------------------------------------------------------------------


class CronField:
    """A single field of a cron expression (minute, hour, etc.)."""

    def __init__(self, raw: str, min_val: int, max_val: int) -> None:
        self.raw = raw
        self.min_val = min_val
        self.max_val = max_val
        self.values: Set[int] = self._parse(raw)

    def _parse(self, raw: str) -> Set[int]:
        """Parse a cron field into a set of integer values."""
        if raw == "*":
            return set(range(self.min_val, self.max_val + 1))
        if raw == "?":
            return set()

        values: Set[int] = set()
        for part in raw.split(","):
            values.update(self._parse_part(part))
        return values

    def _parse_part(self, part: str) -> Set[int]:
        """Parse a single part of a field (e.g., '1-5', '*/2', '1')."""
        if "/" in part:
            base, step_str = part.split("/", 1)
            step = int(step_str)
            if base == "*":
                start = self.min_val
                end = self.max_val
            elif "-" in base:
                start_s, end_s = base.split("-", 1)
                start, end = int(start_s), int(end_s)
            else:
                start = int(base)
                end = self.max_val
            return set(range(start, end + 1, step))
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
            return set(range(start, end + 1))
        return {int(part)}

    def matches(self, value: int) -> bool:
        return value in self.values

    def next(self, current: int) -> Optional[int]:
        """Return the next matching value >= current, or None."""
        candidates = sorted(v for v in self.values if v >= current)
        return candidates[0] if candidates else None

    def first(self) -> Optional[int]:
        return min(self.values) if self.values else None


@dataclass
class CronExpression:
    """Parsed cron expression.

    Supports standard 5-field cron with optional 6th field for seconds::

        minute hour day-of-month month day-of-week [? year]

    Each field supports:
    - ``*`` (any value)
    - ``?`` (no specific value, used for day-of-month or day-of-week)
    - ``5`` (specific value)
    - ``1-5`` (range)
    - ``*/2`` (step)
    - ``1,3,5`` (list)
    """

    raw: str
    minute: CronField = field(init=False)
    hour: CronField = field(init=False)
    day_of_month: CronField = field(init=False)
    month: CronField = field(init=False)
    day_of_week: CronField = field(init=False)
    year: Optional[CronField] = field(init=False, default=None)

    # Field definitions: (min, max)
    _FIELDS: Tuple[Tuple[str, int, int], ...] = (
        ("minute", 0, 59),
        ("hour", 0, 23),
        ("day_of_month", 1, 31),
        ("month", 1, 12),
        ("day_of_week", 0, 6),  # 0 = Sunday
        ("year", 1970, 2099),
    )

    def __post_init__(self) -> None:
        parts = self.raw.strip().split()
        if len(parts) < 5:
            raise ValueError(
                f"cron expression must have at least 5 fields, got {len(parts)}: {self.raw!r}"
            )
        # Pad to 6 fields if needed
        while len(parts) < 6:
            parts.append("*")
        for i, (name, min_val, max_val) in enumerate(self._FIELDS):
            if i < len(parts):
                field = CronField(parts[i], min_val, max_val)
            else:
                field = CronField("*", min_val, max_val)
            if name == "year":
                self.year = field
            else:
                setattr(self, name, field)

    def matches(self, dt: datetime) -> bool:
        """Check if a datetime matches this cron expression."""
        if not self.minute.matches(dt.minute):
            return False
        if not self.hour.matches(dt.hour):
            return False
        if not self.day_of_month.matches(dt.day):
            return False
        if not self.month.matches(dt.month):
            return False
        # day_of_week: Python's weekday() returns 0=Monday, cron uses 0=Sunday
        cron_dow = (dt.weekday() + 1) % 7
        if not self.day_of_week.matches(cron_dow):
            return False
        if self.year is not None and not self.year.matches(dt.year):
            return False
        return True

    def next_run(self, after: Optional[datetime] = None) -> Optional[datetime]:
        """Compute the next run time after ``after`` (default: now)."""
        after = after or datetime.now(timezone.utc)
        # Start from the next minute
        candidate = after.replace(second=0, microsecond=0)
        # Search up to 4 years ahead
        max_years = 4
        for _ in range(max_years * 366 * 24 * 60):
            candidate = candidate.replace(minute=candidate.minute)
            if self._matches_datetime(candidate):
                return candidate
            # Increment by 1 minute
            candidate = self._add_minutes(candidate, 1)
        return None

    def _matches_datetime(self, dt: datetime) -> bool:
        if not self.year.matches(dt.year):
            return False
        if not self.month.matches(dt.month):
            return False
        if not self.day_of_month.matches(dt.day):
            return False
        cron_dow = (dt.weekday() + 1) % 7
        if not self.day_of_week.matches(cron_dow):
            return False
        if not self.hour.matches(dt.hour):
            return False
        if not self.minute.matches(dt.minute):
            return False
        return True

    @staticmethod
    def _add_minutes(dt: datetime, minutes: int) -> datetime:
        """Add minutes to a datetime, handling month/year rollover."""
        from datetime import timedelta

        return dt + timedelta(minutes=minutes)


# ---------------------------------------------------------------------------
# Cron Job
# ---------------------------------------------------------------------------


class CronJobStatus(str, Enum):
    """Status of a cron job."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class CronRunRecord:
    """Record of a single cron job execution."""

    run_id: str
    scheduled_at: float
    started_at: float
    finished_at: Optional[float] = None
    error: Optional[str] = None
    result: Any = None


@dataclass
class CronJob:
    """A cron job with a schedule and task.

    Parameters
    ----------
    name
        Unique name for the job.
    schedule
        Cron expression string.
    task
        Async callable to execute.
    args / kwargs
        Positional and keyword arguments passed to ``task``.
    max_concurrent
        Maximum concurrent executions.
    max_runs
        Maximum number of executions (None = unlimited).
    """

    name: str
    schedule: str
    task: Callable[..., Awaitable[Any]]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    max_concurrent: int = 1
    max_runs: Optional[int] = None
    # runtime state
    expression: CronExpression = field(init=False)
    status: CronJobStatus = CronJobStatus.IDLE
    run_count: int = 0
    running_count: int = 0
    last_run_at: Optional[float] = None
    last_error: Optional[str] = None
    next_run_at: Optional[float] = None
    history: List[CronRunRecord] = field(default_factory=list)
    _task: Optional[asyncio.Task] = None

    def __post_init__(self) -> None:
        self.expression = CronExpression(self.schedule)
        self._compute_next_run()

    def _compute_next_run(self, after: Optional[datetime] = None) -> None:
        dt = self.expression.next_run(after)
        self.next_run_at = dt.timestamp() if dt else None


# ---------------------------------------------------------------------------
# CronTab
# ---------------------------------------------------------------------------


class CronTab:
    """Manage and dispatch a set of cron jobs.

    Parameters
    ----------
    check_interval
        How often (seconds) to check for due jobs.
    max_history
        Maximum run history entries per job.
    on_error
        Optional callback ``(job, record)`` invoked when a job raises.
    """

    def __init__(
        self,
        check_interval: float = 1.0,
        max_history: int = 50,
        on_error: Optional[Callable[[CronJob, CronRunRecord], None]] = None,
    ) -> None:
        self._check_interval = check_interval
        self._max_history = max_history
        self._on_error = on_error
        self._jobs: Dict[str, CronJob] = {}
        self._running = False
        self._dispatcher_task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(10)

    # -- job management -----------------------------------------------------

    def add(self, job: CronJob) -> CronJob:
        """Add a cron job."""
        if job.name in self._jobs:
            raise ValueError(f"cron job {job.name!r} already exists")
        self._jobs[job.name] = job
        return job

    def remove(self, name: str) -> Optional[CronJob]:
        """Remove a cron job.  Returns the job if found."""
        job = self._jobs.pop(name, None)
        if job and job._task:
            job._task.cancel()
        return job

    def get(self, name: str) -> Optional[CronJob]:
        return self._jobs.get(name)

    def pause(self, name: str) -> None:
        job = self._jobs.get(name)
        if job:
            job.status = CronJobStatus.PAUSED

    def resume(self, name: str) -> None:
        job = self._jobs.get(name)
        if job and job.status == CronJobStatus.PAUSED:
            job.status = CronJobStatus.IDLE

    def enable(self, name: str) -> None:
        job = self._jobs.get(name)
        if job:
            job.status = CronJobStatus.IDLE

    def disable(self, name: str) -> None:
        job = self._jobs.get(name)
        if job:
            job.status = CronJobStatus.DISABLED

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Start the cron dispatcher."""
        if self._running:
            return
        self._running = True
        self._dispatcher_task = asyncio.create_task(self._dispatcher_loop())
        log.info("cron dispatcher started with %d jobs", len(self._jobs))

    async def stop(self) -> None:
        """Stop the cron dispatcher."""
        self._running = False
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass
            self._dispatcher_task = None
        for job in self._jobs.values():
            if job._task and not job._task.done():
                job._task.cancel()
        log.info("cron dispatcher stopped")

    # -- queries ------------------------------------------------------------

    @property
    def jobs(self) -> Dict[str, CronJob]:
        return dict(self._jobs)

    @property
    def running(self) -> bool:
        return self._running

    def status(self) -> Dict[str, Any]:
        """Return a summary of all cron jobs."""
        return {
            "running": self._running,
            "total": len(self._jobs),
            "jobs": {
                name: {
                    "status": j.status.value,
                    "schedule": j.schedule,
                    "run_count": j.run_count,
                    "running_count": j.running_count,
                    "last_run_at": j.last_run_at,
                    "next_run_at": j.next_run_at,
                    "last_error": j.last_error,
                }
                for name, j in self._jobs.items()
            },
        }

    # -- internal -----------------------------------------------------------

    async def _dispatcher_loop(self) -> None:
        """Main dispatcher loop that checks for due jobs."""
        while self._running:
            await asyncio.sleep(self._check_interval)
            now = time.time()
            for job in list(self._jobs.values()):
                if job.status != CronJobStatus.IDLE:
                    continue
                if job.next_run_at is None or job.next_run_at > now:
                    continue
                if job.running_count >= job.max_concurrent:
                    continue
                if job.max_runs is not None and job.run_count >= job.max_runs:
                    job.status = CronJobStatus.DISABLED
                    continue
                job._task = asyncio.create_task(self._execute_job(job))

    async def _execute_job(self, job: CronJob) -> None:
        """Execute a single cron job."""
        run_id = uuid.uuid4().hex[:12]
        scheduled_at = job.next_run_at or time.time()
        started_at = time.time()
        record = CronRunRecord(
            run_id=run_id,
            scheduled_at=scheduled_at,
            started_at=started_at,
        )
        job.status = CronJobStatus.RUNNING
        job.running_count += 1
        try:
            async with self._semaphore:
                result = await job.task(*job.args, **job.kwargs)
            record.result = result
        except asyncio.CancelledError:
            record.error = "cancelled"
            raise
        except Exception as exc:
            record.error = str(exc)
            job.last_error = str(exc)
            job.status = CronJobStatus.ERROR
            log.exception("cron job %s failed", job.name)
            if self._on_error:
                try:
                    self._on_error(job, record)
                except Exception:
                    log.exception("on_error callback error")
        finally:
            record.finished_at = time.time()
            job.running_count -= 1
            job.run_count += 1
            job.last_run_at = started_at
            job.history.append(record)
            if len(job.history) > self._max_history:
                job.history = job.history[-self._max_history :]
            # Schedule next run
            job._compute_next_run(datetime.fromtimestamp(scheduled_at, tz=timezone.utc))
            if job.status != CronJobStatus.ERROR:
                job.status = CronJobStatus.IDLE
