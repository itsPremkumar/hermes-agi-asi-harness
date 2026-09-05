"""Tests for mmlu_benchmark.py — MMLU Benchmark."""

from src.benchmark.mmlu_benchmark import (
    MMLU_CATEGORIES,
    MMLUBenchmark,
    QuestionStatus,
)


class TestMMLUBenchmark:
    def test_create(self):
        b = MMLUBenchmark()
        assert b.load_categories() == MMLU_CATEGORIES

    def test_generate_questions(self):
        b = MMLUBenchmark()
        questions = b.generate_questions("abstract_algebra", 10)
        assert len(questions) == 10

    def test_generate_all(self):
        b = MMLUBenchmark()
        total = b.generate_all()
        assert total == len(MMLU_CATEGORIES) * 246

    def test_run_question(self):
        b = MMLUBenchmark()
        questions = b.generate_questions("abstract_algebra", 1)
        qid = questions[0].id
        assert b.run_question(qid, questions[0].correct_answer) is True

    def test_run_question_wrong(self):
        b = MMLUBenchmark()
        questions = b.generate_questions("abstract_algebra", 1)
        qid = questions[0].id
        wrong = (questions[0].correct_answer + 1) % 4
        assert b.run_question(qid, wrong) is False

    def test_run_question_missing(self):
        b = MMLUBenchmark()
        assert b.run_question("nonexistent", 0) is False

    def test_get_accuracy(self):
        b = MMLUBenchmark()
        b.generate_questions("abstract_algebra", 5)
        for q in b.load_questions("abstract_algebra"):
            b.run_question(q.id, q.correct_answer)
        assert b.get_accuracy("abstract_algebra") == 1.0

    def test_get_accuracy_empty(self):
        b = MMLUBenchmark()
        assert b.get_accuracy("abstract_algebra") == 0.0

    def test_get_overall(self):
        b = MMLUBenchmark()
        b.generate_questions("abstract_algebra", 5)
        for q in b.load_questions("abstract_algebra"):
            b.run_question(q.id, q.correct_answer)
        overall = b.get_overall()
        assert overall["correct"] == 5

    def test_get_category_results(self):
        b = MMLUBenchmark()
        b.generate_questions("abstract_algebra", 5)
        for q in b.load_questions("abstract_algebra"):
            b.run_question(q.id, q.correct_answer)
        results = b.get_category_results()
        assert len(results) > 0

    def test_load_questions(self):
        b = MMLUBenchmark()
        b.generate_questions("abstract_algebra", 10)
        questions = b.load_questions("abstract_algebra")
        assert len(questions) == 10

    def test_question_status(self):
        assert QuestionStatus.PENDING.value == "pending"
        assert QuestionStatus.CORRECT.value == "correct"
        assert QuestionStatus.INCORRECT.value == "incorrect"

    def test_load_categories(self):
        b = MMLUBenchmark()
        cats = b.load_categories()
        assert len(cats) == 57

    def test_run_questions(self):
        b = MMLUBenchmark()
        b.generate_questions("abstract_algebra", 3)
        answers = {q.id: q.correct_answer for q in b.load_questions("abstract_algebra")}
        results = b.run_questions(answers)
        assert all(results.values())
