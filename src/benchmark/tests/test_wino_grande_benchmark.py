"""Tests for wino_grande_benchmark.py."""

import pytest
import json
import os
import tempfile
from benchmark.wino_grande_benchmark import (
    WinogradProblem, ProblemResult, BenchmarkResult,
    WinogradBenchmark, SAMPLE_PROBLEMS,
)


class TestWinogradProblem:
    """Tests for WinogradProblem."""

    def test_problem_fields(self):
        problem = WinogradProblem(
            problem_id="win_001",
            sentence="The city councilmen refused the demonstrators a permit because they feared violence.",
            pronoun="they",
            options=["city councilmen", "demonstrators"],
            answer=0,
        )
        assert problem.problem_id == "win_001"
        assert problem.answer == 0
        assert len(problem.options) == 2

    def test_problem_to_dict(self):
        problem = WinogradProblem(
            problem_id="win_001",
            sentence="Test sentence.",
            pronoun="it",
            options=["a", "b"],
            answer=1,
        )
        d = problem.to_dict()
        assert d["problem_id"] == "win_001"
        assert d["answer"] == 1

    def test_problem_from_dict(self):
        data = {"problem_id": "test", "sentence": "Test", "pronoun": "it", "options": ["a", "b"], "answer": 0}
        problem = WinogradProblem.from_dict(data)
        assert problem.problem_id == "test"
        assert problem.answer == 0


class TestWinogradBenchmark:
    """Tests for WinogradBenchmark."""

    def test_load_problems_default(self):
        bench = WinogradBenchmark()
        count = bench.load_problems()
        assert count == len(SAMPLE_PROBLEMS)
        assert len(bench.problems) > 0

    def test_load_problems_from_file(self):
        bench = WinogradBenchmark()
        data = [
            {"problem_id": "custom_001", "sentence": "Test.", "pronoun": "it", "options": ["a", "b"], "answer": 0},
            {"problem_id": "custom_002", "sentence": "Test 2.", "pronoun": "they", "options": ["x", "y"], "answer": 1},
        ]
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        count = bench.load_problems(path)
        assert count == 2
        os.unlink(path)

    def test_get_problem(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        problem = bench.get_problem("win_001")
        assert problem is not None
        assert problem.problem_id == "win_001"

    def test_get_problem_invalid(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        problem = bench.get_problem("invalid")
        assert problem is None

    def test_run_problem(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        problem = bench.problems[0]
        result = bench.run_problem(problem)
        assert isinstance(result, ProblemResult)
        assert result.problem_id == problem.problem_id

    def test_run_problem_with_solver(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        problem = bench.problems[0]
        solver = lambda s, p, o: 0
        result = bench.run_problem(problem, solver)
        assert isinstance(result, ProblemResult)
        assert result.predicted_answer == 0

    def test_run_sample(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        result = bench.run_sample(5, random_seed=42)
        assert isinstance(result, BenchmarkResult)
        assert result.total_problems == 5
        assert 0 <= result.accuracy <= 1

    def test_run_sample_reproducible(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        result1 = bench.run_sample(3, random_seed=42)
        bench.clear_results()
        result2 = bench.run_sample(3, random_seed=42)
        assert result1.total_problems == result2.total_problems

    def test_run_all(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        result = bench.run_all()
        assert isinstance(result, BenchmarkResult)
        assert result.total_problems == len(SAMPLE_PROBLEMS)

    def test_get_accuracy(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        bench.run_sample(5, random_seed=42)
        accuracy = bench.get_accuracy()
        assert "total_problems" in accuracy
        assert "correct" in accuracy
        assert "incorrect" in accuracy
        assert "accuracy" in accuracy
        assert accuracy["total_problems"] == 5

    def test_get_accuracy_empty(self):
        bench = WinogradBenchmark()
        accuracy = bench.get_accuracy()
        assert accuracy["total_problems"] == 0
        assert accuracy["accuracy"] == 0.0

    def test_clear_results(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        bench.run_sample(3, random_seed=42)
        assert len(bench.results) > 0
        bench.clear_results()
        assert len(bench.results) == 0

    def test_default_solver_because(self):
        bench = WinogradBenchmark()
        problem = WinogradProblem(
            problem_id="test",
            sentence="The city councilmen refused the demonstrators a permit because they feared violence.",
            pronoun="they",
            options=["city councilmen", "demonstrators"],
            answer=0,
        )
        answer, output = bench._default_solver(problem)
        assert answer == 0

    def test_default_solver_after(self):
        bench = WinogradBenchmark()
        problem = WinogradProblem(
            problem_id="test",
            sentence="Tom threw his schoolbag to Ray after he reached the bottom.",
            pronoun="he",
            options=["Tom", "Ray"],
            answer=0,
        )
        answer, output = bench._default_solver(problem)
        assert answer == 1

    def test_get_statistics(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        bench.run_sample(5, random_seed=42)
        stats = bench.get_statistics()
        assert "total" in stats
        assert "correct" in stats
        assert "accuracy" in stats

    def test_benchmark_result_to_dict(self):
        result = BenchmarkResult(
            total_problems=10,
            correct=7,
            incorrect=3,
            accuracy=0.7,
            results=[],
        )
        d = result.to_dict()
        assert d["total_problems"] == 10
        assert d["accuracy"] == 0.7

    def test_problem_result_to_dict(self):
        result = ProblemResult(
            problem_id="test",
            sentence="Test",
            pronoun="it",
            options=["a", "b"],
            correct_answer=0,
            predicted_answer=0,
            correct=True,
            output="a",
            feedback="Correct!",
        )
        d = result.to_dict()
        assert d["problem_id"] == "test"
        assert d["correct"] is True

    def test_sample_problems_valid(self):
        assert len(SAMPLE_PROBLEMS) >= 10
        for problem in SAMPLE_PROBLEMS:
            assert problem.problem_id != ""
            assert problem.sentence != ""
            assert len(problem.options) == 2
            assert problem.answer in [0, 1]

    def test_run_sample_accuracy_range(self):
        bench = WinogradBenchmark()
        bench.load_problems()
        result = bench.run_sample(10, random_seed=42)
        assert 0 <= result.accuracy <= 1
        assert result.correct + result.incorrect == result.total_problems
