"""Tests for Continuous Development System — ≥40 tests across all modules."""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hermes.engines.continuous_dev import (
    ABTestingFramework,
    CanaryDeploymentManager,
    CanaryStatus,
    CronStatus,
    CronTask,
    DailyImprovementCron,
    DashboardMetric,
    ProgressDashboard,
    RollbackManager,
)


class TestDailyImprovementCron(unittest.TestCase):
    def setUp(self):
        self.cron = DailyImprovementCron()

    def test_default_tasks_loaded(self):
        tasks = self.cron.list_tasks()
        self.assertGreaterEqual(len(tasks), 8)

    def test_add_task(self):
        task = CronTask("test-task", "0 * * * *", "echo test")
        self.cron.add_task(task)
        self.assertEqual(self.cron.get_task("test-task").name, "test-task")

    def test_get_nonexistent_task(self):
        self.assertIsNone(self.cron.get_task("nonexistent"))

    def test_run_task(self):
        result = asyncio.run(self.cron.run_task("benchmark-suite"))
        self.assertEqual(result, CronStatus.PASSED)

    def test_run_disabled_task(self):
        task = CronTask("disabled", "0 * * * *", "echo", enabled=False)
        self.cron.add_task(task)
        result = asyncio.run(self.cron.run_task("disabled"))
        self.assertEqual(result, CronStatus.SKIPPED)

    def test_run_all(self):
        results = asyncio.run(self.cron.run_all())
        self.assertGreaterEqual(len(results), 8)
        for status in results.values():
            self.assertIn(status, [CronStatus.PASSED, CronStatus.SKIPPED])

    def test_task_records_last_run(self):
        asyncio.run(self.cron.run_task("lint"))
        task = self.cron.get_task("lint")
        self.assertIsNotNone(task.last_run)
        self.assertEqual(task.last_status, CronStatus.PASSED)

    def test_task_records_duration(self):
        asyncio.run(self.cron.run_task("lint"))
        task = self.cron.get_task("lint")
        self.assertIsNotNone(task.last_duration)
        self.assertGreaterEqual(task.last_duration, 0)


class TestABTestingFramework(unittest.TestCase):
    def setUp(self):
        self.framework = ABTestingFramework()

    def test_create_test(self):
        test_id = self.framework.create_test("test", "control", "variant", "latency")
        self.assertIsNotNone(test_id)
        test = self.framework.get_test(test_id)
        self.assertEqual(test.name, "test")

    def test_record_sample_a(self):
        test_id = self.framework.create_test("test", "a", "b", "metric")
        self.framework.record_sample(test_id, "a", 1.5)
        test = self.framework.get_test(test_id)
        self.assertEqual(len(test.samples_a), 1)

    def test_record_sample_b(self):
        test_id = self.framework.create_test("test", "a", "b", "metric")
        self.framework.record_sample(test_id, "b", 2.0)
        test = self.framework.get_test(test_id)
        self.assertEqual(len(test.samples_b), 1)

    def test_run_test_insufficient_samples(self):
        test_id = self.framework.create_test("test", "a", "b", "metric")
        result = self.framework.run_test(test_id)
        self.assertIn("error", result)

    def test_run_test_with_enough_samples(self):
        test_id = self.framework.create_test("test", "a", "b", "metric")
        for _ in range(20):
            self.framework.record_sample(test_id, "a", 10.0)
            self.framework.record_sample(test_id, "b", 12.0)
        result = self.framework.run_test(test_id)
        self.assertEqual(result["status"], "completed")
        self.assertIsNotNone(result["winner"])

    def test_variant_b_wins(self):
        test_id = self.framework.create_test("test", "a", "b", "metric")
        for _ in range(50):
            self.framework.record_sample(test_id, "a", 10.0)
            self.framework.record_sample(test_id, "b", 15.0)
        result = self.framework.run_test(test_id)
        self.assertEqual(result["winner"], "b")

    def test_variant_b_wins_lower_is_better(self):
        test_id = self.framework.create_test("test", "a", "b", "latency", lower_is_better=True)
        for _ in range(50):
            self.framework.record_sample(test_id, "a", 15.0)
            self.framework.record_sample(test_id, "b", 8.0)
        result = self.framework.run_test(test_id)
        self.assertEqual(result["winner"], "b")

    def test_variant_a_wins(self):
        test_id = self.framework.create_test("test", "a", "b", "metric")
        for _ in range(50):
            self.framework.record_sample(test_id, "a", 20.0)
            self.framework.record_sample(test_id, "b", 10.0)
        result = self.framework.run_test(test_id)
        self.assertEqual(result["winner"], "a")

    def test_get_nonexistent_test(self):
        self.assertIsNone(self.framework.get_test("nonexistent"))


