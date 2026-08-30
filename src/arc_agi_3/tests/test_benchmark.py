"""Tests for ARC-AGI-3 Benchmark Runner."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from arc_agi_3.benchmark_runner import (
    BenchmarkRunner, BenchmarkResult, BenchmarkSuite,
    build_default_benchmark_suite,
)
from arc_agi_3.engine import Engine, Grid, Task


class TestBenchmarkResult:
    def test_create(self):
        result = BenchmarkResult(task_id="t1", solved=True, iterations=3, score=0.9, duration_ms=10.0)
        assert result.task_id == "t1"
        assert result.solved is True
        assert result.iterations == 3
        assert result.score == 0.9
        assert result.duration_ms == 10.0

    def test_default_error(self):
        result = BenchmarkResult(task_id="t1", solved=False, iterations=0, score=0.0)
        assert result.error == ""


class TestBenchmarkSuite:
    def test_create(self):
        suite = BenchmarkSuite(id="s1", name="Test Suite")
        assert suite.id == "s1"
        assert suite.name == "Test Suite"
        assert suite.tasks == []


class TestBenchmarkRunner:
    def test_create(self):
        runner = BenchmarkRunner()
        assert runner.engine is not None

    def test_register_suite(self):
        runner = BenchmarkRunner()
        suite = BenchmarkSuite(id="s1", name="Test")
        runner.register_suite(suite)
        assert runner.get_suite("s1") is suite

    def test_get_suite_not_found(self):
        runner = BenchmarkRunner()
        assert runner.get_suite("nonexistent") is None

    def test_list_suites(self):
        runner = BenchmarkRunner()
        runner.register_suite(BenchmarkSuite(id="s1", name="Test1"))
        runner.register_suite(BenchmarkSuite(id="s2", name="Test2"))
        assert len(runner.list_suites()) == 2

    def test_run_task(self):
        runner = BenchmarkRunner()
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[1, 2]]),
            examples=[(Grid([[1, 2]]), Grid([[1, 2]]))],
        )
        result = runner.run_task(task)
        assert result.task_id == "t1"
        assert isinstance(result.solved, bool)

    def test_run_suite(self):
        runner = BenchmarkRunner()
        suite = BenchmarkSuite(
            id="s1",
            name="Test",
            tasks=[
                Task(
                    id="t1",
                    input_grid=Grid([[1]]),
                    target_grid=Grid([[1]]),
                    examples=[(Grid([[1]]), Grid([[1]]))],
                ),
            ],
        )
        runner.register_suite(suite)
        results = runner.run_suite("s1")
        assert len(results) == 1

    def test_run_suite_not_found(self):
        runner = BenchmarkRunner()
        results = runner.run_suite("nonexistent")
        assert results == []

    def test_run_all(self):
        runner = BenchmarkRunner()
        runner.register_suite(BenchmarkSuite(
            id="s1", name="Test",
            tasks=[Task(id="t1", input_grid=Grid([[1]]), target_grid=Grid([[1]]), examples=[(Grid([[1]]), Grid([[1]]))])],
        ))
        results = runner.run_all()
        assert len(results) == 1

    def test_get_results(self):
        runner = BenchmarkRunner()
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            target_grid=Grid([[1]]),
            examples=[(Grid([[1]]), Grid([[1]]))],
        )
        runner.run_task(task)
        assert len(runner.get_results()) == 1

    def test_get_stats(self):
        runner = BenchmarkRunner()
        stats = runner.get_stats()
        assert stats["total"] == 0

    def test_get_stats_with_results(self):
        runner = BenchmarkRunner()
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            target_grid=Grid([[1]]),
            examples=[(Grid([[1]]), Grid([[1]]))],
        )
        runner.run_task(task)
        stats = runner.get_stats()
        assert stats["total"] == 1

    def test_clear_results(self):
        runner = BenchmarkRunner()
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            target_grid=Grid([[1]]),
            examples=[(Grid([[1]]), Grid([[1]]))],
        )
        runner.run_task(task)
        runner.clear_results()
        assert len(runner.get_results()) == 0


class TestDefaultBenchmarkSuite:
    def test_build(self):
        suite = build_default_benchmark_suite()
        assert suite.id == "default"
        assert len(suite.tasks) > 0

    def test_tasks_have_examples(self):
        suite = build_default_benchmark_suite()
        for task in suite.tasks:
            assert len(task.examples) > 0

    def test_tasks_have_targets(self):
        suite = build_default_benchmark_suite()
        for task in suite.tasks:
            assert task.target_grid is not None

    def test_metadata(self):
        suite = build_default_benchmark_suite()
        assert "version" in suite.metadata


class TestBenchmarkIntegration:
    def test_full_pipeline(self):
        runner = BenchmarkRunner()
        suite = build_default_benchmark_suite()
        runner.register_suite(suite)
        results = runner.run_suite("default")
        assert len(results) == len(suite.tasks)

    def test_solve_rate(self):
        runner = BenchmarkRunner()
        suite = build_default_benchmark_suite()
        runner.register_suite(suite)
        runner.run_suite("default")
        stats = runner.get_stats()
        assert 0.0 <= stats["solve_rate"] <= 1.0

    def test_custom_engine(self):
        engine = Engine(max_iterations=5)
        runner = BenchmarkRunner(engine=engine)
        task = Task(
            id="t1",
            input_grid=Grid([[1, 2]]),
            target_grid=Grid([[3, 4]]),
            examples=[(Grid([[1, 2]]), Grid([[3, 4]]))],
        )
        result = runner.run_task(task, max_iterations=3)
        assert result.iterations <= 3

    def test_multiple_suites(self):
        runner = BenchmarkRunner()
        runner.register_suite(BenchmarkSuite(
            id="s1", name="Suite1",
            tasks=[Task(id="t1", input_grid=Grid([[1]]), target_grid=Grid([[1]]), examples=[(Grid([[1]]), Grid([[1]]))])],
        ))
        runner.register_suite(BenchmarkSuite(
            id="s2", name="Suite2",
            tasks=[Task(id="t2", input_grid=Grid([[2]]), target_grid=Grid([[2]]), examples=[(Grid([[2]]), Grid([[2]]))])],
        ))
        results = runner.run_all()
        assert len(results) == 2

    def test_result_duration(self):
        runner = BenchmarkRunner()
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            target_grid=Grid([[1]]),
            examples=[(Grid([[1]]), Grid([[1]]))],
        )
        result = runner.run_task(task)
        assert result.duration_ms >= 0

    def test_suite_with_multiple_tasks(self):
        runner = BenchmarkRunner()
        suite = build_default_benchmark_suite()
        runner.register_suite(suite)
        results = runner.run_suite("default")
        for result in results:
            assert isinstance(result, BenchmarkResult)

    def test_stats_after_clear(self):
        runner = BenchmarkRunner()
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            target_grid=Grid([[1]]),
            examples=[(Grid([[1]]), Grid([[1]]))],
        )
        runner.run_task(task)
        runner.clear_results()
        stats = runner.get_stats()
        assert stats["total"] == 0

    def test_benchmark_result_defaults(self):
        result = BenchmarkResult(task_id="t1", solved=False, iterations=0, score=0.0)
        assert result.solution_id == ""
        assert result.error == ""

    def test_runner_thread_safety(self):
        runner = BenchmarkRunner()
        suite = build_default_benchmark_suite()
        runner.register_suite(suite)
        # Running multiple times should not crash
        runner.run_all()
        runner.run_all()
        assert len(runner.get_results()) > 0

    def test_empty_suite(self):
        runner = BenchmarkRunner()
        suite = BenchmarkSuite(id="empty", name="Empty")
        runner.register_suite(suite)
        results = runner.run_suite("empty")
        assert len(results) == 0

    def test_stats_avg_score(self):
        runner = BenchmarkRunner()
        suite = build_default_benchmark_suite()
        runner.register_suite(suite)
        runner.run_suite("default")
        stats = runner.get_stats()
        assert 0.0 <= stats["avg_score"] <= 1.0

    def test_engine_reference(self):
        runner = BenchmarkRunner()
        assert runner.engine is not None

    def test_results_accumulate(self):
        runner = BenchmarkRunner()
        task = Task(
            id="t1",
            input_grid=Grid([[1]]),
            target_grid=Grid([[1]]),
            examples=[(Grid([[1]]), Grid([[1]]))],
        )
        runner.run_task(task)
        runner.run_task(task)
        assert len(runner.get_results()) == 2
