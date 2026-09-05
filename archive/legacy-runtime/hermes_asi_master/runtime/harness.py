"""harness.py — Top-level integration for the 24/7 runtime.

The ``HarnessRuntime`` wires together the watchdog, scheduler, and cron
subsystems into a single component that can be started and stopped.  It
also provides a health endpoint and status aggregation.

Usage::

    runtime = HarnessRuntime()
    runtime.watchdog.register("worker", target=worker_fn)
    runtime.cron_tab.add(CronJob(name="heartbeat", schedule="*/5 * * * *", task=hb))
    await runtime.start()
    # ... later ...
    await runtime.stop()
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .watchdog import Watchdog, WatchdogConfig, ProcessHandle, ProcessStatus
from .scheduler import TaskScheduler, ScheduledTask, TaskPriority
from .cron import CronJob, CronTab, CronExpression, CronField

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class HarnessRuntimeConfig:
    """Configuration for the harness runtime.

    Parameters
    ----------
    watchdog
        Watchdog configuration.
    scheduler_check_interval
        How often (seconds) the scheduler checks for due tasks.
    cron_check_interval
        How often (seconds) the cron dispatcher checks for due jobs.
    health_check_interval
        How often (seconds) to run the built-in health check.
    """

    watchdog: WatchdogConfig = field(default_factory=WatchdogConfig)
    scheduler_check_interval: float = 0.5
    cron_check_interval: float = 1.0
    health_check_interval: float = 30.0


# ---------------------------------------------------------------------------
# Harness Runtime
# ---------------------------------------------------------------------------


class HarnessRuntime:
    """Top-level 24/7 runtime for hermes-agi-asi-harness.

    Integrates the watchdog, scheduler, and cron subsystems.

    Parameters
    ----------
    config
        Runtime configuration.
    """

    def __init__(
        self,
        config: Optional[HarnessRuntimeConfig] = None,
    ) -> None:
        self._config = config or HarnessRuntimeConfig()
        self._watchdog = Watchdog(config=self._config.watchdog)
        self._scheduler = TaskScheduler(
            check_interval=self._config.scheduler_check_interval
        )
        self._cron_tab = CronTab(check_interval=self._config.cron_check_interval)
        self._running = False
        self._start_time: Optional[float] = None
        self._health_check_task: Optional[asyncio.Task] = None

    # -- subsystem access ---------------------------------------------------

    @property
    def watchdog(self) -> Watchdog:
        return self._watchdog

    @property
    def scheduler(self) -> TaskScheduler:
        return self._scheduler

    @property
    def cron_tab(self) -> CronTab:
        return self._cron_tab

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Start the harness runtime and all subsystems."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        await self._watchdog.start()
        await self._scheduler.start()
        await self._cron_tab.start()
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        log.info("harness runtime started")

    async def stop(self) -> None:
        """Stop the harness runtime and all subsystems."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
        await self._cron_tab.stop()
        await self._scheduler.stop()
        await self._watchdog.stop()
        log.info("harness runtime stopped")

    # -- queries ------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._running

    @property
    def uptime_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def status(self) -> Dict[str, Any]:
        """Return a comprehensive status report."""
        return {
            "running": self._running,
            "uptime_seconds": self.uptime_seconds,
            "watchdog": self._watchdog.status(),
            "scheduler": self._scheduler.status(),
            "cron": self._cron_tab.status(),
        }

    def health(self) -> Dict[str, Any]:
        """Return a health check result."""
        wd_status = self._watchdog.status()
        failed_processes = [
            name
            for name, info in wd_status.get("processes", {}).items()
            if info.get("status") == ProcessStatus.FAILED.value
        ]
        total_tasks = self._scheduler.status().get("total", 0)
        error_tasks = sum(
            1
            for t in self._scheduler.tasks.values()
            if t.status.value == "error"
        )
        total_cron_jobs = self._cron_tab.status().get("total", 0)
        error_cron_jobs = sum(
            1
            for j in self._cron_tab.jobs.values()
            if j.status.value == "error"
        )
        healthy = (
            len(failed_processes) == 0
            and error_tasks == 0
            and error_cron_jobs == 0
        )
        return {
            "healthy": healthy,
            "failed_processes": failed_processes,
            "error_tasks": error_tasks,
            "error_cron_jobs": error_cron_jobs,
            "uptime_seconds": self.uptime_seconds,
        }

    # -- internal -----------------------------------------------------------

    async def _health_check_loop(self) -> None:
        """Periodic health check that logs warnings."""
        while self._running:
            await asyncio.sleep(self._config.health_check_interval)
            h = self.health()
            if not h["healthy"]:
                log.warning("harness health check FAILED: %s", h)
            else:
                log.debug("harness health check OK (uptime %.0fs)", h["uptime_seconds"])
