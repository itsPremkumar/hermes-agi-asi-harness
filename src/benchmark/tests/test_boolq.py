"""Tests for BoolQ Benchmark."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from benchmark.boolq_benchmark import BoolQBenchmark, BoolQProblem, BoolQResult, ProblemStatus


class TestBoolQBenchmark:
    def test_create(self):
        bench = BoolQBenchmark()
        assert bench.count() == 0

    def test_load_default(self):
        bench = BoolQBenchmark()
        count = bench.load_problems()
        assert count == 1000

    def test_load_custom(self):
        bench = BoolQBenchmark()
        custom = [{"id": "C1", "question": "q", "passage": "p", "answer": True}]
        assert bench.load_problems(custom) == 1

    def test_run_problem(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        result = bench.run_problem("BoolQ_1", predicted=True)
        assert result.status in (ProblemStatus.PASSED, ProblemStatus.FAILED)

    def test_run_problem_correct(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        problem = bench.get_problem("BoolQ_1")
        result = bench.run_problem("BoolQ_1", predicted=problem.answer)
        assert result.status == ProblemStatus.PASSED
        assert result.correct is True

    def test_run_problem_wrong(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        problem = bench.get_problem("BoolQ_1")
        result = bench.run_problem("BoolQ_1", predicted=not problem.answer)
        assert result.status == ProblemStatus.FAILED
        assert result.correct is False

    def test_run_problem_not_found(self):
        bench = BoolQBenchmark()
        result = bench.run_problem("nonexistent")
        assert result.status == ProblemStatus.ERROR

    def test_set_prediction(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        bench.set_prediction("BoolQ_1", True)
        result = bench.run_problem("BoolQ_1")
        assert result.predicted is True

    def test_run_all(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        results = bench.run_all()
        assert len(results) == 1000

    def test_get_pass_rate(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        bench.run_all()
        rate = bench.get_pass_rate()
        assert rate["total"] == 1000

    def test_get_pass_rate_empty(self):
        bench = BoolQBenchmark()
        rate = bench.get_pass_rate()
        assert rate["total"] == 0

    def test_get_result(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        bench.run_problem("BoolQ_1", predicted=True)
        result = bench.get_result("BoolQ_1")
        assert result is not None

    def test_clear_results(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        bench.run_all()
        bench.clear_results()
        assert bench.get_pass_rate()["total"] == 0

    def test_count(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        assert bench.count() == 1000

    def test_problem_metadata(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        problem = bench.get_problem("BoolQ_1")
        assert "difficulty" in problem.metadata

    def test_problem_has_question(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        problem = bench.get_problem("BoolQ_1")
        assert len(problem.question) > 0

    def test_problem_has_passage(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        problem = bench.get_problem("BoolQ_1")
        assert len(problem.passage) > 0

    def test_list_problems(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        assert len(bench.list_problems()) == 1000

    def test_result_duration(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        result = bench.run_problem("BoolQ_1", predicted=True)
        assert result.duration_ms >= 0

    def test_full_pipeline(self):
        bench = BoolQBenchmark()
        assert bench.load_problems() == 1000
        results = bench.run_all()
        assert len(results) == 1000
        rate = bench.get_pass_rate()
        assert rate["total"] == 1000

    def test_multiple_problems(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        for i in range(1, 11):
            bench.run_problem(f"BoolQ_{i}", predicted=True)
        rate = bench.get_pass_rate()
        assert rate["total"] == 10

    def test_different_difficulties(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        easy = bench.get_problem("BoolQ_1")
        medium = bench.get_problem("BoolQ_400")
        hard = bench.get_problem("BoolQ_800")
        assert easy.metadata["difficulty"] == "easy"
        assert medium.metadata["difficulty"] == "medium"
        assert hard.metadata["difficulty"] == "hard"

    def test_answer_types(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        for pid in bench.list_problems()[:100]:
            problem = bench.get_problem(pid)
            assert isinstance(problem.answer, bool)

    def test_pass_rate_after_clear(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        bench.run_all()
        assert bench.get_pass_rate()["total"] == 1000
        bench.clear_results()
        assert bench.get_pass_rate()["total"] == 0

    def test_problem_status(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        problem = bench.get_problem("BoolQ_1")
        assert problem.status == ProblemStatus.PENDING

    def test_result_predicted(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        result = bench.run_problem("BoolQ_1", predicted=False)
        assert result.predicted is False

    def test_prediction_override(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        bench.set_prediction("BoolQ_1", True)
        result = bench.run_problem("BoolQ_1", predicted=False)
        assert result.predicted is False

    def test_multiple_runs(self):
        bench = BoolQBenchmark()
        bench.load_problems()
        for _ in range(3):
            result = bench.run_problem("BoolQ_1", predicted=True)
            assert result.status in (ProblemStatus.PASSED, ProblemStatus.FAILED)
