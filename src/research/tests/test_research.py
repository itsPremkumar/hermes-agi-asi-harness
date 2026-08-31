"""Tests for Research module."""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from research.benchmark_research import (
    BenchmarkResearch, BenchmarkRun, TrendAnalysis, TrendDirection,
    ImprovementRecommendation,
)


class TestBenchmarkRun:
    def test_create(self):
        run = BenchmarkRun(id="r1", task_id="t1", score=0.9, duration_ms=100, iterations=3)
        assert run.id == "r1"
        assert run.task_id == "t1"
        assert run.score == 0.9
        assert run.duration_ms == 100
        assert run.iterations == 3

    def test_default_timestamp(self):
        run = BenchmarkRun(id="r1", task_id="t1", score=0.9, duration_ms=100, iterations=3)
        assert run.timestamp > 0


class TestTrendAnalysis:
    def test_create(self):
        analysis = TrendAnalysis(
            task_id="t1",
            direction=TrendDirection.IMPROVING,
            slope=0.1,
            confidence=0.8,
            data_points=5,
            recommendation="Continue",
        )
        assert analysis.task_id == "t1"
        assert analysis.direction == TrendDirection.IMPROVING
        assert analysis.slope == 0.1


class TestImprovementRecommendation:
    def test_create(self):
        rec = ImprovementRecommendation(
            id="rec1",
            category="strategy",
            description="Try new approach",
            expected_impact=0.7,
            effort=0.5,
        )
        assert rec.id == "rec1"
        assert rec.category == "strategy"
        assert rec.priority == 0.7 / 0.5

    def test_priority_calculation(self):
        rec = ImprovementRecommendation(
            id="rec1",
            category="parameters",
            description="Tune",
            expected_impact=0.6,
            effort=0.2,
        )
        assert rec.priority == 0.6 / 0.2

    def test_priority_min_effort(self):
        rec = ImprovementRecommendation(
            id="rec1",
            category="test",
            description="Test",
            expected_impact=0.5,
            effort=0.0,
        )
        assert rec.priority == 0.5 / 0.01


class TestTrendDirection:
    def test_values(self):
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.DECLINING.value == "declining"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.VOLATILE.value == "volatile"


class TestBenchmarkResearch:
    def test_create(self):
        research = BenchmarkResearch()
        assert research.get_stats()["total_runs"] == 0

    def test_record_run(self):
        research = BenchmarkResearch()
        run = BenchmarkRun(id="r1", task_id="t1", score=0.9, duration_ms=100, iterations=3)
        research.record_run(run)
        assert research.get_stats()["total_runs"] == 1

    def test_get_runs(self):
        research = BenchmarkResearch()
        research.record_run(BenchmarkRun(id="r1", task_id="t1", score=0.9, duration_ms=100, iterations=3))
        research.record_run(BenchmarkRun(id="r2", task_id="t2", score=0.8, duration_ms=100, iterations=3))
        assert len(research.get_runs()) == 2

    def test_get_runs_by_task(self):
        research = BenchmarkResearch()
        research.record_run(BenchmarkRun(id="r1", task_id="t1", score=0.9, duration_ms=100, iterations=3))
        research.record_run(BenchmarkRun(id="r2", task_id="t1", score=0.8, duration_ms=100, iterations=3))
        research.record_run(BenchmarkRun(id="r3", task_id="t2", score=0.7, duration_ms=100, iterations=3))
        assert len(research.get_runs("t1")) == 2

    def test_analyze_trend_stable(self):
        research = BenchmarkResearch()
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.5 + i * 0.005,  # Very small change
                duration_ms=100, iterations=3,
            ))
        analysis = research.analyze_trend("t1")
        assert analysis.direction == TrendDirection.STABLE

    def test_analyze_trend_improving(self):
        research = BenchmarkResearch()
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.1 + i * 0.1,  # Clear improvement
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        analysis = research.analyze_trend("t1")
        assert analysis.direction == TrendDirection.IMPROVING
        assert analysis.slope > 0

    def test_analyze_trend_declining(self):
        research = BenchmarkResearch()
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.9 - i * 0.1,  # Clear decline
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        analysis = research.analyze_trend("t1")
        assert analysis.direction == TrendDirection.DECLINING
        assert analysis.slope < 0

    def test_analyze_trend_insufficient_data(self):
        research = BenchmarkResearch()
        research.record_run(BenchmarkRun(id="r1", task_id="t1", score=0.5, duration_ms=100, iterations=3))
        analysis = research.analyze_trend("t1")
        assert analysis.data_points == 1
        assert "Need more data" in analysis.recommendation

    def test_analyze_trend_volatile(self):
        research = BenchmarkResearch()
        scores = [0.1, 0.9, 0.2, 0.8, 0.3]  # High variance
        for i, score in enumerate(scores):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=score, duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        analysis = research.analyze_trend("t1")
        assert analysis.direction == TrendDirection.VOLATILE

    def test_generate_recommendations_declining(self):
        research = BenchmarkResearch()
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.9 - i * 0.1,
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        recommendations = research.generate_recommendations()
        assert len(recommendations) >= 1

    def test_generate_recommendations_stable(self):
        research = BenchmarkResearch()
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.5 + i * 0.005,
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        recommendations = research.generate_recommendations()
        assert len(recommendations) >= 1

    def test_recommendations_sorted_by_priority(self):
        research = BenchmarkResearch()
        # Declining task
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="declining",
                score=0.9 - i * 0.1,
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        # Stable task
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"s{i}", task_id="stable",
                score=0.5,
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        recommendations = research.generate_recommendations()
        # Verify sorted by priority (descending)
        for i in range(len(recommendations) - 1):
            assert recommendations[i].priority >= recommendations[i + 1].priority

    def test_get_trend(self):
        research = BenchmarkResearch()
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.1 + i * 0.1,
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        research.analyze_trend("t1")
        trend = research.get_trend("t1")
        assert trend is not None
        assert trend.task_id == "t1"

    def test_get_all_trends(self):
        research = BenchmarkResearch()
        for task in ["t1", "t2"]:
            for i in range(5):
                research.record_run(BenchmarkRun(
                    id=f"{task}_r{i}", task_id=task,
                    score=0.1 + i * 0.1,
                    duration_ms=100, iterations=3,
                    timestamp=time.time() + i,
                ))
        research.analyze_trend("t1")
        research.analyze_trend("t2")
        trends = research.get_all_trends()
        assert len(trends) == 2

    def test_get_recommendations(self):
        research = BenchmarkResearch()
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.9 - i * 0.1,
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        research.generate_recommendations()
        recommendations = research.get_recommendations()
        assert len(recommendations) >= 1

    def test_get_stats_empty(self):
        research = BenchmarkResearch()
        stats = research.get_stats()
        assert stats["total_runs"] == 0
        assert stats["avg_score"] == 0.0

    def test_get_stats_with_runs(self):
        research = BenchmarkResearch()
        research.record_run(BenchmarkRun(id="r1", task_id="t1", score=0.8, duration_ms=100, iterations=3))
        research.record_run(BenchmarkRun(id="r2", task_id="t2", score=0.6, duration_ms=100, iterations=3))
        stats = research.get_stats()
        assert stats["total_runs"] == 2
        assert stats["avg_score"] == 0.7
        assert stats["min_score"] == 0.6
        assert stats["max_score"] == 0.8
        assert stats["tasks"] == 2

    def test_clear(self):
        research = BenchmarkResearch()
        research.record_run(BenchmarkRun(id="r1", task_id="t1", score=0.9, duration_ms=100, iterations=3))
        research.clear()
        assert research.get_stats()["total_runs"] == 0


