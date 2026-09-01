"""Tests for GSM8K benchmark — 9 tests."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.benchmark.gsm8k_benchmark import (
    GSM8KQuestion,
    GSM8KResult,
    GSM8KBenchmark,
)


def test_benchmark_init():
    """Test benchmark initialization."""
    bench = GSM8KBenchmark()
    assert bench._questions == {}
    assert bench._results == {}


def test_add_question():
    """Test adding a question."""
    bench = GSM8KBenchmark()
    q = GSM8KQuestion(
        question_id="test_001",
        question="What is 2+2?",
        answer=4.0,
        steps=["Add 2 and 2"],
    )
    bench.add_question(q)
    assert bench.count() == 1


def test_run_question():
    """Test running a question."""
    bench = GSM8KBenchmark()
    q = GSM8KQuestion(
        question_id="test_001",
        question="What is 2+2?",
        answer=4.0,
    )
    bench.add_question(q)
    result = bench.run_question("test_001", 4.0)
    assert result.correct is True


def test_run_question_incorrect():
    """Test running a question with wrong answer."""
    bench = GSM8KBenchmark()
    q = GSM8KQuestion(
        question_id="test_001",
        question="What is 2+2?",
        answer=4.0,
    )
    bench.add_question(q)
    result = bench.run_question("test_001", 5.0)
    assert result.correct is False


def test_get_accuracy():
    """Test getting accuracy."""
    bench = GSM8KBenchmark()
    q1 = GSM8KQuestion(question_id="q1", question="Q1", answer=10.0)
    q2 = GSM8KQuestion(question_id="q2", question="Q2", answer=20.0)
    bench.add_question(q1)
    bench.add_question(q2)
    bench.run_question("q1", 10.0)
    bench.run_question("q2", 5.0)
    acc = bench.get_accuracy()
    assert acc == 0.5


def test_gsm8k_question_dataclass():
    """Test GSM8KQuestion dataclass."""
    q = GSM8KQuestion(
        question_id="test_001",
        question="What is 5*5?",
        answer=25.0,
        steps=["Multiply 5 by 5"],
    )
    assert q.question_id == "test_001"
    assert q.answer == 25.0
    assert len(q.steps) == 1


def test_gsm8k_result_dataclass():
    """Test GSM8KResult dataclass."""
    result = GSM8KResult(
        question_id="test_001",
        predicted=25.0,
        correct_answer=25.0,
        correct=True,
    )
    assert result.question_id == "test_001"
    assert result.correct is True


def test_run_all():
    """Test running all questions."""
    bench = GSM8KBenchmark()
    q1 = GSM8KQuestion(question_id="q1", question="Q1", answer=10.0)
    q2 = GSM8KQuestion(question_id="q2", question="Q2", answer=20.0)
    bench.add_question(q1)
    bench.add_question(q2)
    results = bench.run_all({"q1": 10.0, "q2": 20.0})
    assert len(results) == 2


def test_get_report():
    """Test getting report."""
    bench = GSM8KBenchmark()
    q1 = GSM8KQuestion(question_id="q1", question="Q1", answer=10.0)
    bench.add_question(q1)
    bench.run_question("q1", 10.0)
    report = bench.get_report()
    assert report["total"] == 1
    assert report["correct"] == 1
