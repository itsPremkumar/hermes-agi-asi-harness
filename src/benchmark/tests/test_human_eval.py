"""Tests for HumanEval benchmark."""

import pytest

from benchmark.human_eval_benchmark import (
    HumanEvalBenchmark,
    HumanEvalProblem,
    ProblemDifficulty,
    ProblemResult,
)


class TestHumanEvalProblem:
    def test_create(self):
        problem = HumanEvalProblem(
            id="test/0",
            prompt="def foo(): pass",
            test="assert True",
            entry_point="foo",
        )
        assert problem.id == "test/0"
        assert problem.difficulty == ProblemDifficulty.EASY

    def test_create_medium(self):
        problem = HumanEvalProblem(
            id="test/1",
            prompt="def bar(): pass",
            test="assert True",
            entry_point="bar",
            difficulty=ProblemDifficulty.MEDIUM,
        )
        assert problem.difficulty == ProblemDifficulty.MEDIUM


class TestHumanEvalBenchmark:
    def test_create(self):
        bench = HumanEvalBenchmark()
        assert bench is not None
        assert bench.get_problem_count() > 0

    def test_get_problem(self):
        bench = HumanEvalBenchmark()
        problem = bench.get_problem("HumanEval/0")
        assert problem is not None
        assert problem.id == "HumanEval/0"

    def test_get_all_problems(self):
        bench = HumanEvalBenchmark()
        problems = bench.get_all_problems()
        assert len(problems) >= 10

    def test_load_problems(self):
        bench = HumanEvalBenchmark()
        initial_count = bench.get_problem_count()
        new_problem = HumanEvalProblem(
            id="Custom/0",
            prompt="def test(): pass",
            test="assert True",
            entry_point="test",
        )
        bench.load_problems([new_problem])
        assert bench.get_problem_count() == initial_count + 1

    def test_run_problem_pass(self):
        bench = HumanEvalBenchmark()
        solution = "def add(a, b):\n    return a + b\n"
        result = bench.run_problem("HumanEval/0", solution)
        assert isinstance(result, ProblemResult)
        assert result.passed is True

    def test_run_problem_fail(self):
        bench = HumanEvalBenchmark()
        solution = "def add(a, b):\n    return 0\n"
        result = bench.run_problem("HumanEval/0", solution)
        assert result.passed is False

    def test_run_problem_not_found(self):
        bench = HumanEvalBenchmark()
        result = bench.run_problem("nonexistent", "pass")
        assert result.passed is False
        assert "not found" in result.error.lower()

    def test_run_all(self):
        bench = HumanEvalBenchmark()
        solutions = {
            "HumanEval/0": "def add(a, b):\n    return a + b\n",
            "HumanEval/1": "def is_even(n):\n    return n % 2 == 0\n",
        }
        results = bench.run_all(solutions)
        assert len(results) == 2

    def test_get_pass_rate(self):
        bench = HumanEvalBenchmark()
        solutions = {
            "HumanEval/0": "def add(a, b):\n    return a + b\n",
        }
        bench.run_all(solutions)
        rate = bench.get_pass_rate()
        assert 0 <= rate <= 100

    def test_get_results_summary(self):
        bench = HumanEvalBenchmark()
        summary = bench.get_results_summary()
        assert "total_problems" in summary
        assert "pass_rate" in summary

    def test_load_from_json(self, tmp_path):
        import json
        bench = HumanEvalBenchmark()
        data = [
            {
                "task_id": "JSON/0",
                "prompt": "def test(): pass",
                "test": "assert True",
                "entry_point": "test",
            }
        ]
        filepath = tmp_path / "problems.json"
        with open(filepath, "w") as f:
            json.dump(data, f)
        count = bench.load_from_json(str(filepath))
        assert count == 1

    def test_problem_count(self):
        bench = HumanEvalBenchmark()
        assert bench.get_problem_count() >= 10


class TestProblemResult:
    def test_create(self):
        result = ProblemResult(problem_id="test", passed=True)
        assert result.problem_id == "test"
        assert result.passed is True
        assert result.error == ""
