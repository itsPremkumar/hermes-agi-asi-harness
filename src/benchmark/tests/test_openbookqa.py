"""Tests for OpenBookQA benchmark — 25 tests."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.benchmark.openbookqa_benchmark import (
    OpenBookQABenchmark,
    OpenBookProblem,
    OpenBookResult,
    ProblemStatus,
)


def test_benchmark_init():
    """Test benchmark initialization."""
    bench = OpenBookQABenchmark()
    assert bench._problems == {}
    assert bench._results == {}


def test_load_problems():
    """Test loading problems."""
    bench = OpenBookQABenchmark()
    count = bench.load_problems()
    assert count == 500


def test_load_problems_count():
    """Test that 500 problems are loaded."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    assert bench.count() == 500


def test_list_problems():
    """Test listing problems."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    problems = bench.list_problems()
    assert len(problems) == 500
    assert "OBQA_1" in problems
    assert "OBQA_500" in problems


def test_get_problem():
    """Test getting a specific problem."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    problem = bench.get_problem("OBQA_1")
    assert problem is not None
    assert problem.id == "OBQA_1"
    assert len(problem.options) == 4


def test_get_problem_not_found():
    """Test getting a non-existent problem."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    problem = bench.get_problem("NONEXISTENT")
    assert problem is None


def test_set_prediction():
    """Test setting a prediction."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    bench.set_prediction("OBQA_1", 2)
    result = bench.run_problem("OBQA_1")
    assert result.predicted_index == 2


def test_run_problem():
    """Test running a single problem."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    result = bench.run_problem("OBQA_1", predicted_index=0)
    assert isinstance(result, OpenBookResult)
    assert result.problem_id == "OBQA_1"


def test_run_problem_correct():
    """Test running a problem with correct prediction."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    problem = bench.get_problem("OBQA_1")
    correct_idx = problem.correct_index
    result = bench.run_problem("OBQA_1", predicted_index=correct_idx)
    assert result.correct is True
    assert result.status == ProblemStatus.PASSED


def test_run_problem_incorrect():
    """Test running a problem with incorrect prediction."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    problem = bench.get_problem("OBQA_1")
    wrong_idx = (problem.correct_index + 1) % 4
    result = bench.run_problem("OBQA_1", predicted_index=wrong_idx)
    assert result.correct is False
    assert result.status == ProblemStatus.FAILED


def test_run_problem_not_found():
    """Test running a non-existent problem."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    result = bench.run_problem("NONEXISTENT")
    assert result.status == ProblemStatus.ERROR


def test_run_all():
    """Test running all problems."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    results = bench.run_all()
    assert len(results) == 500


def test_get_pass_rate():
    """Test getting pass rate."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    bench.run_all()
    rate = bench.get_pass_rate()
    assert rate["total"] == 500
    assert rate["passed"] + rate["failed"] == 500


def test_get_pass_rate_empty():
    """Test getting pass rate with no results."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    rate = bench.get_pass_rate()
    assert rate["total"] == 0
    assert rate["pass_rate"] == 0.0


def test_get_result():
    """Test getting a specific result."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    bench.run_problem("OBQA_1", predicted_index=0)
    result = bench.get_result("OBQA_1")
    assert result is not None
    assert result.problem_id == "OBQA_1"


def test_get_result_not_found():
    """Test getting a non-existent result."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    result = bench.get_result("NONEXISTENT")
    assert result is None


def test_clear_results():
    """Test clearing results."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    bench.run_all()
    assert len(bench._results) == 500
    bench.clear_results()
    assert len(bench._results) == 0


def test_problem_status_enum():
    """Test ProblemStatus enum values."""
    assert ProblemStatus.PENDING.value == "pending"
    assert ProblemStatus.PASSED.value == "passed"
    assert ProblemStatus.FAILED.value == "failed"
    assert ProblemStatus.ERROR.value == "error"


def test_open_book_problem_dataclass():
    """Test OpenBookProblem dataclass."""
    problem = OpenBookProblem(
        id="test_001",
        question="What is 2+2?",
        options=["3", "4", "5", "6"],
        correct_index=1,
    )
    assert problem.id == "test_001"
    assert problem.correct_index == 1
    assert problem.status == ProblemStatus.PENDING


def test_open_book_result_dataclass():
    """Test OpenBookResult dataclass."""
    result = OpenBookResult(
        problem_id="test_001",
        status=ProblemStatus.PASSED,
        predicted_index=1,
        correct=True,
        duration_ms=5.0,
    )
    assert result.problem_id == "test_001"
    assert result.correct is True
    assert result.duration_ms == 5.0


def test_prediction_with_set_prediction():
    """Test prediction set via set_prediction method."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    bench.set_prediction("OBQA_1", 3)
    result = bench.run_problem("OBQA_1")
    assert result.predicted_index == 3


def test_run_problem_duration():
    """Test that run_problem records duration."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    result = bench.run_problem("OBQA_1", predicted_index=0)
    assert result.duration_ms >= 0.0


def test_multiple_runs():
    """Test running multiple problems."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    for i in range(1, 11):
        bench.run_problem(f"OBQA_{i}", predicted_index=0)
    assert len(bench._results) == 10


def test_pass_rate_calculation():
    """Test pass rate calculation."""
    bench = OpenBookQABenchmark()
    bench.load_problems()
    # Run first 10 problems with correct answers
    for i in range(1, 11):
        problem = bench.get_problem(f"OBQA_{i}")
        bench.run_problem(f"OBQA_{i}", predicted_index=problem.correct_index)
    rate = bench.get_pass_rate()
    assert rate["passed"] == 10
    assert rate["pass_rate"] == 1.0


def test_benchmark_thread_safety():
    """Test that benchmark has thread lock."""
    bench = OpenBookQABenchmark()
    assert hasattr(bench, '_lock')
