"""
HERMES INTELLIGENCE OS — CONTINUOUS SCHEDULER (24/7 CRON)
=========================================================
Lightweight interval + daily scheduler for the PersistentDaemonRuntime:
- register_interval(name, seconds, coro_fn)
- register_daily(name, hh_mm, coro_fn)  (24h local time)
- tick() executes due jobs; designed to be called from daemon on_tick.
No third-party dependency (Windows-safe).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List

logger = logging.getLogger("hermes.os.scheduler")


@dataclass
class ScheduledJob:
    name: str
    kind: str  # interval | daily | cron
    interval_seconds: float = 3600.0
    daily_hh_mm: str = "02:00"
    cron_expr: str = ""
    handler: Callable[[], Awaitable[Any]] | None = None
    last_run: float = 0.0
    run_count: int = 0

    def due(self, now: float) -> bool:
        if self.kind == "interval":
            return (now - self.last_run) >= self.interval_seconds
        if self.kind == "daily":
            try:
                hh, mm = self.daily_hh_mm.split(":")
                target = datetime.now().replace(hour=int(hh), minute=int(mm), second=0, microsecond=0).timestamp()
                # Run once per 24h window after target passes
                return now >= target and (now - self.last_run) >= 23 * 3600
            except Exception:
                return False
        if self.kind == "cron":
            try:
                from .cron_expr import CronExpression
                # Fire at most once per minute while the expression matches now
                return CronExpression(self.cron_expr).matches(datetime.now()) and (now - self.last_run) >= 60.0
            except Exception:
                return False
        return False


class ContinuousScheduler:
    """Minimal durable scheduler. Persist last_run to .hermes/scheduler.json."""

    def __init__(self, workspace_root: str = "."):
        from pathlib import Path
        import json
        self.workspace_root = workspace_root
        self._state_file = Path(workspace_root) / ".hermes" / "scheduler.json"
        self._jobs: Dict[str, ScheduledJob] = {}
        self._json = json
        self._load_state()

    def register_interval(self, name: str, seconds: float, handler: Callable[[], Awaitable[Any]]) -> None:
        self._jobs[name] = ScheduledJob(name=name, kind="interval", interval_seconds=seconds, handler=handler,
                                        last_run=self._jobs.get(name, ScheduledJob(name, "interval")).last_run)

    def register_daily(self, name: str, hh_mm: str, handler: Callable[[], Awaitable[Any]]) -> None:
        self._jobs[name] = ScheduledJob(name=name, kind="daily", daily_hh_mm=hh_mm, handler=handler,
                                        last_run=self._jobs.get(name, ScheduledJob(name, "daily")).last_run)

    def register_cron(self, name: str, expr: str, handler: Callable[[], Awaitable[Any]]) -> None:
        """Cron-syntax schedule (e.g. '0 2 * * *'). Validated eagerly; ValueError on bad syntax."""
        from .cron_expr import CronExpression
        CronExpression(expr)  # validate now, fail fast
        self._jobs[name] = ScheduledJob(name=name, kind="cron", cron_expr=expr, handler=handler,
                                        last_run=self._jobs.get(name, ScheduledJob(name, "cron")).last_run)

    def _load_state(self) -> None:
        try:
            if self._state_file.exists():
                data = self._json.loads(self._state_file.read_text(encoding="utf-8"))
                for name, last in data.get("last_run", {}).items():
                    self._jobs[name] = ScheduledJob(name=name, kind="interval", last_run=float(last))
        except Exception as e:
            logger.debug("Scheduler state load failed: %s", e)

    def _save_state(self) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {"last_run": {n: j.last_run for n, j in self._jobs.items()}}
            self._state_file.write_text(self._json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    async def tick(self) -> List[str]:
        """Run all due jobs. Returns names of jobs executed."""
        now = time.time()
        ran: List[str] = []
        for job in list(self._jobs.values()):
            if job.handler is None:
                continue
            if job.due(now):
                try:
                    if asyncio.iscoroutinefunction(job.handler):
                        await job.handler()
                    else:
                        job.handler()
                    ran.append(job.name)
                except Exception as e:
                    logger.error("Scheduled job '%s' failed: %s", job.name, e)
                job.last_run = now
                job.run_count += 1
        if ran:
            self._save_state()
        return ran

    def stats(self) -> Dict[str, Any]:
        return {n: {"kind": j.kind, "runs": j.run_count, "last_run": j.last_run} for n, j in self._jobs.items()}