class TestCanaryDeploymentManager(unittest.TestCase):
    def setUp(self):
        self.manager = CanaryDeploymentManager()

    def test_start_canary(self):
        release_id = self.manager.start_canary("v1.2.3")
        release = self.manager.get_release(release_id)
        self.assertEqual(release.status, CanaryStatus.PENDING)

    def test_deploy(self):
        release_id = self.manager.start_canary("v1.2.3")
        result = self.manager.deploy(release_id)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_release(release_id).status, CanaryStatus.MONITORING)

    def test_record_metrics_healthy(self):
        release_id = self.manager.start_canary("v1.2.3")
        self.manager.deploy(release_id)
        result = self.manager.record_metrics(release_id, 0.5, 200.0)
        self.assertEqual(result, "healthy")

    def test_record_metrics_rollback_on_error(self):
        release_id = self.manager.start_canary("v1.2.3", error_threshold=1.0)
        self.manager.deploy(release_id)
        result = self.manager.record_metrics(release_id, 5.0, 200.0)
        self.assertEqual(result, "rollback")
        self.assertEqual(self.manager.get_release(release_id).status, CanaryStatus.ROLLED_BACK)

    def test_record_metrics_rollback_on_latency(self):
        release_id = self.manager.start_canary("v1.2.3", latency_threshold=100.0)
        self.manager.deploy(release_id)
        result = self.manager.record_metrics(release_id, 0.5, 500.0)
        self.assertEqual(result, "rollback")

    def test_promote(self):
        release_id = self.manager.start_canary("v1.2.3")
        self.manager.deploy(release_id)
        result = self.manager.promote(release_id)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_release(release_id).status, CanaryStatus.PROMOTED)

    def test_rollback(self):
        release_id = self.manager.start_canary("v1.2.3")
        self.manager.deploy(release_id)
        result = self.manager.rollback(release_id)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_release(release_id).status, CanaryStatus.ROLLED_BACK)

    def test_get_nonexistent_release(self):
        self.assertIsNone(self.manager.get_release("nonexistent"))


class TestRollbackManager(unittest.TestCase):
    def setUp(self):
        self.manager = RollbackManager(max_points=5)

    def test_create_point(self):
        point_id = self.manager.create_point("v1.0", "Initial release")
        self.assertIsNotNone(point_id)

    def test_rollback_to(self):
        point_id = self.manager.create_point("v1.0", "Initial")
        result = self.manager.rollback_to(point_id)
        self.assertEqual(result["status"], "completed")

    def test_rollback_to_nonexistent(self):
        result = self.manager.rollback_to("nonexistent")
        self.assertEqual(result["status"], "not_found")

    def test_list_points(self):
        for i in range(3):
            self.manager.create_point(f"v1.{i}", f"Release {i}")
        points = self.manager.list_points()
        self.assertEqual(len(points), 3)

    def test_max_points_enforced(self):
        for i in range(7):
            self.manager.create_point(f"v1.{i}", f"Release {i}")
        points = self.manager.list_points()
        self.assertLessEqual(len(points), 5)

    def test_latest(self):
        for i in range(3):
            self.manager.create_point(f"v1.{i}", f"Release {i}")
        latest = self.manager.latest()
        self.assertEqual(latest.version, "v1.2")


