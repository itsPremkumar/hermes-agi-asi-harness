"""
Tests for Executive Agent.
Test count: 42
"""
import asyncio
import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.executive_agent import (
    BenchmarkOrchestrator,
    BenchmarkResult,
    BenchmarkTask,
    DailyCycle,
    DailyReport,
    ImprovementPlan,
    ImprovementPlanner,
    ReportGenerator,
    ScoreAggregator,
    Scorecard,
)


def async_run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ──────────────────── Domain Model Tests ──────────────────────────────


class TestBenchmarkTask:
    def test_create(self):
        task = BenchmarkTask(id="t1", name="test", category="general")
        assert task.id == "t1"
        assert task.name == "test"
        assert task.category == "general"
        assert task.weight == 1.0

    def test_auto_id(self):
        task = BenchmarkTask(id="", name="test", category="general")
        assert len(task.id) > 0

    def test_default_values(self):
        task = BenchmarkTask(id="t1", name="test", category="general")
        assert task.timeout == 300.0
        assert task.metadata == {}


class TestBenchmarkResult:
    def test_create(self):
        result = BenchmarkResult(
            task_id="t1",
            benchmark_name="test_bench",
            score=0.85,
        )
        assert result.score == 0.85
        assert result.success is True

    def test_success_with_error(self):
        result = BenchmarkResult(
            task_id="t1",
            benchmark_name="test_bench",
            score=0.0,
            error="Failed",
        )
        assert result.success is False

    def test_duration(self):
        result = BenchmarkResult(
            task_id="t1",
            benchmark_name="test",
            score=0.5,
        )
        assert result.duration == 0.0


class TestScorecard:
    def test_create(self):
        card = Scorecard(
            id="s1",
            timestamp=123.0,
            overall_score=0.75,
            category_scores={"general": 0.8},
            benchmark_results=[],
        )
        assert card.overall_score == 0.75
        assert card.category_scores["general"] == 0.8

    def test_auto_id(self):
        card = Scorecard(
            id="",
            timestamp=0,
            overall_score=0,
            category_scores={},
            benchmark_results=[],
        )
        assert len(card.id) > 0

    def test_to_dict(self):
        card = Scorecard(
            id="s1",
            timestamp=123.0,
            overall_score=0.75,
            category_scores={"general": 0.8},
            benchmark_results=[],
        )
        d = card.to_dict()
        assert d["overall_score"] == 0.75


class TestImprovementPlan:
    def test_create(self):
        plan = ImprovementPlan(
            id="p1",
            target_benchmark="general",
            current_score=0.5,
            target_score=0.9,
            strategies=["strategy1", "strategy2"],
        )
        assert plan.target_benchmark == "general"
        assert plan.priority == 0

    def test_auto_id(self):
        plan = ImprovementPlan(
            id="",
            target_benchmark="general",
            current_score=0.5,
            target_score=0.9,
            strategies=[],
        )
        assert len(plan.id) > 0


class TestDailyReport:
    def test_create(self):
        report = DailyReport(
            id="r1",
            date="2024-01-15",
            cycle_number=1,
            scorecards=[],
            improvements_attempted=3,
            improvements_succeeded=2,
            key_findings=["finding1"],
            recommendations=["rec1"],
        )
        assert report.cycle_number == 1
        assert report.improvements_attempted == 3

    def test_auto_id(self):
        report = DailyReport(
            id="",
            date="2024-01-15",
            cycle_number=1,
            scorecards=[],
            improvements_attempted=0,
            improvements_succeeded=0,
            key_findings=[],
            recommendations=[],
        )
        assert len(report.id) > 0

    def test_to_dict(self):
        report = DailyReport(
            id="r1",
            date="2024-01-15",
            cycle_number=1,
            scorecards=[],
            improvements_attempted=3,
            improvements_succeeded=2,
            key_findings=["f1"],
            recommendations=["r1"],
        )
        d = report.to_dict()
        assert d["cycle_number"] == 1


# ──────────────── BenchmarkOrchestrator Tests ─────────────────────────


