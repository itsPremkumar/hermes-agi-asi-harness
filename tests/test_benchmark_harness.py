"""Tests for core.benchmark.harness (BenchmarkRunner + ScoringFunction)."""

from __future__ import annotations

from hermes.core.benchmark.harness import BenchmarkRunner, ScoringFunction


class TestScoringFunction:
    def test_truthy_scores_one(self):
        assert ScoringFunction()(True) == 1.0
        assert ScoringFunction()(5) == 1.0
        assert ScoringFunction()("x") == 1.0

    def test_falsy_scores_zero(self):
        assert ScoringFunction()(False) == 0.0
        assert ScoringFunction()(0) == 0.0
        assert ScoringFunction()("") == 0.0
        assert ScoringFunction()(None) == 0.0


class TestBenchmarkRunner:
    def test_all_pass_summary(self):
        runner = BenchmarkRunner(ScoringFunction())
        scores = runner.run(
            [
                {"name": "a", "fn": lambda: True},
                {"name": "b", "fn": lambda: 42},
            ],
            n_runs=1,
        )
        assert [s.name for s in scores] == ["a", "b"]
        assert all(s.passed for s in scores)
        summary = runner.summary()
        assert summary["total_tasks"] == 2
        assert summary["passed_tasks"] == 2
        assert summary["failed_tasks"] == 0
        assert summary["mean_score"] == 1.0
        assert summary["pass_rate"] == 1.0
        assert summary["measured"] is True

    def test_failure_and_exception_recorded_not_raised(self):
        def boom():
            raise RuntimeError("kaput")

        runner = BenchmarkRunner(ScoringFunction())
        scores = runner.run(
            [
                {"name": "ok", "fn": lambda: True},
                {"name": "bad", "fn": lambda: False},
                {"name": "crash", "fn": boom},
            ]
        )
        by_name = {s.name: s for s in scores}
        assert by_name["ok"].passed is True
        assert by_name["bad"].passed is False
        assert by_name["crash"].passed is False
        assert "RuntimeError" in by_name["crash"].error
        summary = runner.summary()
        assert summary["passed_tasks"] == 1
        assert summary["failed_tasks"] == 2
        assert summary["measured"] is True

    def test_n_runs_repeats_and_averages(self):
        calls = []

        def fn():
            calls.append(1)
            return True

        runner = BenchmarkRunner(ScoringFunction())
        scores = runner.run([{"name": "rep", "fn": fn}], n_runs=3)
        assert len(calls) == 3
        assert scores[0].runs == 3
        assert scores[0].passed is True
        assert scores[0].score == 1.0

    def test_empty_run_is_unmeasured(self):
        runner = BenchmarkRunner(ScoringFunction())
        assert runner.run([]) == []
        summary = runner.summary()
        assert summary["total_tasks"] == 0
        assert summary["measured"] is False
        assert summary["mean_score"] == 0.0

    def test_custom_scorer_below_threshold_fails(self):
        runner = BenchmarkRunner(scoring_fn=lambda v: 0.5)
        scores = runner.run([{"name": "half", "fn": lambda: "anything"}])
        assert scores[0].score == 0.5
        assert scores[0].passed is False
        assert runner.summary()["mean_score"] == 0.5
