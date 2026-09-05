"""Tests for HellaSwag Benchmark."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from benchmark.hellaswag_benchmark import HellaSwagBenchmark, ProblemStatus


class TestHellaSwagBenchmark:
    def test_create(self):
        bench = HellaSwagBenchmark()
        assert bench.count() == 0

    def test_load_default(self):
        bench = HellaSwagBenchmark()
        count = bench.load_problems()
        assert count == 10000

    def test_load_custom(self):
        bench = HellaSwagBenchmark()
        custom = [{"id": "C1", "context": "ctx", "endings": ["a", "b"], "correct_index": 0}]
        assert bench.load_problems(custom) == 1

    def test_run_problem(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        result = bench.run_problem("HellaSwag_1", predicted_index=1)
        assert result.status in (ProblemStatus.PASSED, ProblemStatus.FAILED)

    def test_run_problem_correct(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HellaSwag_1")
        result = bench.run_problem("HellaSwag_1", predicted_index=problem.correct_index)
        assert result.status == ProblemStatus.PASSED
        assert result.correct is True

    def test_run_problem_wrong(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HellaSwag_1")
        wrong = (problem.correct_index + 1) % 4
        result = bench.run_problem("HellaSwag_1", predicted_index=wrong)
        assert result.status == ProblemStatus.FAILED
        assert result.correct is False

    def test_run_problem_not_found(self):
        bench = HellaSwagBenchmark()
        result = bench.run_problem("nonexistent")
        assert result.status == ProblemStatus.ERROR

    def test_set_prediction(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        bench.set_prediction("HellaSwag_1", 0)
        result = bench.run_problem("HellaSwag_1")
        assert result.predicted_index == 0

    def test_run_all(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        results = bench.run_all()
        assert len(results) == 10000

    def test_get_pass_rate(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        bench.run_all()
        rate = bench.get_pass_rate()
        assert rate["total"] == 10000

    def test_get_pass_rate_empty(self):
        bench = HellaSwagBenchmark()
        rate = bench.get_pass_rate()
        assert rate["total"] == 0

    def test_get_result(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        bench.run_problem("HellaSwag_1", predicted_index=0)
        result = bench.get_result("HellaSwag_1")
        assert result is not None

    def test_clear_results(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        bench.run_all()
        bench.clear_results()
        assert bench.get_pass_rate()["total"] == 0

    def test_count(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        assert bench.count() == 10000

    def test_problem_metadata(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HellaSwag_1")
        assert "difficulty" in problem.metadata
        assert "category" in problem.metadata

    def test_problem_has_context(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HellaSwag_1")
        assert len(problem.context) > 0

    def test_problem_has_endings(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HellaSwag_1")
        assert len(problem.endings) == 4

    def test_list_problems(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        assert len(bench.list_problems()) == 10000

    def test_result_duration(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        result = bench.run_problem("HellaSwag_1", predicted_index=0)
        assert result.duration_ms >= 0

    def test_full_pipeline(self):
        bench = HellaSwagBenchmark()
        assert bench.load_problems() == 10000
        results = bench.run_all()
        assert len(results) == 10000
        rate = bench.get_pass_rate()
        assert rate["total"] == 10000

    def test_multiple_problems(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        for i in range(1, 11):
            bench.run_problem(f"HellaSwag_{i}", predicted_index=0)
        rate = bench.get_pass_rate()
        assert rate["total"] == 10

    def test_different_difficulties(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        easy = bench.get_problem("HellaSwag_1")
        medium = bench.get_problem("HellaSwag_3000")
        hard = bench.get_problem("HellaSwag_7000")
        assert easy.metadata["difficulty"] == "easy"
        assert medium.metadata["difficulty"] == "medium"
        assert hard.metadata["difficulty"] == "hard"

    def test_categories(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        categories = set()
        for pid in bench.list_problems()[:20]:
            problem = bench.get_problem(pid)
            categories.add(problem.metadata["category"])
        assert len(categories) > 0

    def test_correct_index_bounds(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        for pid in bench.list_problems()[:100]:
            problem = bench.get_problem(pid)
            assert 0 <= problem.correct_index < 4

    def test_pass_rate_after_clear(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        bench.run_all()
        assert bench.get_pass_rate()["total"] == 10000
        bench.clear_results()
        assert bench.get_pass_rate()["total"] == 0

    def test_problem_status(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HellaSwag_1")
        assert problem.status == ProblemStatus.PENDING

    def test_result_predicted_index(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        result = bench.run_problem("HellaSwag_1", predicted_index=2)
        assert result.predicted_index == 2

    def test_prediction_override(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        bench.set_prediction("HellaSwag_1", 0)
        result = bench.run_problem("HellaSwag_1", predicted_index=3)
        assert result.predicted_index == 3

    def test_multiple_runs(self):
        bench = HellaSwagBenchmark()
        bench.load_problems()
        for _ in range(3):
            result = bench.run_problem("HellaSwag_1", predicted_index=0)
            assert result.status in (ProblemStatus.PASSED, ProblemStatus.FAILED)
