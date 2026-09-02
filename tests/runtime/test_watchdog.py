"""Tests for hermes_asi_master.runtime.watchdog."""
from __future__ import annotations

import asyncio
import pytest

from hermes_asi_master.runtime.watchdog import (
    Watchdog,
    WatchdogConfig,
    ProcessHandle,
    ProcessStatus,
    RestartRecord,
)


class TestProcessStatus:
    def test_values(self):
        assert ProcessStatus.PENDING.value == "pending"
        assert ProcessStatus.RUNNING.value == "running"
        assert ProcessStatus.RESTARTING.value == "restarting"
        assert ProcessStatus.STOPPED.value == "stopped"
        assert ProcessStatus.FAILED.value == "failed"


class TestRestartRecord:
    def test_create(self):
        r = RestartRecord(timestamp=1.0, exit_code=1, reason="test")
        assert r.timestamp == 1.0
        assert r.exit_code == 1
        assert r.reason == "test"


class TestProcessHandle:
    def test_create(self):
        h = ProcessHandle(name="test")
        assert h.name == "test"
        assert h.status == ProcessStatus.PENDING
        assert h.restart_count == 0
        assert h.uptime_seconds == 0.0

    def test_uptime(self):
        import time
        now = time.time()
        h = ProcessHandle(name="test", started_at=now - 10)
        assert 9.0 < h.uptime_seconds < 11.0


class TestWatchdogConfig:
    def test_defaults(self):
        c = WatchdogConfig()
        assert c.check_interval == 1.0
        assert c.max_restarts == 5
        assert c.restart_window_seconds == 60.0
        assert c.restart_delay == 1.0
        assert c.backoff_factor == 2.0
        assert c.max_restart_delay == 60.0


class TestWatchdog:
    def test_register(self):
        wd = Watchdog()

        async def target():
            await asyncio.sleep(10)

        h = wd.register("test", target=target)
        assert h.name == "test"
        assert "test" in wd.processes

    def test_register_duplicate(self):
        wd = Watchdog()

        async def target():
            await asyncio.sleep(10)

        wd.register("test", target=target)
        with pytest.raises(ValueError, match="already registered"):
            wd.register("test", target=target)

    def test_unregister(self):
        wd = Watchdog()

        async def target():
            await asyncio.sleep(10)

        wd.register("test", target=target)
        h = wd.unregister("test")
        assert h is not None
        assert "test" not in wd.processes

    def test_unregister_unknown(self):
        wd = Watchdog()
        assert wd.unregister("unknown") is None

    @pytest.mark.asyncio
    async def test_start_stop(self):
        wd = Watchdog()

        async def target():
            await asyncio.sleep(10)

        wd.register("test", target=target)
        await wd.start()
        assert wd.running
        assert wd.get("test").status == ProcessStatus.RUNNING
        await wd.stop()
        assert not wd.running

    @pytest.mark.asyncio
    async def test_process_restart(self):
        wd = Watchdog(
            config=WatchdogConfig(
                check_interval=0.1,
                restart_delay=0.1,
                max_restarts=3,
                restart_window_seconds=10.0,
            )
        )

        counter = 0

        async def target():
            nonlocal counter
            counter += 1
            await asyncio.sleep(0.1)
            raise RuntimeError("boom")

        wd.register("test", target=target, restart=True)
        await wd.start()
        await asyncio.sleep(1.0)
        await wd.stop()
        assert counter >= 2

    @pytest.mark.asyncio
    async def test_restart_budget_exceeded(self):
        wd = Watchdog(
            config=WatchdogConfig(
                check_interval=0.1,
                restart_delay=0.01,
                max_restarts=2,
                restart_window_seconds=10.0,
                backoff_factor=1.0,
            )
        )

        async def target():
            await asyncio.sleep(0.01)
            raise RuntimeError("boom")

        wd.register("test", target=target, restart=True)
        await wd.start()
        await asyncio.sleep(1.0)
        h = wd.get("test")
        assert h.status == ProcessStatus.FAILED
        await wd.stop()

    @pytest.mark.asyncio
    async def test_no_restart(self):
        wd = Watchdog(config=WatchdogConfig(check_interval=0.1))

        async def target():
            await asyncio.sleep(0.01)
            raise RuntimeError("boom")

        wd.register("test", target=target, restart=False)
        await wd.start()
        await asyncio.sleep(0.5)
        h = wd.get("test")
        assert h.status == ProcessStatus.STOPPED
        await wd.stop()

    def test_status(self):
        wd = Watchdog()

        async def target():
            await asyncio.sleep(10)

        wd.register("test", target=target)
        s = wd.status()
        assert s["running"] is False
        assert s["total"] == 1
        assert "test" in s["processes"]
