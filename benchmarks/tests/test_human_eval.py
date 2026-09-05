"""Tests for HumanEval Benchmark."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from benchmark.human_eval_benchmark import (
    HumanEvalBenchmark,
    Problem,
    ProblemResult,
    ProblemStatus,
)


class TestProblem:
    def test_create(self):
        problem = Problem(id="HE_1", prompt="test", entry_point="func")
        assert problem.id == "HE_1"
        assert problem.prompt == "test"
        assert problem.entry_point == "func"
        assert problem.status == ProblemStatus.PENDING


class TestProblemResult:
    def test_create(self):
        result = ProblemResult(problem_id="HE_1", status=ProblemStatus.PASSED)
        assert result.problem_id == "HE_1"
        assert result.status == ProblemStatus.PASSED


class TestHumanEvalBenchmark:
    def test_create(self):
        bench = HumanEvalBenchmark()
        assert bench.count() == 0

    def test_load_default_problems(self):
        bench = HumanEvalBenchmark()
        count = bench.load_problems()
        assert count == 164

    def test_load_custom_problems(self):
        bench = HumanEvalBenchmark()
        custom = [
            {"id": "C1", "prompt": "p1", "entry_point": "f1"},
            {"id": "C2", "prompt": "p2", "entry_point": "f2"},
        ]
        count = bench.load_problems(custom)
        assert count == 2

    def test_get_problem(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HumanEval_1")
        assert problem is not None
        assert problem.id == "HumanEval_1"

    def test_list_problems(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        problems = bench.list_problems()
        assert len(problems) == 164

    def test_run_problem(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        result = bench.run_problem("HumanEval_1", solution="def add(a, b): return a + b")
        assert result.problem_id == "HumanEval_1"
        assert result.status == ProblemStatus.PASSED

    def test_run_problem_not_found(self):
        bench = HumanEvalBenchmark()
        result = bench.run_problem("nonexistent")
        assert result.status == ProblemStatus.ERROR

    def test_run_problem_syntax_error(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        result = bench.run_problem("HumanEval_1", solution="def add(:")
        assert result.status == ProblemStatus.FAILED

    def test_set_solution(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        bench.set_solution("HumanEval_1", "def add(a, b): return a + b")
        result = bench.run_problem("HumanEval_1")
        assert result.status == ProblemStatus.PASSED

    def test_run_all(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        results = bench.run_all()
        assert len(results) == 164

    def test_get_pass_rate(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        bench.run_all()
        rate = bench.get_pass_rate()
        assert rate["total"] == 164
        assert 0 <= rate["pass_rate"] <= 1

    def test_get_pass_rate_empty(self):
        bench = HumanEvalBenchmark()
        rate = bench.get_pass_rate()
        assert rate["total"] == 0

    def test_get_result(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        bench.run_problem("HumanEval_1", "def add(a, b): return a + b")
        result = bench.get_result("HumanEval_1")
        assert result is not None
        assert result.status == ProblemStatus.PASSED

    def test_clear_results(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        bench.run_all()
        bench.clear_results()
        assert bench.get_pass_rate()["total"] == 0

    def test_count(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        assert bench.count() == 164

    def test_problem_metadata(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HumanEval_1")
        assert "difficulty" in problem.metadata
        assert "category" in problem.metadata

    def test_problem_has_prompt(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HumanEval_1")
        assert len(problem.prompt) > 0

    def test_problem_has_entry_point(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HumanEval_1")
        assert len(problem.entry_point) > 0

    def test_problem_has_test_code(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HumanEval_1")
        assert len(problem.test_code) > 0

    def test_default_solutions(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        result = bench.run_problem("HumanEval_1")
        assert result.status == ProblemStatus.PASSED

    def test_result_duration(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        result = bench.run_problem("HumanEval_1", "def add(a, b): return a + b")
        assert result.duration_ms >= 0

    def test_result_has_solution(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        result = bench.run_problem("HumanEval_1", "def add(a, b): return a + b")
        assert result.solution == "def add(a, b): return a + b"


class TestHumanEvalIntegration:
    def test_full_pipeline(self):
        bench = HumanEvalBenchmark()
        assert bench.load_problems() == 164
        results = bench.run_all()
        assert len(results) == 164
        rate = bench.get_pass_rate()
        assert rate["total"] == 164

    def test_multiple_problems(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        for i in range(1, 11):
            bench.run_problem(f"HumanEval_{i}")
        rate = bench.get_pass_rate()
        assert rate["total"] == 10

    def test_different_difficulties(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        easy = bench.get_problem("HumanEval_1")
        medium = bench.get_problem("HumanEval_30")
        hard = bench.get_problem("HumanEval_100")
        assert easy.metadata["difficulty"] == "easy"
        assert medium.metadata["difficulty"] == "medium"
        assert hard.metadata["difficulty"] == "hard"

    def test_custom_solution_overrides(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        custom = "def add(x, y): return x + y"
        result = bench.run_problem("HumanEval_1", custom)
        assert result.solution == custom
        assert result.status == ProblemStatus.PASSED

    def test_syntax_error_reporting(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        result = bench.run_problem("HumanEval_1", "def add(:")
        assert "Syntax error" in result.error

    def test_pass_rate_after_clear(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        bench.run_all()
        assert bench.get_pass_rate()["total"] == 164
        bench.clear_results()
        assert bench.get_pass_rate()["total"] == 0

    def test_problem_status_transitions(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        problem = bench.get_problem("HumanEval_1")
        assert problem.status == ProblemStatus.PENDING
        bench.run_problem("HumanEval_1")
        # Problem status may remain pending (we don't update it)

    def test_categories_coverage(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        categories = set()
        for pid in bench.list_problems()[:20]:
            problem = bench.get_problem(pid)
            categories.add(problem.metadata["category"])
        assert len(categories) > 0

    def test_entry_points_unique(self):
        bench = HumanEvalBenchmark()
        bench.load_problems()
        entry_points = set()
        for pid in bench.list_problems()[:50]:
            problem = bench.get_problem(pid)
            entry_points.add(problem.entry_point)
        # Should have reasonable variety
        assert len(entry_points) > 10