class TestBenchmarkOrchestrator:
    def test_create(self):
        orch = BenchmarkOrchestrator(max_concurrent=4)
        assert orch.max_concurrent == 4

    def test_register_benchmark(self):
        orch = BenchmarkOrchestrator()
        async def my_bench():
            return {"score": 0.9}
        orch.register_benchmark("my_bench", my_bench)
        assert "my_bench" in orch._benchmarks

    def test_add_task(self):
        orch = BenchmarkOrchestrator()
        task = BenchmarkTask(id="t1", name="test", category="general")
        orch.add_task(task)
        assert len(orch._tasks) == 1

    async def _predictor(self, task):
        return {"score": 0.85}

    def test_run_all(self):
        async def run():
            orch = BenchmarkOrchestrator()
            orch.add_task(BenchmarkTask(id="t1", name="test1", category="general"))
            orch.add_task(BenchmarkTask(id="t2", name="test2", category="general"))
            results = await orch.run_all(self._predictor)
            assert len(results) == 2
            assert all(r.success for r in results)
        async_run(run())

    def test_run_all_returns_results(self):
        async def run():
            orch = BenchmarkOrchestrator()
            orch.add_task(BenchmarkTask(id="t1", name="test", category="accuracy"))
            results = await orch.run_all(self._predictor)
            assert len(results) == 1
            assert results[0].score == 0.85
        async_run(run())

    def test_run_category(self):
        async def run():
            orch = BenchmarkOrchestrator()
            orch.add_task(BenchmarkTask(id="t1", name="test1", category="accuracy"))
            orch.add_task(BenchmarkTask(id="t2", name="test2", category="speed"))
            results = await orch.run_category("accuracy", self._predictor)
            assert len(results) == 1
        async_run(run())

    def test_extract_score_numeric(self):
        assert BenchmarkOrchestrator._extract_score(0.85) == 0.85

    def test_extract_score_dict(self):
        assert BenchmarkOrchestrator._extract_score({"score": 0.9}) == 0.9

    def test_extract_score_dict_accuracy(self):
        assert BenchmarkOrchestrator._extract_score({"accuracy": 0.75}) == 0.75


# ─────────────────── ScoreAggregator Tests ─────────────────────────────


class TestScoreAggregator:
    def test_create(self):
        agg = ScoreAggregator()
        assert agg is not None

    def test_aggregate_empty(self):
        agg = ScoreAggregator()
        card = agg.aggregate([], [])
        assert card.overall_score == 0.0

    def test_aggregate_single(self):
        agg = ScoreAggregator()
        results = [BenchmarkResult(task_id="t1", benchmark_name="test", score=0.8)]
        tasks = [BenchmarkTask(id="t1", name="test", category="general")]
        card = agg.aggregate(results, tasks)
        assert card.overall_score == 0.8

    def test_aggregate_multiple(self):
        agg = ScoreAggregator()
        results = [
            BenchmarkResult(task_id="t1", benchmark_name="test1", score=0.8),
            BenchmarkResult(task_id="t2", benchmark_name="test2", score=0.6),
        ]
        tasks = [
            BenchmarkTask(id="t1", name="test1", category="general"),
            BenchmarkTask(id="t2", name="test2", category="general"),
        ]
        card = agg.aggregate(results, tasks)
        assert card.overall_score == 0.7

    def test_aggregate_weighted(self):
        agg = ScoreAggregator()
        results = [
            BenchmarkResult(task_id="t1", benchmark_name="test1", score=0.8),
            BenchmarkResult(task_id="t2", benchmark_name="test2", score=0.6),
        ]
        tasks = [
            BenchmarkTask(id="t1", name="test1", category="general", weight=2.0),
            BenchmarkTask(id="t2", name="test2", category="general", weight=1.0),
        ]
        card = agg.aggregate(results, tasks)
        # (0.8*2 + 0.6*1) / 3 = 0.733
        assert abs(card.overall_score - 0.733) < 0.01

    def test_compute_trend(self):
        agg = ScoreAggregator()
        cards = [
            Scorecard(id="", timestamp=1, overall_score=0.5, category_scores={}, benchmark_results=[]),
            Scorecard(id="", timestamp=2, overall_score=0.7, category_scores={}, benchmark_results=[]),
        ]
        trend = agg.compute_trend(cards)
        assert trend["overall_trend"] == pytest.approx(0.2)

    def test_compare_scorecards(self):
        agg = ScoreAggregator()
        base = Scorecard(id="", timestamp=1, overall_score=0.5, category_scores={"a": 0.5}, benchmark_results=[])
        curr = Scorecard(id="", timestamp=2, overall_score=0.7, category_scores={"a": 0.8}, benchmark_results=[])
        deltas = agg.compare_scorecards(base, curr)
        assert deltas["overall_delta"] == pytest.approx(0.2)
        assert deltas["category_deltas"]["a"] == pytest.approx(0.3)


# ─────────────────── ImprovementPlanner Tests ──────────────────────────


