"""Tests for siqa_benchmark.py — SIQA Benchmark."""

from src.benchmark.siqa_benchmark import (
    SIQABenchmark,
    SIQADataset,
    SIQAQuestion,
    SIQAResult,
)


class TestSIQABenchmark:
    def test_create(self):
        b = SIQABenchmark()
        assert b.get_results() == []

    def test_load_default(self):
        b = SIQABenchmark()
        b.load()
        assert b.get_dataset() is not None
        assert len(b.get_dataset().questions) > 0

    def test_run(self):
        b = SIQABenchmark()
        b.load()
        async def predictor(q):
            return 0
        results = b.run(predictor)
        assert len(results) > 0

    def test_run_sample(self):
        b = SIQABenchmark()
        b.load()
        async def predictor(q):
            return 0
        results = b.run_sample(predictor, sample_size=5)
        assert len(results) == 5

    def test_get_accuracy(self):
        b = SIQABenchmark()
        b.load()
        async def predictor(q):
            return q.correct_answer
        b.run(predictor)
        assert b.get_accuracy() == 1.0

    def test_get_accuracy_partial(self):
        b = SIQABenchmark()
        b.load()
        async def predictor(q):
            return 0  # not always correct
        b.run(predictor)
        acc = b.get_accuracy()
        assert 0 <= acc <= 1

    def test_get_report(self):
        b = SIQABenchmark()
        b.load()
        async def predictor(q):
            return 0
        b.run(predictor)
        report = b.get_report()
        assert "accuracy" in report
        assert "total_questions" in report

    def test_get_results(self):
        b = SIQABenchmark()
        b.load()
        async def predictor(q):
            return 0
        b.run(predictor)
        assert len(b.get_results()) > 0

    def test_reset(self):
        b = SIQABenchmark()
        b.load()
        async def predictor(q):
            return 0
        b.run(predictor)
        b.reset()
        assert b.get_results() == []

    def test_siqa_question(self):
        q = SIQAQuestion(id="t1", context="ctx", question="q", choices=["a", "b", "c"], correct_answer=0)
        assert q.id == "t1"
        assert q.correct_answer == 0

    def test_siqa_result(self):
        r = SIQAResult(question_id="t1", predicted_answer=0, correct_answer=0, correct=True)
        assert r.correct is True
        assert r.duration == 0.0

    def test_siqa_dataset(self):
        ds = SIQADataset(questions=[], metadata={})
        assert ds.questions == []

    def test_run_sample_seed(self):
        b = SIQABenchmark()
        b.load()
        async def predictor(q):
            return 0
        r1 = b.run_sample(predictor, sample_size=5, seed=42)
        r2 = b.run_sample(predictor, sample_size=5, seed=42)
        assert len(r1) == len(r2)
