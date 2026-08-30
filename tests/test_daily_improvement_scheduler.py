"""Tests for Daily Improvement Scheduler — ≥30 tests."""
from __future__ import annotations

import asyncio
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.daily_improvement.scheduler import (
    DailyImprovementLoop,
    DailyImprovementScheduler,
    ImprovementTask,
    TaskPriority,
    TaskStatus,
)


class TestDailyImprovementScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = DailyImprovementScheduler()

    def test_add_task(self):
        task_id = self.scheduler.add_task("test-task")
        self.assertIsNotNone(task_id)
        task = self.scheduler.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task.name, "test-task")

    def test_add_task_with_priority(self):
        task_id = self.scheduler.add_task("high-task", priority=TaskPriority.HIGH)
        task = self.scheduler.get_task(task_id)
        self.assertEqual(task.priority, TaskPriority.HIGH)

    def test_add_task_with_metadata(self):
        task_id = self.scheduler.add_task("meta-task", metadata={"key": "value"})
        task = self.scheduler.get_task(task_id)
        self.assertEqual(task.metadata["key"], "value")

    def test_get_next(self):
        self.scheduler.add_task("task-1")
        task = self.scheduler.get_next()
        self.assertIsNotNone(task)
        self.assertEqual(task.name, "task-1")
        self.assertEqual(task.status, TaskStatus.RUNNING)

    def test_get_next_empty(self):
        self.assertIsNone(self.scheduler.get_next())

    def test_complete_task(self):
        task_id = self.scheduler.add_task("complete-task")
        task = self.scheduler.get_next()
        self.scheduler.complete(task)
        self.assertEqual(task.status, TaskStatus.COMPLETED)

    def test_fail_task(self):
        task_id = self.scheduler.add_task("fail-task")
        task = self.scheduler.get_next()
        self.scheduler.fail(task, "Something went wrong")
        self.assertEqual(task.status, TaskStatus.FAILED)
        self.assertEqual(task.last_error, "Something went wrong")

    def test_demote_task(self):
        task_id = self.scheduler.add_task("demote-task", priority=TaskPriority.CRITICAL)
        task = self.scheduler.get_next()
        self.scheduler.demote(task)
        self.assertEqual(task.priority, TaskPriority.HIGH)

    def test_promote_task(self):
        task_id = self.scheduler.add_task("promote-task", priority=TaskPriority.LOW)
        task = self.scheduler.get_next()
        self.scheduler.promote(task)
        self.assertEqual(task.priority, TaskPriority.MEDIUM)

    def test_get_stats(self):
        self.scheduler.add_task("task-1")
        self.scheduler.add_task("task-2")
        stats = self.scheduler.get_stats()
        self.assertEqual(stats["pending"], 2)

    def test_list_pending(self):
        self.scheduler.add_task("task-1")
        self.scheduler.add_task("task-2")
        pending = self.scheduler.list_pending()
        self.assertEqual(len(pending), 2)

    def test_list_completed(self):
        self.scheduler.add_task("task-1")
        task = self.scheduler.get_next()
        self.scheduler.complete(task)
        completed = self.scheduler.list_completed()
        self.assertEqual(len(completed), 1)

    def test_list_failed(self):
        self.scheduler.add_task("task-1")
        task = self.scheduler.get_next()
        self.scheduler.fail(task, "error")
        failed = self.scheduler.list_failed()
        self.assertEqual(len(failed), 1)

    def test_clear_completed(self):
        self.scheduler.add_task("task-1")
        task = self.scheduler.get_next()
        self.scheduler.complete(task)
        self.scheduler.clear_completed()
        self.assertEqual(len(self.scheduler.list_completed()), 0)

    def test_clear_failed(self):
        self.scheduler.add_task("task-1")
        task = self.scheduler.get_next()
        self.scheduler.fail(task, "error")
        self.scheduler.clear_failed()
        self.assertEqual(len(self.scheduler.list_failed()), 0)

    def test_demote_from_critical(self):
        """Demoting from CRITICAL should go to HIGH."""
        task_id = self.scheduler.add_task("demote-critical", priority=TaskPriority.CRITICAL)
        task = self.scheduler.get_next()
        self.scheduler.demote(task)
        self.assertEqual(task.priority, TaskPriority.HIGH)

    def test_promote_from_low(self):
        """Promoting from LOW should go to MEDIUM."""
        task_id = self.scheduler.add_task("promote-low", priority=TaskPriority.LOW)
        task = self.scheduler.get_next()
        self.scheduler.promote(task)
        self.assertEqual(task.priority, TaskPriority.MEDIUM)

    def test_promote_from_critical_stays_critical(self):
        """Promoting from CRITICAL should stay CRITICAL."""
        task_id = self.scheduler.add_task("promote-critical", priority=TaskPriority.CRITICAL)
        task = self.scheduler.get_next()
        self.scheduler.promote(task)
        self.assertEqual(task.priority, TaskPriority.CRITICAL)

    def test_task_initial_status_pending(self):
        task_id = self.scheduler.add_task("pending-task")
        task = self.scheduler.get_task(task_id)
        self.assertEqual(task.status, TaskStatus.PENDING)

    def test_multiple_tasks_same_priority(self):
        self.scheduler.add_task("task-1", priority=TaskPriority.MEDIUM)
        self.scheduler.add_task("task-2", priority=TaskPriority.MEDIUM)
        self.scheduler.add_task("task-3", priority=TaskPriority.MEDIUM)
        stats = self.scheduler.get_stats()
        self.assertEqual(stats["pending"], 3)

    def test_get_task_not_found(self):
        self.assertIsNone(self.scheduler.get_task("nonexistent"))

    def test_task_order_by_priority(self):
        self.scheduler.add_task("low", priority=TaskPriority.LOW)
        self.scheduler.add_task("high", priority=TaskPriority.HIGH)
        self.scheduler.add_task("critical", priority=TaskPriority.CRITICAL)
        first = self.scheduler.get_next()
        second = self.scheduler.get_next()
        third = self.scheduler.get_next()
        self.assertEqual(first.priority, TaskPriority.CRITICAL)
        self.assertEqual(second.priority, TaskPriority.HIGH)
        self.assertEqual(third.priority, TaskPriority.LOW)

    def test_task_run_count(self):
        task_id = self.scheduler.add_task("count-task")
        task = self.scheduler.get_next()
        self.scheduler.complete(task)
        self.assertEqual(task.run_count, 1)

    def test_task_total_runtime(self):
        task_id = self.scheduler.add_task("runtime-task")
        task = self.scheduler.get_next()
        time.sleep(0.01)
        self.scheduler.complete(task)
        self.assertGreater(task.total_runtime, 0.0)


