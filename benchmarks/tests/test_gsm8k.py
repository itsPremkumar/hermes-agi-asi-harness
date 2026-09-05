"""Tests for gsm8k_benchmark.py — GSM8K Benchmark."""

from src.benchmark.gsm8k_benchmark import (
    GSM8KBenchmark,
    GSM8KQuestion,
    GSM8KResult,
)


class TestGSM8KBenchmark:
    def test_create(self):
        b = GSM8KBenchmark(data_dir="/tmp/nonexistent")
        assert b.get_stats()["total_questions"] == 0

    def test_add_question(self):
        b = GSM8KBenchmark(data_dir="/tmp/nonexistent")
        b.add_question(GSM8KQuestion(question_id="q1", question="What is 5+3?", answer=8.0))
        assert b.get_stats()["total_questions"] == 1

    def test_evaluate_correct(self):
        b = GSM8KBenchmark(data_dir="/tmp/nonexistent")
        b.add_question(GSM8KQuestion(question_id="q1", question="Q", answer=8.0))
        assert b.evaluate("q1", 8.0) is True

    def test_evaluate_incorrect(self):
        b = GSM8KBenchmark(data_dir="/tmp/nonexistent")
        b.add_question(GSM8KQuestion(question_id="q1", question="Q", answer=8.0))
        assert b.evaluate("q1", 999.0) is False

    def test_evaluate_missing(self):
        b = GSM8KBenchmark(data_dir="/tmp/nonexistent")
        assert b.evaluate("nonexistent", 0.0) is False

    def test_generate_synthetic(self):
        b = GSM8KBenchmark(data_dir="/tmp/nonexistent")
        questions = b.generate_synthetic_questions(10)
        assert len(questions) == 10
        assert b.get_stats()["total_questions"] == 10

    def test_run_benchmark(self):
        b = GSM8KBenchmark(data_dir="/tmp/nonexistent")
        b.generate_synthetic_questions(10)
        result = b.run_benchmark()
        assert result["total"] == 10

    def test_run_benchmark_with_limit(self):
        b = GSM8KBenchmark(data_dir="/tmp/nonexistent")
        b.generate_synthetic_questions(10)
        result = b.run_benchmark(num_questions=5)
        assert result["total"] == 5

    def test_get_stats(self):
        b = GSM8KBenchmark(data_dir="/tmp/nonexistent")
        b.add_question(GSM8KQuestion(question_id="q1", question="Q", answer=42.0))
        assert b.get_stats()["total_questions"] == 1

    def test_save_results(self, tmp_path):
        b = GSM8KBenchmark(data_dir="/tmp/nonexistent")
        b.generate_synthetic_questions(5)
        result = b.run_benchmark()
        out = tmp_path / "results.json"
        b.save_results(result, str(out))
        assert out.exists()

    def test_gsm8k_question(self):
        q = GSM8KQuestion(question_id="q1", question="What is 2+2?", answer=4.0)
        assert q.question_id == "q1"
        assert q.answer == 4.0

    def test_gsm8k_result(self):
        r = GSM8KResult(question_id="q1", correct=True, predicted=4.0, expected=4.0)
        assert r.correct is True
