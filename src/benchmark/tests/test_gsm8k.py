import pytest
import os
import tempfile
import json

from benchmark.gsm8k_benchmark import GSM8KQuestion, GSM8KResult, GSM8KLoader, GSM8KEvaluator, GSM8KBenchmark


def _create_temp_json(data):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return path


class TestGSM8KLoader:
    def test_create(self):
        loader = GSM8KLoader()
        assert len(loader.questions) == 0

    def test_load_questions(self):
        path = _create_temp_json([
            {"id": "1", "question": "Janet has 5 apples. She gives 2 away. How many left?", "answer": 3},
            {"id": "2", "question": "What is 10 * 5?", "answer": 50},
        ])
        loader = GSM8KLoader()
        questions = loader.load_questions(path)
        assert len(questions) == 2
        os.unlink(path)

    def test_load_with_steps(self):
        path = _create_temp_json([
            {"id": "1", "question": "Q", "answer": 42, "steps": ["step1", "step2"]},
        ])
        loader = GSM8KLoader()
        questions = loader.load_questions(path)
        assert len(questions[0].steps) == 2
        os.unlink(path)


class TestGSM8KEvaluator:
    def test_extract_number(self):
        ev = GSM8KEvaluator()
        assert ev.extract_number("The answer is 42") == 42
        assert ev.extract_number("Result: 3.14") == 3.14
        assert ev.extract_number("No numbers here") is None

    def test_evaluate_correct(self):
        ev = GSM8KEvaluator()
        q = GSM8KQuestion(id="1", question="Q", answer=42)
        r = ev.evaluate(q, "The answer is 42")
        assert r.correct is True
        assert r.predicted == 42

    def test_evaluate_incorrect(self):
        ev = GSM8KEvaluator()
        q = GSM8KQuestion(id="1", question="Q", answer=42)
        r = ev.evaluate(q, "The answer is 99")
        assert r.correct is False

    def test_evaluate_float(self):
        ev = GSM8KEvaluator()
        q = GSM8KQuestion(id="1", question="Q", answer=3.14)
        r = ev.evaluate(q, "The answer is 3.14")
        assert r.correct is True

    def test_evaluate_no_number(self):
        ev = GSM8KEvaluator()
        q = GSM8KQuestion(id="1", question="Q", answer=42)
        r = ev.evaluate(q, "I don't know")
        assert r.correct is False


class TestGSM8KBenchmark:
    def test_create(self):
        b = GSM8KBenchmark()
        assert len(b.results) == 0

    def test_load_and_run(self):
        path = _create_temp_json([
            {"id": "1", "question": "What is 5 + 3?", "answer": 8},
        ])
        b = GSM8KBenchmark()
        b.load_questions(path)
        r = b.run_question("1", "The answer is 8")
        assert r is not None
        assert r.correct is True
        os.unlink(path)

    def test_get_accuracy(self):
        path = _create_temp_json([
            {"id": "1", "question": "Q1", "answer": 10},
            {"id": "2", "question": "Q2", "answer": 20},
        ])
        b = GSM8KBenchmark()
        b.load_questions(path)
        b.run_question("1", "The answer is 10")
        b.run_question("2", "The answer is 999")
        acc = b.get_accuracy()
        assert acc["accuracy"] == 0.5
        assert acc["total"] == 2
        os.unlink(path)

    def test_unknown_question(self):
        b = GSM8KBenchmark()
        assert b.run_question("nonexistent", "42") is None

    def test_accuracy_no_results(self):
        b = GSM8KBenchmark()
        acc = b.get_accuracy()
        assert acc["accuracy"] == 0.0
        assert acc["total"] == 0


class TestGSM8KQuestion:
    def test_create(self):
        q = GSM8KQuestion(id="1", question="What is 2+2?", answer=4)
        assert q.question == "What is 2+2?"
        assert q.answer == 4

    def test_from_dict(self):
        d = {"id": "2", "question": "Q", "answer": 42, "steps": ["a", "b"]}
        q = GSM8KQuestion.from_dict(d)
        assert q.answer == 42
        assert len(q.steps) == 2


class TestGSM8KResult:
    def test_create(self):
        r = GSM8KResult(id="r1", question_id="q1", predicted=42, correct=True)
        assert r.correct is True
        assert r.predicted == 42


class TestGSM8KEvaluatorEdgeCases:
    def test_negative_number(self):
        ev = GSM8KEvaluator()
        q = GSM8KQuestion(id="1", question="Q", answer=-5)
        r = ev.evaluate(q, "The answer is -5")
        assert r.correct is True

    def test_decimal_tolerance(self):
        ev = GSM8KEvaluator(tolerance=0.01)
        q = GSM8KQuestion(id="1", question="Q", answer=1.005)
        r = ev.evaluate(q, "The answer is 1.0")
        assert r.correct is True

    def test_multiple_numbers_takes_last(self):
        ev = GSM8KEvaluator()
        q = GSM8KQuestion(id="1", question="Q", answer=99)
        r = ev.evaluate(q, "First I got 5, then 99")
        assert r.predicted == 99
