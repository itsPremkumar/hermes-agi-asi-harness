"""Tests for hermes_asi_master.runtime.harness."""
from __future__ import annotations

import asyncio

import pytest

pytest.importorskip(
    "hermes_asi_master.runtime.harness",
    reason="hermes_asi_master runtime retired in 26c4285, salvaged into "
    "src/hermes_os (cron_expr, process_guard, watchdog); "
    "see tests/test_new_subsystems.py",
)

from hermes_asi_master.runtime.cron import CronJob
from hermes_asi_master.runtime.harness import (
    HarnessRuntime,
    HarnessRuntimeConfig,
)
from hermes_asi_master.runtime.scheduler import ScheduledTask
from hermes_asi_master.runtime.watchdog import WatchdogConfig


class TestHarnessRuntimeConfig:
    def test_defaults(self):
        c = HarnessRuntimeConfig()
        assert isinstance(c.watchdog, WatchdogConfig)
        assert c.scheduler_check_interval == 0.5
        assert c.cron_check_interval == 1.0
        assert c.health_check_interval == 30.0


class TestHarnessRuntime:
    def test_create(self):
        r = HarnessRuntime()
        assert not r.running
        assert r.uptime_seconds == 0.0

    @pytest.mark.asyncio
    async def test_start_stop(self):
        r = HarnessRuntime()
        await r.start()
        assert r.running
        await asyncio.sleep(0.1)
        assert r.uptime_seconds > 0
        await r.stop()
        assert not r.running

    @pytest.mark.asyncio
    async def test_subsystems_accessible(self):
        r = HarnessRuntime()
        assert r.watchdog is not None
        assert r.scheduler is not None
        assert r.cron_tab is not None

    @pytest.mark.asyncio
    async def test_register_watchdog_process(self):
        r = HarnessRuntime()

        async def target():
            await asyncio.sleep(10)

        r.watchdog.register("test", target=target)
        await r.start()
        assert r.watchdog.get("test").status.value == "running"
        await r.stop()

    @pytest.mark.asyncio
    async def test_add_scheduled_task(self):
        r = HarnessRuntime()

        async def task():
            pass

        r.scheduler.add(ScheduledTask(name="t", fn=task, interval_seconds=10.0))
        await r.start()
        assert "t" in r.scheduler.tasks
        await r.stop()

    @pytest.mark.asyncio
    async def test_add_cron_job(self):
        r = HarnessRuntime()

        async def task():
            pass

        r.cron_tab.add(CronJob(name="j", schedule="*/5 * * * *", task=task))
        await r.start()
        assert "j" in r.cron_tab.jobs
        await r.stop()

    def test_status(self):
        r = HarnessRuntime()
        s = r.status()
        assert s["running"] is False
        assert "watchdog" in s
        assert "scheduler" in s
        assert "cron" in s

    def test_health(self):
        r = HarnessRuntime()
        h = r.health()
        assert h["healthy"] is True
        assert h["failed_processes"] == []
        assert h["error_tasks"] == 0
        assert h["error_cron_jobs"] == 0

    @pytest.mark.asyncio
    async def test_health_with_failed_process(self):
        r = HarnessRuntime(
            config=HarnessRuntimeConfig(
                watchdog=WatchdogConfig(
                    check_interval=0.1,
                    restart_delay=0.01,
                    max_restarts=1,
                    restart_window_seconds=10.0,
                    backoff_factor=1.0,
                )
            )
        )

        async def target():
            await asyncio.sleep(0.01)
            raise RuntimeError("boom")

        r.watchdog.register("test", target=target, restart=True)
        await r.start()
        await asyncio.sleep(0.5)
        h = r.health()
        assert h["healthy"] is False
        assert len(h["failed_processes"]) >= 1
        await r.stop()
