"""Tests for hermes_asi_master.runtime.cron."""
from __future__ import annotations

import asyncio
import pytest

from hermes_asi_master.runtime.cron import (
    CronExpression,
    CronField,
    CronJob,
    CronTab,
    CronJobStatus,
    CronRunRecord,
)


class TestCronField:
    def test_star(self):
        f = CronField("*", 0, 59)
        assert 0 in f.values
        assert 59 in f.values
        assert len(f.values) == 60

    def test_specific(self):
        f = CronField("5", 0, 59)
        assert f.values == {5}

    def test_range(self):
        f = CronField("1-5", 0, 59)
        assert f.values == {1, 2, 3, 4, 5}

    def test_step(self):
        f = CronField("*/15", 0, 59)
        assert f.values == {0, 15, 30, 45}

    def test_list(self):
        f = CronField("1,3,5", 0, 59)
        assert f.values == {1, 3, 5}

    def test_complex(self):
        f = CronField("1-3,5", 0, 59)
        assert f.values == {1, 2, 3, 5}

    def test_matches(self):
        f = CronField("5,10", 0, 59)
        assert f.matches(5)
        assert f.matches(10)
        assert not f.matches(7)

    def test_next(self):
        f = CronField("5,10,15", 0, 59)
        assert f.next(3) == 5
        assert f.next(5) == 5
        assert f.next(6) == 10
        assert f.next(16) is None

    def test_first(self):
        f = CronField("5,10,15", 0, 59)
        assert f.first() == 5


class TestCronExpression:
    def test_create_5_fields(self):
        c = CronExpression("*/5 * * * *")
        assert c.minute.values == {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}
        assert len(c.hour.values) == 24
        assert len(c.day_of_month.values) == 31
        assert len(c.month.values) == 12
        assert len(c.day_of_week.values) == 7

    def test_create_6_fields(self):
        c = CronExpression("0 0 * * * 2025")
        assert c.year.values == {2025}

    def test_create_too_few_fields(self):
        with pytest.raises(ValueError, match="at least 5 fields"):
            CronExpression("* * * *")

    def test_matches(self):
        c = CronExpression("0 12 * * *")
        from datetime import datetime, timezone
        dt = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert c.matches(dt)

    def test_not_matches(self):
        c = CronExpression("0 12 * * *")
        from datetime import datetime, timezone
        dt = datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc)
        assert not c.matches(dt)

    def test_next_run(self):
        c = CronExpression("0 12 * * *")
        from datetime import datetime, timezone
        dt = datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc)
        nxt = c.next_run(dt)
        assert nxt is not None
        assert nxt.hour == 12
        assert nxt.minute == 0

    def test_next_run_specific_dow(self):
        c = CronExpression("0 0 * * 1")  # Monday
        from datetime import datetime, timezone
        dt = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)  # Wednesday
        nxt = c.next_run(dt)
        assert nxt is not None
        # Next Monday
        assert (nxt.weekday() + 1) % 7 == 1


class TestCronJobStatus:
    def test_values(self):
        assert CronJobStatus.IDLE.value == "idle"
        assert CronJobStatus.RUNNING.value == "running"
        assert CronJobStatus.PAUSED.value == "paused"
        assert CronJobStatus.DISABLED.value == "disabled"
        assert CronJobStatus.ERROR.value == "error"


class TestCronRunRecord:
    def test_create(self):
        r = CronRunRecord(run_id="r1", scheduled_at=1.0, started_at=1.0)
        assert r.run_id == "r1"
        assert r.finished_at is None


class TestCronJob:
    def test_create(self):
        async def task():
            pass

        j = CronJob(name="test", schedule="*/5 * * * *", task=task)
        assert j.name == "test"
        assert j.schedule == "*/5 * * * *"
        assert j.status == CronJobStatus.IDLE
        assert j.next_run_at is not None

    def test_create_invalid_schedule(self):
        async def task():
            pass

        with pytest.raises(ValueError):
            CronJob(name="test", schedule="* * *", task=task)


class TestCronTab:
    def test_add(self):
        ct = CronTab()

        async def task():
            pass

        j = CronJob(name="test", schedule="*/5 * * * *", task=task)
        ct.add(j)
        assert "test" in ct.jobs

    def test_add_duplicate(self):
        ct = CronTab()

        async def task():
            pass

        j = CronJob(name="test", schedule="*/5 * * * *", task=task)
        ct.add(j)
        with pytest.raises(ValueError, match="already exists"):
            ct.add(j)

    def test_remove(self):
        ct = CronTab()

        async def task():
            pass

        j = CronJob(name="test", schedule="*/5 * * * *", task=task)
        ct.add(j)
        removed = ct.remove("test")
        assert removed is not None
        assert "test" not in ct.jobs

    def test_pause_resume(self):
        ct = CronTab()

        async def task():
            pass

        j = CronJob(name="test", schedule="*/5 * * * *", task=task)
        ct.add(j)
        ct.pause("test")
        assert j.status == CronJobStatus.PAUSED
        ct.resume("test")
        assert j.status == CronJobStatus.IDLE

    def test_enable_disable(self):
        ct = CronTab()

        async def task():
            pass

        j = CronJob(name="test", schedule="*/5 * * * *", task=task)
        ct.add(j)
        ct.disable("test")
        assert j.status == CronJobStatus.DISABLED
        ct.enable("test")
        assert j.status == CronJobStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_stop(self):
        ct = CronTab(check_interval=0.1)

        async def task():
            pass

        j = CronJob(name="test", schedule="*/5 * * * *", task=task)
        ct.add(j)
        await ct.start()
        assert ct.running
        await ct.stop()
        assert not ct.running

    @pytest.mark.asyncio
    async def test_job_execution(self):
        ct = CronTab(check_interval=0.05)
        counter = 0

        async def task():
            nonlocal counter
            counter += 1

        # Use a schedule that runs every minute, but we'll trigger manually
        # by setting next_run_at to the past
        j = CronJob(name="test", schedule="*/1 * * * *", task=task)
        j.next_run_at = 0  # Force immediate execution
        ct.add(j)
        await ct.start()
        await asyncio.sleep(0.3)
        await ct.stop()
        assert counter >= 1

    @pytest.mark.asyncio
    async def test_job_error(self):
        ct = CronTab(check_interval=0.05)

        async def task():
            raise RuntimeError("boom")

        j = CronJob(name="test", schedule="*/1 * * * *", task=task)
        j.next_run_at = 0
        ct.add(j)
        await ct.start()
        await asyncio.sleep(0.3)
        await ct.stop()
        assert j.status == CronJobStatus.ERROR
        assert "boom" in (j.last_error or "")

    def test_status(self):
        ct = CronTab()

        async def task():
            pass

        j = CronJob(name="test", schedule="*/5 * * * *", task=task)
        ct.add(j)
        s = ct.status()
        assert s["running"] is False
        assert s["total"] == 1
        assert "test" in s["jobs"]
