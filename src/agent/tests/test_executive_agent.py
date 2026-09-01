"""Tests for executive_agent.py — Executive Agent."""

import asyncio
import pytest
from agent.executive_agent import (
    ExecutiveAgent, BenchmarkOrchestrator, ScoreAggregator, ImprovementPlanner,
    DailyCycle, BenchmarkTask, BenchmarkResult, Scorecard, ImprovementPlan, DailyReport,
)


class TestBenchmarkTask:
    def test_create(self):
        t = BenchmarkTask(id="t1", name="mmlu", category="knowledge")
        assert t.id == "t1"
        assert t.name == "mmlu"
        assert t.weight == 1.0

    def test_default_id(self):
        t = BenchmarkTask(id="", name="mmlu", category="knowledge")
        assert t.id != ""


class TestBenchmarkResult:
    def test_create(self):
        r = BenchmarkResult(task_id="t1", benchmark_name="mmlu", score=0.85)
        assert r.score == 0.85
        assert r.success is True

    def test_success_false_on_error(self):
        r = BenchmarkResult(task_id="t1", benchmark_name="mmlu", score=0.0, error="fail")
        assert r.success is False


class TestScorecard:
    def test_create(self):
        s = Scorecard(id="s1", timestamp=0.0, overall_score=0.8, category_scores={"math": 0.9}, benchmark_results=[])
        assert s.overall_score == 0.8

    def test_to_dict(self):
        s = Scorecard(id="s1", timestamp=0.0, overall_score=0.8, category_scores={}, benchmark_results=[])
        d = s.to_dict()
        assert d["overall_score"] == 0.8


class TestImprovementPlan:
    def test_create(self):
        p = ImprovementPlan(id="p1", target_benchmark="mmlu", current_score=0.5, target_score=0.9, strategies=["s1", "s2"])
        assert p.priority == 0

    def test_default_id(self):
        p = ImprovementPlan(id="", target_benchmark="mmlu", current_score=0.5, target_score=0.9, strategies=[])
        assert p.id != ""


class TestDailyReport:
    def test_create(self):
        r = DailyReport(id="r1", date="2024-01-01", cycle_number=1, scorecards=[], improvements_attempted=0, improvements_succeeded=0, key_findings=[], recommendations=[])
        assert r.cycle_number == 1

    def test_to_dict(self):
        r = DailyReport(id="r1", date="2024-01-01", cycle_number=1, scorecards=[], improvements_attempted=0, improvements_succeeded=0, key_findings=[], recommendations=[])
        d = r.to_dict()
        assert d["cycle_number"] == 1


class TestBenchmarkOrchestrator:
    def test_create(self):
        o = BenchmarkOrchestrator()
        assert o.max_concurrent == 4

    def test_register_benchmark(self):
        o = BenchmarkOrchestrator()
        o.register_benchmark("mmlu", lambda t: {})
        assert len(o._benchmarks) == 1

    def test_add_task(self):
        o = BenchmarkOrchestrator()
        o.add_task(BenchmarkTask(id="t1", name="mmlu", category="knowledge"))
        assert len(o._tasks) == 1


class TestScoreAggregator:
    def test_create(self):
        s = ScoreAggregator()
        assert s is not None

    def test_aggregate_empty(self):
        s = ScoreAggregator()
        sc = s.aggregate([], [])
        assert sc.overall_score == 0.0


class TestImprovementPlanner:
    def test_create(self):
        p = ImprovementPlanner()
        assert p is not None

    def test_plan_improvements(self):
        p = ImprovementPlanner()
        sc = Scorecard(id="s1", timestamp=0.0, overall_score=0.5, category_scores={"math": 0.4}, benchmark_results=[])
        plans = p.plan_improvements(sc, target_score=0.95)
        assert len(plans) > 0


class TestDailyCycle:
    def test_create(self):
        o = BenchmarkOrchestrator()
        a = ScoreAggregator()
        p = ImprovementPlanner()
        d = DailyCycle(o, a, p)
        assert d.cycle_number == 0

    def test_scorecard_history(self):
        o = BenchmarkOrchestrator()
        a = ScoreAggregator()
        p = ImprovementPlanner()
        d = DailyCycle(o, a, p)
        assert d.scorecard_history == []


class TestExecutiveAgent:
    def test_create(self):
        a = ExecutiveAgent()
        assert a is not None