class TestResearchIntegration:
    def test_full_pipeline(self):
        research = BenchmarkResearch()
        # Record multiple runs
        for i in range(10):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.3 + i * 0.05,
                duration_ms=100 + i * 10,
                iterations=3,
                timestamp=time.time() + i,
            ))
        # Analyze trends
        analysis = research.analyze_trend("t1")
        assert analysis.data_points == 10
        assert analysis.confidence == 1.0

        # Generate recommendations
        recommendations = research.generate_recommendations()
        assert isinstance(recommendations, list)

    def test_multiple_tasks(self):
        research = BenchmarkResearch()
        for task in ["task_a", "task_b", "task_c"]:
            for i in range(5):
                research.record_run(BenchmarkRun(
                    id=f"{task}_{i}", task_id=task,
                    score=0.1 + i * 0.1,
                    duration_ms=100, iterations=3,
                    timestamp=time.time() + i,
                ))
        stats = research.get_stats()
        assert stats["tasks"] == 3
        assert stats["total_runs"] == 15

    def test_confidence_increases_with_data(self):
        research = BenchmarkResearch()
        # Run with few data points
        for i in range(2):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.5, duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        analysis_few = research.analyze_trend("t1")

        # Run with more data points
        for i in range(2, 10):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.5, duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        analysis_more = research.analyze_trend("t1")
        assert analysis_more.confidence > analysis_few.confidence

    def test_recommendation_categories(self):
        research = BenchmarkResearch()
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.9 - i * 0.1,
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        recommendations = research.generate_recommendations()
        categories = set(r.category for r in recommendations)
        assert len(categories) >= 1

    def test_stats_after_clear(self):
        research = BenchmarkResearch()
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.5, duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        research.clear()
        stats = research.get_stats()
        assert stats["total_runs"] == 0
        assert stats["tasks"] == 0

    def test_trend_after_more_runs(self):
        research = BenchmarkResearch()
        # Initial improving trend
        for i in range(5):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.1 + i * 0.1,
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        analysis1 = research.analyze_trend("t1")

        # Add declining trend
        for i in range(5, 10):
            research.record_run(BenchmarkRun(
                id=f"r{i}", task_id="t1",
                score=0.9 - (i - 5) * 0.1,
                duration_ms=100, iterations=3,
                timestamp=time.time() + i,
            ))
        analysis2 = research.analyze_trend("t1")

        # With mixed data, should be volatile or different direction
        assert analysis2.data_points == 10
