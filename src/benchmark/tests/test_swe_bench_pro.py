"""Tests for SWE-bench Pro."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from benchmark.swe_bench_pro_benchmark import SWEBenchPro, SWETask, SWEResult, TaskStatus


class TestSWEBenchPro:
    def test_create(self):
        bench = SWEBenchPro()
        assert bench.count() == 0

    def test_load_problems(self):
        bench = SWEBenchPro()
        count = bench.load_problems()
        assert count == 5

    def test_get_task(self):
        bench = SWEBenchPro()
        bench.load_problems()
        task = bench.get_task("swe_pro_1")
        assert task is not None
        assert task.id == "swe_pro_1"

    def test_get_task_not_found(self):
        bench = SWEBenchPro()
        assert bench.get_task("nonexistent") is None

    def test_list_tasks(self):
        bench = SWEBenchPro()
        bench.load_problems()
        tasks = bench.list_tasks()
        assert len(tasks) == 5

    def test_run_problem(self):
        bench = SWEBenchPro()
        bench.load_problems()
        result = bench.run_problem("swe_pro_1")
        assert result.task_id == "swe_pro_1"
        assert result.status == TaskStatus.RESOLVED

    def test_run_problem_not_found(self):
        bench = SWEBenchPro()
        result = bench.run_problem("nonexistent")
        assert result.status == TaskStatus.ERROR

    def test_run_sample(self):
        bench = SWEBenchPro()
        bench.load_problems()
        results = bench.run_sample(3)
        assert len(results) == 3

    def test_run_sample_default(self):
        bench = SWEBenchPro()
        bench.load_problems()
        results = bench.run_sample()
        assert len(results) == 5

    def test_get_resolution_rate(self):
        bench = SWEBenchPro()
        bench.load_problems()
        bench.run_problem("swe_pro_1")
        rate = bench.get_resolution_rate()
        assert rate["total"] == 1
        assert rate["resolved"] == 1
        assert rate["resolution_rate"] == 1.0

    def test_get_resolution_rate_empty(self):
        bench = SWEBenchPro()
        rate = bench.get_resolution_rate()
        assert rate["total"] == 0

    def test_get_report(self):
        bench = SWEBenchPro()
        bench.load_problems()
        bench.run_problem("swe_pro_1")
        report = bench.get_report()
        assert report["total_tasks"] == 5
        assert report["total_runs"] == 1
        assert len(report["results"]) == 1

    def test_get_report_by_difficulty(self):
        bench = SWEBenchPro()
        bench.load_problems()
        report = bench.get_report()
        assert "hard" in report["by_difficulty"]
        assert "extra_hard" in report["by_difficulty"]

    def test_get_report_by_status(self):
        bench = SWEBenchPro()
        bench.load_problems()
        bench.run_problem("swe_pro_1")
        report = bench.get_report()
        assert "resolved" in report["by_status"]
        assert "pending" in report["by_status"]

    def test_get_result(self):
        bench = SWEBenchPro()
        bench.load_problems()
        bench.run_problem("swe_pro_1")
        result = bench.get_result("swe_pro_1")
        assert result is not None
        assert result.status == TaskStatus.RESOLVED

    def test_clear_results(self):
        bench = SWEBenchPro()
        bench.load_problems()
        bench.run_problem("swe_pro_1")
        bench.clear_results()
        assert bench.get_resolution_rate()["total"] == 0

    def test_count(self):
        bench = SWEBenchPro()
        bench.load_problems()
        assert bench.count() == 5

    def test_task_metadata(self):
        bench = SWEBenchPro()
        bench.load_problems()
        task = bench.get_task("swe_pro_1")
        assert task.repo == "django/django"
        assert task.difficulty == "hard"

    def test_result_duration(self):
        bench = SWEBenchPro()
        bench.load_problems()
        result = bench.run_problem("swe_pro_1")
        assert result.duration_ms >= 0

    def test_full_pipeline(self):
        bench = SWEBenchPro()
        assert bench.load_problems() == 5
        results = bench.run_sample(3)
        assert len(results) == 3
        rate = bench.get_resolution_rate()
        assert rate["total"] == 3
        report = bench.get_report()
        assert report["total_runs"] == 3

    def test_multiple_runs(self):
        bench = SWEBenchPro()
        bench.load_problems()
        for _ in range(3):
            result = bench.run_problem("swe_pro_1")
            assert result.status == TaskStatus.RESOLVED

    def test_resolution_rate_after_clear(self):
        bench = SWEBenchPro()
        bench.load_problems()
        bench.run_problem("swe_pro_1")
        assert bench.get_resolution_rate()["total"] == 1
        bench.clear_results()
        assert bench.get_resolution_rate()["total"] == 0

    def test_task_status_transitions(self):
        bench = SWEBenchPro()
        bench.load_problems()
        task = bench.get_task("swe_pro_1")
        assert task.status == TaskStatus.PENDING
        bench.run_problem("swe_pro_1")
        assert task.status == TaskStatus.RESOLVED

    def test_result_patch_applied(self):
        bench = SWEBenchPro()
        bench.load_problems()
        result = bench.run_problem("swe_pro_1")
        assert result.patch_applied is True

    def test_result_tests_passed(self):
        bench = SWEBenchPro()
        bench.load_problems()
        result = bench.run_problem("swe_pro_1")
        assert result.tests_passed == 5

    def test_report_results_format(self):
        bench = SWEBenchPro()
        bench.load_problems()
        bench.run_problem("swe_pro_1")
        report = bench.get_report()
        result = report["results"][0]
        assert "task_id" in result
        assert "status" in result
        assert "patch_applied" in result
        assert "tests_passed" in result
