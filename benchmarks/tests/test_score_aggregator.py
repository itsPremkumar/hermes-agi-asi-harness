"""Tests for score_aggregator.py — Score Aggregator."""

from benchmark.score_aggregator import (
    BenchmarkScore,
    ScoreAggregator,
    ScoreReport,
)


class TestBenchmarkScore:
    def test_create(self):
        s = BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85)
        assert s.benchmark == "mmlu"
        assert s.score == 85.0
        assert s.weight == 1.0

    def test_create_with_weight(self):
        s = BenchmarkScore(benchmark="mmlu", category="knowledge", score=90.0, num_problems=100, num_correct=90, weight=2.0)
        assert s.weight == 2.0

    def test_to_dict(self):
        s = BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85)
        d = s.to_dict()
        assert d["benchmark"] == "mmlu"
        assert d["score"] == 85.0


class TestScoreReport:
    def test_create(self):
        r = ScoreReport(id="r1", overall_score=75.0, category_scores={"knowledge": 80.0}, benchmark_scores={"mmlu": 85.0}, improvements=[], timestamp=0.0)
        assert r.id == "r1"
        assert r.overall_score == 75.0

    def test_to_dict(self):
        r = ScoreReport(id="r1", overall_score=75.0, category_scores={"knowledge": 80.0}, benchmark_scores={"mmlu": 85.0}, improvements=[], timestamp=0.0)
        d = r.to_dict()
        assert d["overall_score"] == 75.0
        assert d["category_scores"]["knowledge"] == 80.0