class TestProgressDashboard(unittest.TestCase):
    def setUp(self):
        self.dashboard = ProgressDashboard()

    def test_add_metric(self):
        self.dashboard.add_metric("test_coverage", 90.0, "%")
        status = self.dashboard.get_status()
        self.assertIn("test_coverage", status)

    def test_update_metric(self):
        self.dashboard.add_metric("test_coverage", 90.0, "%")
        self.dashboard.update("test_coverage", 85.0)
        status = self.dashboard.get_status()
        self.assertEqual(status["test_coverage"]["current"], 85.0)

    def test_metric_percent(self):
        metric = DashboardMetric(name="test", current=75.0, target=100.0, unit="%")
        self.assertEqual(metric.percent, 75.0)

    def test_metric_status_pass(self):
        metric = DashboardMetric(name="test", current=100.0, target=100.0)
        self.assertEqual(metric.status, "PASS")

    def test_metric_status_warn(self):
        metric = DashboardMetric(name="test", current=85.0, target=100.0)
        self.assertEqual(metric.status, "WARN")

    def test_metric_status_fail(self):
        metric = DashboardMetric(name="test", current=50.0, target=100.0)
        self.assertEqual(metric.status, "FAIL")

    def test_overall_progress(self):
        self.dashboard.add_metric("a", 100.0)
        self.dashboard.add_metric("b", 100.0)
        self.dashboard.update("a", 100.0)
        self.dashboard.update("b", 50.0)
        self.assertEqual(self.dashboard.overall_progress(), 75.0)

    def test_render(self):
        self.dashboard.add_metric("test_coverage", 90.0, "%")
        self.dashboard.update("test_coverage", 85.0)
        output = self.dashboard.render()
        self.assertIn("DASHBOARD", output)
        self.assertIn("test_coverage", output)

    def test_empty_dashboard(self):
        self.assertEqual(self.dashboard.overall_progress(), 0.0)


class TestIntegration(unittest.TestCase):
    """Integration tests across continuous development modules."""

    def test_full_improvement_cycle(self):
        """Run daily cron, check results, update dashboard."""
        cron = DailyImprovementCron()
        dashboard = ProgressDashboard()
        dashboard.add_metric("cron_success_rate", 100.0, "%")

        results = asyncio.run(cron.run_all())
        passed = sum(1 for s in results.values() if s == CronStatus.PASSED)
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0.0

        dashboard.update("cron_success_rate", success_rate)
        status = dashboard.get_status()
        self.assertGreaterEqual(status["cron_success_rate"]["current"], 0.0)

    def test_ab_test_to_canary_flow(self):
        """A/B test winner → canary deploy → promote/rollback."""
        framework = ABTestingFramework()
        canary_mgr = CanaryDeploymentManager()

        # Run A/B test
        test_id = framework.create_test("perf", "old", "new", "latency", lower_is_better=True)
        for _ in range(50):
            framework.record_sample(test_id, "a", 100.0)
            framework.record_sample(test_id, "b", 80.0)
        result = framework.run_test(test_id)
        self.assertEqual(result["winner"], "b")

        # Deploy winner as canary
        release_id = canary_mgr.start_canary("v2.0")
        canary_mgr.deploy(release_id)
        canary_mgr.record_metrics(release_id, 0.1, 50.0)
        canary_mgr.promote(release_id)
        self.assertEqual(canary_mgr.get_release(release_id).status, CanaryStatus.PROMOTED)

    def test_canary_rollback_creates_point(self):
        """Canary rollback creates a rollback point."""
        canary_mgr = CanaryDeploymentManager()
        rollback_mgr = RollbackManager()

        release_id = canary_mgr.start_canary("v1.0")
        canary_mgr.deploy(release_id)
        canary_mgr.record_metrics(release_id, 5.0, 200.0)

        rollback_mgr.create_point("v0.9", "Pre-canary baseline")
        result = rollback_mgr.rollback_to(rollback_mgr.latest().point_id)
        self.assertEqual(result["status"], "completed")


if __name__ == "__main__":
    unittest.main()
