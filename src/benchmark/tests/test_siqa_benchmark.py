"""Tests for siqa_benchmark.py — SIQA Benchmark."""
import pytest

from benchmark.siqa_benchmark import (
    SIQABenchmark, SIQAProblem, SIQAResult, ProblemStatus,
)


class TestSIQABenchmark:
    def test_create(self):
        b = SIQABenchmark()
        assert b.count() == 0

    def test_load_problems(self):
        b = SIQABenchmark()
        count = b.load_problems()
        assert count == 1000
        assert b.count() == 1000

    def test_run_problem(self):
        b = SIQABenchmark()
        b.load_problems()
        r = b.run_problem("SIQA_1", 0)
        assert r.status in (ProblemStatus.PASSED, ProblemStatus.FAILED)

    def test_run_problem_correct(self):
        b = SIQABenchmark()
        b.load_problems()
        # SIQA_1 has correct_index = 1 % 3 = 1
        r = b.run_problem("SIQA_1", 1)
        assert r.correct is True
        assert r.status == ProblemStatus.PASSED

    def test_run_problem_incorrect(self):
        b = SIQABenchmark()
        b.load_problems()
        r = b.run_problem("SIQA_1", 0)
        assert r.correct is False
        assert r.status == ProblemStatus.FAILED

    def test_run_problem_missing(self):
        b = SIQABenchmark()
        r = b.run_problem("nonexistent", 0)
        assert r.status == ProblemStatus.ERROR

    def test_run_all(self):
        b = SIQABenchmark()
        b.load_problems()
        results = b.run_all()
        assert len(results) == 1000

    def test_get_pass_rate(self):
        b = SIQABenchmark()
        b.load_problems()
        b.run_problem("SIQA_1", 1)  # correct
        b.run_problem("SIQA_2", 0)  # wrong (correct is 2)
        pr = b.get_pass_rate()
        assert pr["pass_rate"] == 0.5

    def test_get_pass_rate_empty(self):
        b = SIQABenchmark()
        pr = b.get_pass_rate()
        assert pr["pass_rate"] == 0.0

    def test_get_problem(self):
        b = SIQABenchmark()
        b.load_problems()
        p = b.get_problem("SIQA_1")
        assert p is not None
        assert p.id == "SIQA_1"

    def test_list_problems(self):
        b = SIQABenchmark()
        b.load_problems()
        problems = b.list_problems()
        assert len(problems) == 1000

    def test_get_result(self):
        b = SIQABenchmark()
        b.load_problems()
        b.run_problem("SIQA_1", 0)
        r = b.get_result("SIQA_1")
        assert r is not None

    def test_clear_results(self):
        b = SIQABenchmark()
        b.load_problems()
        b.run_problem("SIQA_1", 0)
        b.clear_results()
        assert b.get_result("SIQA_1") is None

    def test_set_prediction(self):
        b = SIQABenchmark()
        b.load_problems()
        b.set_prediction("SIQA_1", 1)
        r = b.run_problem("SIQA_1")
        assert r.correct is True

    def test_problem_status_enum(self):
        assert ProblemStatus.PENDING.value == "pending"
        assert ProblemStatus.PASSED.value == "passed"
        assert ProblemStatus.FAILED.value == "failed"
        assert ProblemStatus.ERROR.value == "error"

    def test_siqa_problem(self):
        p = SIQAProblem(id="test", context="ctx", question="q", options=["a", "b", "c"], correct_index=1)
        assert p.status == ProblemStatus.PENDING

    def test_siqa_result(self):
        r = SIQAResult(problem_id="test", status=ProblemStatus.PASSED, predicted_index=1, correct=True)
        assert r.correct is True