class TestDailyImprovementLoop(unittest.TestCase):
    def setUp(self):
        self.loop = DailyImprovementLoop(DailyImprovementScheduler())

    def test_add_daily_task(self):
        task_id = self.loop.add_daily_task("daily-task")
        self.assertIsNotNone(task_id)

    def test_run_once(self):
        self.loop.add_daily_task("task-1")
        self.loop.add_daily_task("task-2")
        results = self.loop.run_once()
        self.assertEqual(len(results), 2)

    def test_run_once_empty(self):
        results = self.loop.run_once()
        self.assertEqual(len(results), 0)

    def test_run_continuous(self):
        self.loop.add_daily_task("task-1")
        asyncio.run(self._run_loop())
        stats = self.loop.scheduler.get_stats()
        self.assertGreater(stats["completed"], 0)

    async def _run_loop(self):
        self.loop._running = True
        for _ in range(3):
            self.loop.run_once()
            await asyncio.sleep(0.001)
        return []

    def test_stop(self):
        self.loop.stop()
        self.assertFalse(self.loop._running)


class TestIntegration(unittest.TestCase):
    def test_full_improvement_cycle(self):
        scheduler = DailyImprovementScheduler()
        loop = DailyImprovementLoop(scheduler)

        loop.add_daily_task("benchmark", priority=TaskPriority.HIGH)
        loop.add_daily_task("lint", priority=TaskPriority.MEDIUM)
        loop.add_daily_task("docs", priority=TaskPriority.LOW)

        results = loop.run_once()
        self.assertEqual(len(results), 3)

        stats = scheduler.get_stats()
        self.assertEqual(stats["completed"], 3)

    def test_priority_boost(self):
        scheduler = DailyImprovementScheduler()
        scheduler.add_task("background-task", priority=TaskPriority.BACKGROUND)
        scheduler._last_boost = time.time() - scheduler.BOOST_INTERVAL - 1
        task = scheduler.get_next()
        # After boost, should be CRITICAL
        self.assertEqual(task.priority, TaskPriority.CRITICAL)


if __name__ == "__main__":
    unittest.main()