class TestScoreAggregator:
    def test_create(self):
        agg = ScoreAggregator()
        assert len(agg.scores) == 0
        assert len(agg.history) == 0

    def test_add_score(self):
        agg = ScoreAggregator()
        s = BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85)
        agg.add_score(s)
        assert len(agg.scores) == 1

    def test_compute_overall_score_single(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=80.0, num_problems=100, num_correct=80))
        assert agg.compute_overall_score() == 80.0

    def test_compute_overall_score_multiple(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=80.0, num_problems=100, num_correct=80))
        agg.add_score(BenchmarkScore(benchmark="gsm8k", category="math", score=90.0, num_problems=100, num_correct=90))
        assert agg.compute_overall_score() == 85.0

    def test_compute_overall_score_weighted(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=80.0, num_problems=100, num_correct=80, weight=2.0))
        agg.add_score(BenchmarkScore(benchmark="gsm8k", category="math", score=90.0, num_problems=100, num_correct=90, weight=1.0))
        # (80*2 + 90*1) / 3 = 250/3 = 83.33
        assert abs(agg.compute_overall_score() - 83.333) < 0.01

    def test_compute_overall_score_empty(self):
        agg = ScoreAggregator()
        assert agg.compute_overall_score() == 0.0

    def test_compute_category_score(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=80.0, num_problems=100, num_correct=80))
        agg.add_score(BenchmarkScore(benchmark="hellaswag", category="knowledge", score=90.0, num_problems=100, num_correct=90))
        assert agg.compute_category_score("knowledge") == 85.0

    def test_compute_category_score_missing(self):
        agg = ScoreAggregator()
        assert agg.compute_category_score("nonexistent") == 0.0

    def test_compute_benchmark_score(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        assert agg.compute_benchmark_score("mmlu") == 85.0

    def test_compute_benchmark_score_missing(self):
        agg = ScoreAggregator()
        assert agg.compute_benchmark_score("nonexistent") == 0.0

    def test_rank_improvements(self):
        agg = ScoreAggregator()
        # First run
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=70.0, num_problems=100, num_correct=70))
        # Second run - MMLU improved
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        # GSM8K declined
        agg.add_score(BenchmarkScore(benchmark="gsm8k", category="math", score=90.0, num_problems=100, num_correct=90))
        agg.add_score(BenchmarkScore(benchmark="gsm8k", category="math", score=75.0, num_problems=100, num_correct=75))
        ranked = agg.rank_improvements()
        assert "mmlu" in ranked
        assert "gsm8k" in ranked
        # MMLU should be first (+15 vs -15)
        assert ranked[0] == "mmlu"

    def test_rank_improvements_single_score(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        assert agg.rank_improvements() == []

    def test_rank_improvements_empty(self):
        agg = ScoreAggregator()
        assert agg.rank_improvements() == []

    def test_generate_score_report(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        report = agg.generate_score_report()
        assert isinstance(report, ScoreReport)
        assert report.overall_score == 85.0

    def test_generate_score_report_multiple_categories(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        agg.add_score(BenchmarkScore(benchmark="gsm8k", category="math", score=90.0, num_problems=100, num_correct=90))
        report = agg.generate_score_report()
        assert report.category_scores["knowledge"] == 85.0
        assert report.category_scores["math"] == 90.0

    def test_generate_score_report_stores_history(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        agg.generate_score_report()
        assert len(agg.history) == 1

    def test_generate_score_report_unique_ids(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        r1 = agg.generate_score_report()
        r2 = agg.generate_score_report()
        assert r1.id != r2.id

    def test_get_category_breakdown(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        agg.add_score(BenchmarkScore(benchmark="hellaswag", category="knowledge", score=90.0, num_problems=100, num_correct=90))
        agg.add_score(BenchmarkScore(benchmark="gsm8k", category="math", score=80.0, num_problems=100, num_correct=80))
        breakdown = agg.get_category_breakdown()
        assert "knowledge" in breakdown
        assert "math" in breakdown
        assert len(breakdown["knowledge"]) == 2
        assert len(breakdown["math"]) == 1

    def test_get_category_breakdown_empty(self):
        agg = ScoreAggregator()
        assert agg.get_category_breakdown() == {}

    def test_overall_score_zero_weight(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85, weight=0.0))
        assert agg.compute_overall_score() == 0.0

    def test_category_score_zero_weight(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85, weight=0.0))
        assert agg.compute_category_score("knowledge") == 0.0

    def test_score_report_to_dict(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        report = agg.generate_score_report()
        d = report.to_dict()
        assert "id" in d
        assert "overall_score" in d
        assert "category_scores" in d
        assert "benchmark_scores" in d
        assert "improvements" in d
        assert "timestamp" in d

    def test_multiple_benchmarks_same_category(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=80.0, num_problems=100, num_correct=80))
        agg.add_score(BenchmarkScore(benchmark="hellaswag", category="knowledge", score=90.0, num_problems=100, num_correct=90))
        agg.add_score(BenchmarkScore(benchmark="boolq", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        cat_score = agg.compute_category_score("knowledge")
        assert cat_score == 85.0

    def test_overall_score_many_benchmarks(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=80.0, num_problems=100, num_correct=80))
        agg.add_score(BenchmarkScore(benchmark="gsm8k", category="math", score=90.0, num_problems=100, num_correct=90))
        agg.add_score(BenchmarkScore(benchmark="humaneval", category="coding", score=70.0, num_problems=100, num_correct=70))
        agg.add_score(BenchmarkScore(benchmark="mbpp", category="coding", score=85.0, num_problems=100, num_correct=85))
        overall = agg.compute_overall_score()
        assert overall == 81.25

    def test_rank_improvements_order(self):
        agg = ScoreAggregator()
        # Benchmark A: +20 improvement
        agg.add_score(BenchmarkScore(benchmark="A", category="test", score=50.0, num_problems=100, num_correct=50))
        agg.add_score(BenchmarkScore(benchmark="A", category="test", score=70.0, num_problems=100, num_correct=70))
        # Benchmark B: +5 improvement
        agg.add_score(BenchmarkScore(benchmark="B", category="test", score=80.0, num_problems=100, num_correct=80))
        agg.add_score(BenchmarkScore(benchmark="B", category="test", score=85.0, num_problems=100, num_correct=85))
        ranked = agg.rank_improvements()
        assert ranked[0] == "A"
        assert ranked[1] == "B"

    def test_score_with_metadata(self):
        s = BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85, metadata={"model": "gpt-4"})
        assert s.metadata["model"] == "gpt-4"

    def test_score_report_improvements(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=70.0, num_problems=100, num_correct=70))
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        report = agg.generate_score_report()
        assert "mmlu" in report.improvements

    def test_history_accumulates(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85))
        agg.generate_score_report()
        agg.generate_score_report()
        agg.generate_score_report()
        assert len(agg.history) == 3

    def test_benchmark_score_to_dict(self):
        s = BenchmarkScore(benchmark="mmlu", category="knowledge", score=85.0, num_problems=100, num_correct=85, weight=1.5)
        d = s.to_dict()
        assert d["weight"] == 1.5
        assert d["num_correct"] == 85

    def test_aggregator_with_no_scores(self):
        agg = ScoreAggregator()
        report = agg.generate_score_report()
        assert report.overall_score == 0.0
        assert report.category_scores == {}
        assert report.benchmark_scores == {}
        assert report.improvements == []

    def test_category_score_weighted(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=80.0, num_problems=100, num_correct=80, weight=3.0))
        agg.add_score(BenchmarkScore(benchmark="hellaswag", category="knowledge", score=90.0, num_problems=100, num_correct=90, weight=1.0))
        # (80*3 + 90*1) / 4 = 330/4 = 82.5
        assert agg.compute_category_score("knowledge") == 82.5

    def test_rank_improvements_negative(self):
        agg = ScoreAggregator()
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=90.0, num_problems=100, num_correct=90))
        agg.add_score(BenchmarkScore(benchmark="mmlu", category="knowledge", score=70.0, num_problems=100, num_correct=70))
        ranked = agg.rank_improvements()
        assert ranked[0] == "mmlu"  # -20 change, still listed
