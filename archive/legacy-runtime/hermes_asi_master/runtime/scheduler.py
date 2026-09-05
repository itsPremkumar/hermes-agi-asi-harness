"""scheduler.py — Interval and time-based task scheduler.

The ``TaskScheduler`` runs async tasks on fixed intervals or at specific
times, with jitter and concurrency control.  Each task is a
``ScheduledTask`` that defines when and how it should run.

Usage::

    scheduler = TaskScheduler()

    async def heartbeat():
        print("beat")

    scheduler.add(ScheduledTask(name="hb", fn=heartbeat, interval_seconds=5.0))
    await scheduler.start()
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class TaskPriority(int, Enum):
    """Priority for scheduled tasks (higher = runs first)."""

    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class ScheduledTaskStatus(str, Enum):
    """Status of a scheduled task."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class TaskRunRecord:
    """Record of a single task execution."""

    run_id: str
    started_at: float
    finished_at: Optional[float] = None
    error: Optional[str] = None
    result: Any = None


@dataclass
class ScheduledTask:
    """A task that runs on a schedule.

    Parameters
    ----------
    name
        Unique name for the task.
    fn
        Async callable to execute.
    interval_seconds
        Run every ``interval_seconds`` seconds.
    run_at
        Optional specific time (Unix timestamp) to run next.  If both
        ``interval_seconds`` and ``run_at`` are given, ``run_at`` takes
        precedence for the next run.
    priority
        Task priority (higher runs first when multiple are due).
    max_concurrent
        Maximum concurrent executions (default 1).  If a task is already
        running and the concurrency limit is reached, the next run is
        skipped.
    max_runs
        Maximum number of executions.  None means unlimited.
    jitter
        Random jitter (seconds) added to the next run time.  Set to 0
        to disable.
    args / kwargs
        Positional and keyword arguments passed to ``fn``.
    """

    name: str
    fn: Callable[..., Awaitable[Any]]
    interval_seconds: Optional[float] = None
    run_at: Optional[float] = None
    priority: TaskPriority = TaskPriority.NORMAL
    max_concurrent: int = 1
    max_runs: Optional[int] = None
    jitter: float = 0.0
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    # runtime state
    status: ScheduledTaskStatus = ScheduledTaskStatus.IDLE
    run_count: int = 0
    running_count: int = 0
    last_run_at: Optional[float] = None
    last_error: Optional[str] = None
    next_run_at: Optional[float] = None
    history: List[TaskRunRecord] = field(default_factory=list)
    _task: Optional[asyncio.Task] = None

    def __post_init__(self) -> None:
        if self.interval_seconds is None and self.run_at is None:
            raise ValueError("either interval_seconds or run_at must be set")
        if self.interval_seconds is not None and self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")

    def compute_next_run(self, from_time: Optional[float] = None) -> float:
        """Compute the next run time."""
        now = from_time or time.time()
        if self.run_at is not None and self.run_at > now:
            base = self.run_at
        elif self.interval_seconds is not None:
            base = now + self.interval_seconds
        else:
            base = now
        if self.jitter > 0:
            base += random.uniform(0, self.jitter)
        return base


# ---------------------------------------------------------------------------
# Task Scheduler
# ---------------------------------------------------------------------------


