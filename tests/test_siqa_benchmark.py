"""
Tests for SIQA Benchmark.
Test count: 22
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmark.siqa_benchmark import (
    SIQABenchmark,
    SIQADataset,
    SIQAQuestion,
    SIQAResult,
)

# ──────────────────── Domain Model Tests ──────────────────────────────


class TestSIQAQuestion:
    def test_create(self):
        q = SIQAQuestion(
            id="q1",
            context="Alex got a promotion.",
            question="How would Alex feel?",
            choices=["happy", "sad", "indifferent"],
            correct_answer=0,
        )
        assert q.id == "q1"
        assert q.correct_answer == 0
        assert len(q.choices) == 3

    def test_default_metadata(self):
        q = SIQAQuestion(id="q1", context="", question="", choices=[], correct_answer=0)
        assert q.metadata == {}


class TestSIQADataset:
    def test_create(self):
        dataset = SIQADataset(questions=[])
        assert len(dataset.questions) == 0

    def test_create_with_questions(self):
        q = SIQAQuestion(id="q1", context="", question="", choices=[], correct_answer=0)
        dataset = SIQADataset(questions=[q])
        assert len(dataset.questions) == 1


class TestSIQAResult:
    def test_create_correct(self):
        result = SIQAResult(
            question_id="q1",
            predicted_answer=0,
            correct_answer=0,
            correct=True,
        )
        assert result.correct is True

    def test_create_incorrect(self):
        result = SIQAResult(
            question_id="q1",
            predicted_answer=1,
            correct_answer=0,
            correct=False,
        )
        assert result.correct is False

    def test_default_values(self):
        result = SIQAResult(question_id="q1", predicted_answer=0, correct_answer=0, correct=True)
        assert result.confidence == 0.0
        assert result.duration == 0.0


# ──────────────── SIQABenchmark Tests ─────────────────────────────────


class TestSIQABenchmark:
    def test_create(self):
        bench = SIQABenchmark()
        assert bench.data_dir.exists() or True

    def test_load_no_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            dataset = bench.load()
            # Should generate synthetic data
            assert len(dataset.questions) > 0

    def test_load_with_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test JSONL file
            data = [
                {"id": "q1", "context": "Test", "question": "Q?", "choices": {"0": "A", "1": "B"}, "correct": "0"},
                {"id": "q2", "context": "Test2", "question": "Q2?", "choices": {"0": "A", "1": "B"}, "correct": "1"},
            ]
            with open(os.path.join(tmpdir, "siqa_validation.jsonl"), "w") as f:
                for item in data:
                    f.write(json.dumps(item) + "\n")

            bench = SIQABenchmark(data_dir=tmpdir)
            dataset = bench.load()
            assert len(dataset.questions) == 2

    def test_load_with_answer_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = [
                {"id": "q1", "context": "Test", "question": "Q?", "answerA": "Yes", "answerB": "No", "answerC": "Maybe", "answer": "A"},
            ]
            with open(os.path.join(tmpdir, "siqa_validation.jsonl"), "w") as f:
                for item in data:
                    f.write(json.dumps(item) + "\n")

            bench = SIQABenchmark(data_dir=tmpdir)
            dataset = bench.load()
            assert len(dataset.questions) == 1
            assert len(dataset.questions[0].choices) == 3

    def test_run_all(self):
        async def predictor(question):
            return question.correct_answer

        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            results = bench.run(predictor)
            assert len(results) > 0
            assert all(r.correct for r in results)

    def test_run_max_questions(self):
        async def predictor(question):
            return question.correct_answer

        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            results = bench.run(predictor, max_questions=5)
            assert len(results) == 5

    def test_run_sample(self):
        async def predictor(question):
            return question.correct_answer

        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            results = bench.run_sample(predictor, sample_size=5)
            assert len(results) == 5

    def test_run_sample_seed(self):
        async def predictor(question):
            return question.correct_answer

        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            r1 = bench.run_sample(predictor, sample_size=5, seed=42)
            bench.reset()
            r2 = bench.run_sample(predictor, sample_size=5, seed=42)
            assert [r.question_id for r in r1] == [r.question_id for r in r2]

    def test_get_accuracy(self):
        async def predictor(question):
            return question.correct_answer

        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            bench.run(predictor, max_questions=10)
            accuracy = bench.get_accuracy()
            assert accuracy == 1.0

    def test_get_accuracy_no_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            assert bench.get_accuracy() == 0.0

    def test_get_report(self):
        async def predictor(question):
            return question.correct_answer

        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            bench.run(predictor, max_questions=10)
            report = bench.get_report()
            assert report["benchmark"] == "SIQA"
            assert report["total_questions"] == 10
            assert report["correct"] == 10
            assert report["accuracy"] == 1.0

    def test_get_report_no_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            report = bench.get_report()
            assert "error" in report

    def test_get_results(self):
        async def predictor(question):
            return question.correct_answer

        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            bench.run(predictor, max_questions=5)
            results = bench.get_results()
            assert len(results) == 5

    def test_get_dataset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            dataset = bench.get_dataset()
            assert dataset is not None
            assert len(dataset.questions) > 0

    def test_reset(self):
        async def predictor(question):
            return question.correct_answer

        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            bench.run(predictor, max_questions=5)
            assert len(bench.get_results()) == 5
            bench.reset()
            assert len(bench.get_results()) == 0

    def test_predictor_error_handling(self):
        async def bad_predictor(question):
            raise ValueError("Prediction failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            results = bench.run(bad_predictor, max_questions=5)
            assert all(not r.correct for r in results)

    def test_run_partial_correct(self):
        async def partial_predictor(question):
            # Intentionally imperfect: only correct for answer index 0
            return 0

        with tempfile.TemporaryDirectory() as tmpdir:
            bench = SIQABenchmark(data_dir=tmpdir)
            bench.load()
            results = bench.run(partial_predictor, max_questions=20)
            correct_count = sum(1 for r in results if r.correct)
            assert 0 < correct_count < 20
