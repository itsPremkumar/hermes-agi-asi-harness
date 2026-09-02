"""Tests for openbookqa_benchmark.py — OpenBookQA Benchmark."""
import pytest

from src.benchmark.openbookqa_benchmark import (
    OpenBookQABenchmark, OpenBookProblem, OpenBookResult, ProblemStatus,
)


class TestOpenBookQABenchmark:
    def test_create(self):
        b = OpenBookQABenchmark()
        assert b.count() == 0

    def test_load_problems(self):
        b = OpenBookQABenchmark()
        count = b.load_problems()
        assert count == 500
        assert b.count() == 500

    def test_run_problem(self):
        b = OpenBookQABenchmark()
        b.load_problems()
        r = b.run_problem("OBQA_1", 0)
        assert r.status in (ProblemStatus.PASSED, ProblemStatus.FAILED)

    def test_run_problem_correct(self):
        b = OpenBookQABenchmark()
        b.load_problems()
        # OBQA_1 has correct_index = 1 % 4 = 1
        r = b.run_problem("OBQA_1", 1)
        assert r.correct is True

    def test_run_problem_incorrect(self):
        b = OpenBookQABenchmark()
        b.load_problems()
        r = b.run_problem("OBQA_1", 0)
        assert r.correct is False

    def test_run_problem_missing(self):
        b = OpenBookQABenchmark()
        r = b.run_problem("nonexistent", 0)
        assert r.status == ProblemStatus.ERROR

    def test_run_all(self):
        b = OpenBookQABenchmark()
        b.load_problems()
        results = b.run_all()
        assert len(results) == 500

    def test_get_pass_rate(self):
        b = OpenBookQABenchmark()
        b.load_problems()
        b.run_problem("OBQA_1", 1)  # correct
        b.run_problem("OBQA_2", 0)  # wrong (correct is 2)
        pr = b.get_pass_rate()
        assert pr["pass_rate"] == 0.5

    def test_get_pass_rate_empty(self):
        b = OpenBookQABenchmark()
        pr = b.get_pass_rate()
        assert pr["pass_rate"] == 0.0

    def test_get_problem(self):
        b = OpenBookQABenchmark()
        b.load_problems()
        p = b.get_problem("OBQA_1")
        assert p is not None

    def test_list_problems(self):
        b = OpenBookQABenchmark()
        b.load_problems()
        assert len(b.list_problems()) == 500

    def test_clear_results(self):
        b = OpenBookQABenchmark()
        b.load_problems()
        b.run_problem("OBQA_1", 0)
        b.clear_results()
        assert b.get_result("OBQA_1") is None

    def test_set_prediction(self):
        b = OpenBookQABenchmark()
        b.load_problems()
        b.set_prediction("OBQA_1", 1)
        r = b.run_problem("OBQA_1")
        assert r.correct is True

    def test_openbook_problem(self):
        p = OpenBookProblem(id="test", question="q", options=["a", "b", "c", "d"], correct_index=2)
        assert p.status == ProblemStatus.PENDING

    def test_openbook_result(self):
        r = OpenBookResult(problem_id="test", status=ProblemStatus.PASSED, predicted_index=1, correct=True)
        assert r.correct is True
