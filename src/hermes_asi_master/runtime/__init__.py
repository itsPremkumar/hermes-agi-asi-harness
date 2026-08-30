"""runtime — 24/7 Harness Runtime Environment.

Provides the watchdog, scheduler, and cron subsystems that keep the
hermes-agi-asi-harness running continuously:

  * ``Watchdog`` — monitors managed processes, restarts on failure,
    tracks restart counts, and escalates after repeated crashes.
  * ``TaskScheduler`` — runs async tasks on fixed intervals or at
    specific times, with jitter and concurrency control.
  * ``CronJob`` / ``CronTab`` — cron-style scheduling with expression
    parsing, next-run computation, and async dispatch.
  * ``HarnessRuntime`` — top-level integration that wires the three
    subsystems together and exposes a single ``start`` / ``stop`` API.

Usage::

    runtime = HarnessRuntime()
    runtime.watchdog.register("worker", target=worker_fn, restart=True)
    runtime.cron_tab.add(CronJob(name="heartbeat", schedule="*/5 * * * *", task=heartbeat_fn))
    await runtime.start()
"""
from __future__ import annotations

from .watchdog import Watchdog, WatchdogConfig, ProcessHandle, ProcessStatus
from .scheduler import TaskScheduler, ScheduledTask, TaskPriority
from .cron import CronJob, CronTab, CronExpression, CronField
from .harness import HarnessRuntime, HarnessRuntimeConfig

__version__ = "1.0.0"

__all__ = [
    # Watchdog
    "Watchdog",
    "WatchdogConfig",
    "ProcessHandle",
    "ProcessStatus",
    # Scheduler
    "TaskScheduler",
    "ScheduledTask",
    "TaskPriority",
    # Cron
    "CronJob",
    "CronTab",
    "CronExpression",
    "CronField",
    # Harness
    "HarnessRuntime",
    "HarnessRuntimeConfig",
]
