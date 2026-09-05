"""Tests for hermes_asi_master.runtime.scheduler."""
from __future__ import annotations

import asyncio

import pytest

pytest.importorskip(
    "hermes_asi_master.runtime.scheduler",
    reason="hermes_asi_master runtime retired in 26c4285, salvaged into "
    "src/hermes_os (cron_expr, process_guard, watchdog); "
    "see tests/test_new_subsystems.py",
)

from hermes_asi_master.runtime.scheduler import (
    ScheduledTask,
    ScheduledTaskStatus,
    TaskPriority,
    TaskRunRecord,
    TaskScheduler,
)


class TestTaskPriority:
    def test_values(self):
        assert TaskPriority.LOW == 0
        assert TaskPriority.NORMAL == 5
        assert TaskPriority.HIGH == 10
        assert TaskPriority.CRITICAL == 20
        assert TaskPriority.CRITICAL > TaskPriority.NORMAL


class TestScheduledTaskStatus:
    def test_values(self):
        assert ScheduledTaskStatus.IDLE.value == "idle"
        assert ScheduledTaskStatus.RUNNING.value == "running"
        assert ScheduledTaskStatus.PAUSED.value == "paused"
        assert ScheduledTaskStatus.DISABLED.value == "disabled"
        assert ScheduledTaskStatus.ERROR.value == "error"


class TestTaskRunRecord:
    def test_create(self):
        r = TaskRunRecord(run_id="r1", started_at=1.0)
        assert r.run_id == "r1"
        assert r.started_at == 1.0
        assert r.finished_at is None
        assert r.error is None


class TestScheduledTask:
    def test_create_with_interval(self):
        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, interval_seconds=5.0)
        assert t.name == "t"
        assert t.interval_seconds == 5.0
        assert t.status == ScheduledTaskStatus.IDLE

    def test_create_with_run_at(self):
        import time
        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, run_at=time.time() + 10)
        assert t.run_at is not None

    def test_create_no_schedule_raises(self):
        async def fn():
            pass

        with pytest.raises(ValueError, match="interval_seconds or run_at"):
            ScheduledTask(name="t", fn=fn)

    def test_create_negative_interval_raises(self):
        async def fn():
            pass

        with pytest.raises(ValueError, match="positive"):
            ScheduledTask(name="t", fn=fn, interval_seconds=-1)

    def test_compute_next_run_interval(self):
        import time
        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, interval_seconds=5.0)
        now = time.time()
        nxt = t.compute_next_run(now)
        assert abs(nxt - (now + 5.0)) < 0.01

    def test_compute_next_run_with_jitter(self):
        import time
        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, interval_seconds=5.0, jitter=1.0)
        now = time.time()
        nxt = t.compute_next_run(now)
        assert now + 5.0 <= nxt <= now + 6.0


class TestTaskScheduler:
    def test_add(self):
        s = TaskScheduler()

        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, interval_seconds=5.0)
        s.add(t)
        assert "t" in s.tasks

    def test_add_duplicate(self):
        s = TaskScheduler()

        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, interval_seconds=5.0)
        s.add(t)
        with pytest.raises(ValueError, match="already exists"):
            s.add(t)

    def test_remove(self):
        s = TaskScheduler()

        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, interval_seconds=5.0)
        s.add(t)
        removed = s.remove("t")
        assert removed is not None
        assert "t" not in s.tasks

    def test_pause_resume(self):
        s = TaskScheduler()

        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, interval_seconds=5.0)
        s.add(t)
        s.pause("t")
        assert t.status == ScheduledTaskStatus.PAUSED
        s.resume("t")
        assert t.status == ScheduledTaskStatus.IDLE

    def test_enable_disable(self):
        s = TaskScheduler()

        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, interval_seconds=5.0)
        s.add(t)
        s.disable("t")
        assert t.status == ScheduledTaskStatus.DISABLED
        s.enable("t")
        assert t.status == ScheduledTaskStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_stop(self):
        s = TaskScheduler(check_interval=0.1)

        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, interval_seconds=100.0)
        s.add(t)
        await s.start()
        assert s.running
        await s.stop()
        assert not s.running

    @pytest.mark.asyncio
    async def test_task_execution(self):
        s = TaskScheduler(check_interval=0.05)
        counter = 0

        async def fn():
            nonlocal counter
            counter += 1

        t = ScheduledTask(name="t", fn=fn, interval_seconds=0.1)
        s.add(t)
        await s.start()
        await asyncio.sleep(0.5)
        await s.stop()
        assert counter >= 2

    @pytest.mark.asyncio
    async def test_task_error(self):
        s = TaskScheduler(check_interval=0.05)

        async def fn():
            raise RuntimeError("boom")

        t = ScheduledTask(name="t", fn=fn, interval_seconds=0.1)
        s.add(t)
        await s.start()
        await asyncio.sleep(0.3)
        await s.stop()
        assert t.status == ScheduledTaskStatus.ERROR
        assert "boom" in (t.last_error or "")

    @pytest.mark.asyncio
    async def test_max_runs(self):
        s = TaskScheduler(check_interval=0.05)
        counter = 0

        async def fn():
            nonlocal counter
            counter += 1

        t = ScheduledTask(name="t", fn=fn, interval_seconds=0.05, max_runs=2)
        s.add(t)
        await s.start()
        await asyncio.sleep(0.5)
        await s.stop()
        assert counter == 2
        assert t.status == ScheduledTaskStatus.DISABLED

    def test_status(self):
        s = TaskScheduler()

        async def fn():
            pass

        t = ScheduledTask(name="t", fn=fn, interval_seconds=5.0)
        s.add(t)
        st = s.status()
        assert st["running"] is False
        assert st["total"] == 1
        assert "t" in st["tasks"]