class TaskScheduler:
    """Schedule and run async tasks on intervals or at specific times.

    Parameters
    ----------
    check_interval
        How often (seconds) to check for due tasks.
    max_history
        Maximum run history entries per task.
    on_error
        Optional callback ``(task, record)`` invoked when a task raises.
    """

    def __init__(
        self,
        check_interval: float = 0.5,
        max_history: int = 50,
        on_error: Optional[Callable[[ScheduledTask, TaskRunRecord], None]] = None,
    ) -> None:
        self._check_interval = check_interval
        self._max_history = max_history
        self._on_error = on_error
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(10)  # global concurrency cap

    # -- task management ----------------------------------------------------

    def add(self, task: ScheduledTask) -> ScheduledTask:
        """Add a scheduled task."""
        if task.name in self._tasks:
            raise ValueError(f"task {task.name!r} already exists")
        task.next_run_at = task.compute_next_run()
        self._tasks[task.name] = task
        return task

    def remove(self, name: str) -> Optional[ScheduledTask]:
        """Remove a task.  Returns the task if found."""
        task = self._tasks.pop(name, None)
        if task and task._task:
            task._task.cancel()
        return task

    def get(self, name: str) -> Optional[ScheduledTask]:
        return self._tasks.get(name)

    def pause(self, name: str) -> None:
        """Pause a task (skips future runs until resumed)."""
        task = self._tasks.get(name)
        if task:
            task.status = ScheduledTaskStatus.PAUSED

    def resume(self, name: str) -> None:
        """Resume a paused task."""
        task = self._tasks.get(name)
        if task and task.status == ScheduledTaskStatus.PAUSED:
            task.status = ScheduledTaskStatus.IDLE
            if task.next_run_at is None:
                task.next_run_at = task.compute_next_run()

    def enable(self, name: str) -> None:
        task = self._tasks.get(name)
        if task:
            task.status = ScheduledTaskStatus.IDLE

    def disable(self, name: str) -> None:
        task = self._tasks.get(name)
        if task:
            task.status = ScheduledTaskStatus.DISABLED

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        log.info("scheduler started with %d tasks", len(self._tasks))

    async def stop(self) -> None:
        """Stop the scheduler and cancel running tasks."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
        for task in self._tasks.values():
            if task._task and not task._task.done():
                task._task.cancel()
        log.info("scheduler stopped")

    # -- queries ------------------------------------------------------------

    @property
    def tasks(self) -> Dict[str, ScheduledTask]:
        return dict(self._tasks)

    @property
    def running(self) -> bool:
        return self._running

    def status(self) -> Dict[str, Any]:
        """Return a summary of all scheduled tasks."""
        return {
            "running": self._running,
            "total": len(self._tasks),
            "tasks": {
                name: {
                    "status": t.status.value,
                    "run_count": t.run_count,
                    "running_count": t.running_count,
                    "last_run_at": t.last_run_at,
                    "next_run_at": t.next_run_at,
                    "last_error": t.last_error,
                }
                for name, t in self._tasks.items()
            },
        }

    # -- internal -----------------------------------------------------------

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that dispatches due tasks."""
        while self._running:
            await asyncio.sleep(self._check_interval)
            now = time.time()
            # Sort by priority (desc) then next_run_at (asc)
            due_tasks = [
                t for t in self._tasks.values()
                if t.status == ScheduledTaskStatus.IDLE
                and t.next_run_at is not None
                and t.next_run_at <= now
            ]
            due_tasks.sort(key=lambda t: (-t.priority, t.next_run_at or 0))
            for task in due_tasks:
                if task.running_count >= task.max_concurrent:
                    continue
                if task.max_runs is not None and task.run_count >= task.max_runs:
                    task.status = ScheduledTaskStatus.DISABLED
                    continue
                task._task = asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a single task and record the result."""
        run_id = uuid.uuid4().hex[:12]
        started_at = time.time()
        record = TaskRunRecord(run_id=run_id, started_at=started_at)
        task.status = ScheduledTaskStatus.RUNNING
        task.running_count += 1
        try:
            async with self._semaphore:
                result = await task.fn(*task.args, **task.kwargs)
            record.result = result
        except asyncio.CancelledError:
            record.error = "cancelled"
            raise
        except Exception as exc:
            record.error = str(exc)
            task.last_error = str(exc)
            task.status = ScheduledTaskStatus.ERROR
            log.exception("task %s failed", task.name)
            if self._on_error:
                try:
                    self._on_error(task, record)
                except Exception:
                    log.exception("on_error callback error")
        finally:
            record.finished_at = time.time()
            task.running_count -= 1
            task.run_count += 1
            task.last_run_at = started_at
            task.history.append(record)
            if len(task.history) > self._max_history:
                task.history = task.history[-self._max_history :]
            # Schedule next run
            if task.interval_seconds is not None:
                task.next_run_at = task.compute_next_run()
            else:
                task.next_run_at = None
            if task.status != ScheduledTaskStatus.ERROR:
                task.status = ScheduledTaskStatus.IDLE