class TestImprovementPlanner:
    def test_create(self):
        planner = ImprovementPlanner()
        assert planner is not None

    def test_plan_improvements(self):
        planner = ImprovementPlanner()
        card = Scorecard(
            id="", timestamp=0, overall_score=0.5,
            category_scores={"accuracy": 0.4, "speed": 0.9},
            benchmark_results=[],
        )
        plans = planner.plan_improvements(card, target_score=0.8)
        assert len(plans) >= 1
        assert any(p.target_benchmark == "accuracy" for p in plans)

    def test_plan_improvements_all_good(self):
        planner = ImprovementPlanner()
        card = Scorecard(
            id="", timestamp=0, overall_score=0.95,
            category_scores={"accuracy": 0.95},
            benchmark_results=[],
        )
        plans = planner.plan_improvements(card, target_score=0.9)
        assert len(plans) == 0

    def test_prioritize_plans(self):
        planner = ImprovementPlanner()
        plans = [
            ImprovementPlan(id="", target_benchmark="a", current_score=0.5, target_score=0.9, strategies=[], priority=1),
            ImprovementPlan(id="", target_benchmark="b", current_score=0.3, target_score=0.9, strategies=[], priority=5),
        ]
        prioritized = planner.prioritize_plans(plans)
        assert prioritized[0].priority == 5

    def test_register_strategy(self):
        planner = ImprovementPlanner()
        planner.register_strategy("new_cat", "new_strategy")
        assert "new_strategy" in planner._strategies["new_cat"]


# ────────────────────── DailyCycle Tests ───────────────────────────────


class TestDailyCycle:
    def test_create(self):
        cycle = DailyCycle(
            BenchmarkOrchestrator(),
            ScoreAggregator(),
            ImprovementPlanner(),
        )
        assert cycle.cycle_number == 0

    def test_run_cycle(self):
        async def run():
            orch = BenchmarkOrchestrator()
            orch.add_task(BenchmarkTask(id="t1", name="test", category="general"))
            cycle = DailyCycle(orch, ScoreAggregator(), ImprovementPlanner())

            async def predictor(task):
                return {"score": 0.85}

            report = await cycle.run_cycle(predictor)
            assert isinstance(report, DailyReport)
            assert cycle.cycle_number == 1
        async_run(run())

    def test_multiple_cycles(self):
        async def run():
            orch = BenchmarkOrchestrator()
            orch.add_task(BenchmarkTask(id="t1", name="test", category="general"))
            cycle = DailyCycle(orch, ScoreAggregator(), ImprovementPlanner())

            async def predictor(task):
                return {"score": 0.85}

            await cycle.run_cycle(predictor)
            await cycle.run_cycle(predictor)
            assert cycle.cycle_number == 2
            assert len(cycle.scorecard_history) == 2
        async_run(run())

    def test_get_progress_summary(self):
        async def run():
            orch = BenchmarkOrchestrator()
            orch.add_task(BenchmarkTask(id="t1", name="test", category="general"))
            cycle = DailyCycle(orch, ScoreAggregator(), ImprovementPlanner())

            async def predictor(task):
                return {"score": 0.85}

            await cycle.run_cycle(predictor)
            summary = cycle.get_progress_summary()
            assert summary["cycles"] == 1
            assert summary["latest_score"] == 0.85
        async_run(run())


# ──────────────────── ReportGenerator Tests ────────────────────────────


class TestReportGenerator:
    def test_create(self):
        gen = ReportGenerator()
        assert gen is not None

    def test_generate_daily_report(self):
        gen = ReportGenerator()
        report = DailyReport(
            id="r1", date="2024-01-15", cycle_number=1,
            scorecards=[Scorecard(
                id="", timestamp=0, overall_score=0.75,
                category_scores={"general": 0.8}, benchmark_results=[],
            )],
            improvements_attempted=3, improvements_succeeded=2,
            key_findings=["Good progress"], recommendations=["Keep going"],
        )
        md = gen.generate_daily_report(report)
        assert "# Daily Report" in md
        assert "0.75" in md

    def test_generate_progress_report(self):
        gen = ReportGenerator()
        history = [
            Scorecard(id="", timestamp=1, overall_score=0.5, category_scores={}, benchmark_results=[]),
            Scorecard(id="", timestamp=2, overall_score=0.7, category_scores={}, benchmark_results=[]),
        ]
        md = gen.generate_progress_report(history)
        assert "# Progress Report" in md
        assert "0.5" in md
        assert "0.7" in md

    def test_generate_improvement_report(self):
        gen = ReportGenerator()
        plans = [
            ImprovementPlan(id="", target_benchmark="accuracy", current_score=0.5, target_score=0.9, strategies=["s1", "s2"]),
        ]
        md = gen.generate_improvement_report(plans)
        assert "# Improvement Plan" in md
        assert "accuracy" in md

    def test_export_json(self):
        gen = ReportGenerator()
        report = DailyReport(
            id="r1", date="2024-01-15", cycle_number=1,
            scorecards=[], improvements_attempted=0, improvements_succeeded=0,
            key_findings=[], recommendations=[],
        )
        j = gen.export_json(report)
        data = json.loads(j)
        assert data["cycle_number"] == 1

    def test_save_report(self):
        gen = ReportGenerator()
        report = DailyReport(
            id="r1", date="2024-01-15", cycle_number=1,
            scorecards=[], improvements_attempted=0, improvements_succeeded=0,
            key_findings=[], recommendations=[],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.save_report(report, output_dir=tmpdir)
            assert os.path.exists(path)
            assert path.endswith(".md")
