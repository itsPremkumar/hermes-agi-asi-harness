import pytest
import os
import tempfile
import json

from benchmark.mmlu_benchmark import MMLUQuestion, MMLUResult, MMLULoader, MMLUEvaluator, MMLUBenchmark


def _create_temp_json(data):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return path


class TestMMLULoader:
    def test_create(self):
        loader = MMLULoader()
        assert len(loader.questions) == 0

    def test_load_questions(self):
        path = _create_temp_json([
            {"id": "1", "question": "What is 2+2?", "subject": "math", "choices": ["1", "2", "3", "4"], "answer": 3},
            {"id": "2", "question": "What is H2O?", "subject": "chemistry", "choices": ["water", "air", "earth", "fire"], "answer": 0},
        ])
        loader = MMLULoader()
        questions = loader.load_questions(path)
        assert len(questions) == 2
        os.unlink(path)

    def test_get_by_subject(self):
        path = _create_temp_json([
            {"id": "1", "question": "Q1", "subject": "math", "choices": ["a", "b", "c", "d"], "answer": 0},
            {"id": "2", "question": "Q2", "subject": "science", "choices": ["a", "b", "c", "d"], "answer": 1},
            {"id": "3", "question": "Q3", "subject": "math", "choices": ["a", "b", "c", "d"], "answer": 2},
        ])
        loader = MMLULoader()
        loader.load_questions(path)
        math = loader.get_by_subject("math")
        assert len(math) == 2
        os.unlink(path)

    def test_get_subjects(self):
        path = _create_temp_json([
            {"id": "1", "question": "Q1", "subject": "math", "choices": ["a", "b", "c", "d"], "answer": 0},
            {"id": "2", "question": "Q2", "subject": "science", "choices": ["a", "b", "c", "d"], "answer": 1},
        ])
        loader = MMLULoader()
        loader.load_questions(path)
        subjects = loader.get_subjects()
        assert "math" in subjects
        assert "science" in subjects
        os.unlink(path)


class TestMMLUEvaluator:
    def test_evaluate_correct(self):
        ev = MMLUEvaluator()
        q = MMLUQuestion(id="1", question="Q", subject="math", choices=["a", "b", "c", "d"], answer=2)
        r = ev.evaluate(q, 2)
        assert r.correct is True

    def test_evaluate_incorrect(self):
        ev = MMLUEvaluator()
        q = MMLUQuestion(id="1", question="Q", subject="math", choices=["a", "b", "c", "d"], answer=2)
        r = ev.evaluate(q, 0)
        assert r.correct is False


class TestMMLUBenchmark:
    def test_create(self):
        b = MMLUBenchmark()
        assert len(b.results) == 0

    def test_load_and_run(self):
        path = _create_temp_json([
            {"id": "1", "question": "What is 2+2?", "subject": "math", "choices": ["1", "2", "3", "4"], "answer": 3},
        ])
        b = MMLUBenchmark()
        b.load_questions(path)
        r = b.run_question("1", 3)
        assert r is not None
        assert r.correct is True
        os.unlink(path)

    def test_get_accuracy(self):
        path = _create_temp_json([
            {"id": "1", "question": "Q1", "subject": "math", "choices": ["a", "b", "c", "d"], "answer": 0},
            {"id": "2", "question": "Q2", "subject": "math", "choices": ["a", "b", "c", "d"], "answer": 1},
        ])
        b = MMLUBenchmark()
        b.load_questions(path)
        b.run_question("1", 0)  # correct
        b.run_question("2", 0)  # wrong
        acc = b.get_accuracy()
        assert acc["accuracy"] == 0.5
        assert acc["total"] == 2
        os.unlink(path)

    def test_get_subject_accuracy(self):
        path = _create_temp_json([
            {"id": "1", "question": "Q1", "subject": "math", "choices": ["a", "b", "c", "d"], "answer": 0},
            {"id": "2", "question": "Q2", "subject": "science", "choices": ["a", "b", "c", "d"], "answer": 1},
        ])
        b = MMLUBenchmark()
        b.load_questions(path)
        b.run_question("1", 0)  # correct
        b.run_question("2", 0)  # wrong
        math_acc = b.get_accuracy("math")
        assert math_acc["accuracy"] == 1.0
        science_acc = b.get_accuracy("science")
        assert science_acc["accuracy"] == 0.0
        os.unlink(path)


class TestMMLUQuestion:
    def test_create(self):
        q = MMLUQuestion(id="1", question="What is 2+2?", subject="math", choices=["1", "2", "3", "4"], answer=3)
        assert q.question == "What is 2+2?"
        assert q.answer == 3

    def test_from_dict(self):
        d = {"id": "2", "question": "Q", "subject": "sci", "choices": ["a", "b", "c", "d"], "answer": 1}
        q = MMLUQuestion.from_dict(d)
        assert q.subject == "sci"


class TestMMLUResult:
    def test_create(self):
        r = MMLUResult(id="r1", question_id="q1", predicted=2, correct=True, subject="math")
        assert r.correct is True
        assert r.subject == "math"


class TestMMLUBenchmarkAllSubjects:
    def test_all_subjects_accuracy(self):
        path = _create_temp_json([
            {"id": "1", "question": "Q1", "subject": "math", "choices": ["a", "b", "c", "d"], "answer": 0},
            {"id": "2", "question": "Q2", "subject": "science", "choices": ["a", "b", "c", "d"], "answer": 1},
            {"id": "3", "question": "Q3", "subject": "math", "choices": ["a", "b", "c", "d"], "answer": 2},
        ])
        b = MMLUBenchmark()
        b.load_questions(path)
        b.run_question("1", 0)  # correct
        b.run_question("2", 0)  # wrong
        b.run_question("3", 2)  # correct
        all_acc = b.get_all_subjects_accuracy()
        assert "math" in all_acc
        assert "science" in all_acc
        assert all_acc["math"]["accuracy"] == 1.0
        assert all_acc["science"]["accuracy"] == 0.0
        os.unlink(path)


class TestMMLUBenchmarkEdgeCases:
    def test_missing_file(self):
        loader = MMLULoader()
        assert loader.load_questions("/nonexistent/path.json") == []

    def test_unknown_question(self):
        b = MMLUBenchmark()
        assert b.run_question("nonexistent", 0) is None

    def test_accuracy_no_results(self):
        b = MMLUBenchmark()
        acc = b.get_accuracy()
        assert acc["accuracy"] == 0.0
        assert acc["total"] == 0

    def test_batch_evaluate(self):
        ev = MMLUEvaluator()
        q1 = MMLUQuestion(id="1", question="Q1", subject="math", choices=["a", "b", "c", "d"], answer=0)
        q2 = MMLUQuestion(id="2", question="Q2", subject="math", choices=["a", "b", "c", "d"], answer=1)
        results = ev.evaluate_batch([q1, q2], [0, 1])
        assert len(results) == 2
        assert results[0].correct is True
        assert results[1].correct is True

    def test_multiple_subjects(self):
        path = _create_temp_json([
            {"id": "1", "question": "Q1", "subject": "math", "choices": ["a", "b", "c", "d"], "answer": 0},
            {"id": "2", "question": "Q2", "subject": "science", "choices": ["a", "b", "c", "d"], "answer": 1},
            {"id": "3", "question": "Q3", "subject": "history", "choices": ["a", "b", "c", "d"], "answer": 2},
        ])
        b = MMLUBenchmark()
        b.load_questions(path)
        assert len(b.loader.get_subjects()) == 3
        os.unlink(path)
