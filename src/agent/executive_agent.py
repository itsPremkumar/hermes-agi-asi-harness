"""
Executive Agent — Coordinates benchmarking, scoring, improvement planning,
daily reporting, and continuous self-improvement cycles.
"""

from __future__ import annotations
import asyncio
import enum
import json
import logging
import statistics
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


# ──────────────────────────── Domain Models ────────────────────────────


@dataclass
class BenchmarkTask:
    id: str
    name: str
    category: str
    weight: float = 1.0
    timeout: float = 300.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]


@dataclass
class BenchmarkResult:
    task_id: str
    benchmark_name: str
    score: float
    raw_output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class Scorecard:
    """Aggregated score across multiple benchmarks."""
    id: str
    timestamp: float
    overall_score: float
    category_scores: dict[str, float]
    benchmark_results: list[BenchmarkResult]
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "overall_score": self.overall_score,
            "category_scores": self.category_scores,
            "benchmark_count": len(self.benchmark_results),
        }


@dataclass
class ImprovementPlan:
    id: str
    target_benchmark: str
    current_score: float
    target_score: float
    strategies: list[str]
    priority: int = 0
    estimated_effort: str = "medium"
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]


@dataclass
class DailyReport:
    id: str
    date: str
    cycle_number: int
    scorecards: list[Scorecard]
    improvements_attempted: int
    improvements_succeeded: int
    key_findings: list[str]
    recommendations: list[str]
    generated_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "cycle_number": self.cycle_number,
            "scorecards": [s.to_dict() for s in self.scorecards],
            "improvements_attempted": self.improvements_attempted,
            "improvements_succeeded": self.improvements_succeeded,
            "key_findings": self.key_findings,
            "recommendations": self.recommendations,
        }


# ──────────────────── 1. BenchmarkOrchestrator ────────────────────────


class BenchmarkOrchestrator:
    """Coordinates running multiple benchmarks across categories."""

    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self._benchmarks: dict[str, Callable] = {}
        self._tasks: list[BenchmarkTask] = []
        self._results: list[BenchmarkResult] = []

    def register_benchmark(
        self,
        name: str,
        func: Callable[..., Awaitable[dict]],
        category: str = "general",
        weight: float = 1.0,
    ):
        """Register a benchmark function."""
        self._benchmarks[name] = func

    def add_task(self, task: BenchmarkTask):
        """Add a benchmark task to the queue."""
        self._tasks.append(task)

    async def run_all(
        self,
        predictor: Callable[[BenchmarkTask], Awaitable[Any]],
    ) -> list[BenchmarkResult]:
        """Run all benchmark tasks with concurrency control."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_one(task: BenchmarkTask) -> BenchmarkResult:
            async with semaphore:
                return await self._run_single(task, predictor)

        self._results = await asyncio.gather(*[run_one(t) for t in self._tasks])
        return list(self._results)

    async def run_category(
        self,
        category: str,
        predictor: Callable[[BenchmarkTask], Awaitable[Any]],
    ) -> list[BenchmarkResult]:
        """Run benchmarks for a specific category."""
        tasks = [t for t in self._tasks if t.category == category]
        results = []
        for task in tasks:
            result = await self._run_single(task, predictor)
            results.append(result)
        return results

    async def _run_single(
        self,
        task: BenchmarkTask,
        predictor: Callable[[BenchmarkTask], Awaitable[Any]],
    ) -> BenchmarkResult:
        """Run a single benchmark task."""
        started = time.time()
        try:
            output = await asyncio.wait_for(predictor(task), timeout=task.timeout)
            duration = time.time() - started
            score = self._extract_score(output)
            return BenchmarkResult(
                task_id=task.id,
                benchmark_name=task.name,
                score=score,
                raw_output=output,
                duration=duration,
            )
        except asyncio.TimeoutError:
            return BenchmarkResult(
                task_id=task.id,
                benchmark_name=task.name,
                score=0.0,
                error=f"Timeout after {task.timeout}s",
                duration=time.time() - started,
            )
        except Exception as e:
            return BenchmarkResult(
                task_id=task.id,
                benchmark_name=task.name,
                score=0.0,
                error=str(e),
                duration=time.time() - started,
            )

    @staticmethod
    def _extract_score(output: Any) -> float:
        """Extract a numeric score from benchmark output."""
        if isinstance(output, (int, float)):
            return float(output)
        if isinstance(output, dict):
            return float(output.get("score", output.get("accuracy", 0.0)))
        return 0.0

    def get_results(self) -> list[BenchmarkResult]:
        """Get all benchmark results."""
        return list(self._results)


# ────────────────────── 2. ScoreAggregator ─────────────────────────────


class ScoreAggregator:
    """Aggregates benchmark results into scorecards."""

    def aggregate(
        self,
        results: list[BenchmarkResult],
        tasks: list[BenchmarkTask],
    ) -> Scorecard:
        """Aggregate results into a scorecard."""
        if not results:
            return Scorecard(
                id="",
                timestamp=time.time(),
                overall_score=0.0,
                category_scores={},
                benchmark_results=[],
            )

        # Build task weight map
        weight_map = {t.name: t.weight for t in tasks}
        category_map = {t.name: t.category for t in tasks}

        # Compute weighted overall score
        total_weight = 0.0
        weighted_sum = 0.0
        category_scores: dict[str, list[float]] = defaultdict(list)

        for result in results:
            if not result.success:
                continue
            weight = weight_map.get(result.benchmark_name, 1.0)
            weighted_sum += result.score * weight
            total_weight += weight

            category = category_map.get(result.benchmark_name, "general")
            category_scores[category].append(result.score)

        overall = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Compute per-category averages
        category_averages = {}
        for cat, scores in category_scores.items():
            category_averages[cat] = statistics.mean(scores) if scores else 0.0

        return Scorecard(
            id="",
            timestamp=time.time(),
            overall_score=overall,
            category_scores=category_averages,
            benchmark_results=results,
        )

    def compute_trend(
        self,
        scorecards: list[Scorecard],
    ) -> dict[str, float]:
        """Compute score trends across scorecards."""
        if len(scorecards) < 2:
            return {"overall_trend": 0.0}

        # Sort by timestamp
        sorted_cards = sorted(scorecards, key=lambda s: s.timestamp)
        first = sorted_cards[0]
        last = sorted_cards[-1]

        # Overall trend
        overall_trend = last.overall_score - first.overall_score

        # Per-category trends
        trends = {"overall_trend": overall_trend}
        all_categories = set()
        for card in sorted_cards:
            all_categories.update(card.category_scores.keys())

        for cat in all_categories:
            first_score = first.category_scores.get(cat, 0.0)
            last_score = last.category_scores.get(cat, 0.0)
            trends[f"{cat}_trend"] = last_score - first_score

        return trends

    def compare_scorecards(
        self,
        baseline: Scorecard,
        current: Scorecard,
    ) -> dict[str, Any]:
        """Compare two scorecards and return deltas."""
        deltas = {
            "overall_delta": current.overall_score - baseline.overall_score,
            "category_deltas": {},
        }

        all_categories = set(baseline.category_scores.keys()) | set(
            current.category_scores.keys()
        )
        for cat in all_categories:
            base = baseline.category_scores.get(cat, 0.0)
            curr = current.category_scores.get(cat, 0.0)
            deltas["category_deltas"][cat] = curr - base

        return deltas


# ────────────────────── 3. ImprovementPlanner ──────────────────────────


class ImprovementPlanner:
    """Plans improvements based on scorecard analysis."""

    def __init__(self):
        self._strategies: dict[str, list[str]] = {
            "general": [
                "increase_reasoning_depth",
                "add_few_shot_examples",
                "improve_prompt_clarity",
                "add_error_handling",
            ],
            "accuracy": [
                "add_verification_steps",
                "use_ensemble_methods",
                "increase_computation",
                "add_self_consistency",
            ],
            "speed": [
                "optimize_prompt_length",
                "use_caching",
                "parallelize_subtasks",
                "reduce_round_trips",
            ],
            "robustness": [
                "add_edge_case_handling",
                "improve_input_validation",
                "add_fallback_strategies",
                "increase_diversity",
            ],
        }

    def plan_improvements(
        self,
        scorecard: Scorecard,
        target_score: float = 0.95,
    ) -> list[ImprovementPlan]:
        """Generate improvement plans for underperforming areas."""
        plans = []

        for category, score in scorecard.category_scores.items():
            if score < target_score:
                gap = target_score - score
                strategies = self._strategies.get(
                    category, self._strategies["general"]
                )

                plan = ImprovementPlan(
                    id="",
                    target_benchmark=category,
                    current_score=score,
                    target_score=target_score,
                    strategies=strategies[:3],  # Top 3 strategies
                    priority=int(gap * 10),
                    estimated_effort="high" if gap > 0.3 else "medium",
                )
                plans.append(plan)

        # Sort by priority (highest first)
        plans.sort(key=lambda p: p.priority, reverse=True)
        return plans

    def prioritize_plans(
        self,
        plans: list[ImprovementPlan],
    ) -> list[ImprovementPlan]:
        """Prioritize improvement plans."""
        return sorted(plans, key=lambda p: p.priority, reverse=True)

    def register_strategy(self, category: str, strategy: str):
        """Register a new improvement strategy."""
        if category not in self._strategies:
            self._strategies[category] = []
        self._strategies[category].append(strategy)


# ───────────────────────── 4. DailyCycle ──────────────────────────────


class DailyCycle:
    """Manages the daily improvement cycle."""

    def __init__(
        self,
        orchestrator: BenchmarkOrchestrator,
        aggregator: ScoreAggregator,
        planner: ImprovementPlanner,
    ):
        self.orchestrator = orchestrator
        self.aggregator = aggregator
        self.planner = planner
        self._cycle_number = 0
        self._scorecard_history: list[Scorecard] = []
        self._reports: list[DailyReport] = []

    @property
    def cycle_number(self) -> int:
        return self._cycle_number

    @property
    def scorecard_history(self) -> list[Scorecard]:
        return list(self._scorecard_history)

    async def run_cycle(
        self,
        predictor: Callable[[BenchmarkTask], Awaitable[Any]],
    ) -> DailyReport:
        """Run a full daily improvement cycle."""
        self._cycle_number += 1
        logger.info(f"Starting daily cycle {self._cycle_number}")

        # Step 1: Run benchmarks
        results = await self.orchestrator.run_all(predictor)

        # Step 2: Aggregate scores
        scorecard = self.aggregator.aggregate(
            results, self.orchestrator._tasks
        )
        self._scorecard_history.append(scorecard)

        # Step 3: Plan improvements
        plans = self.planner.plan_improvements(scorecard)

        # Step 4: Generate report
        report = self._generate_cycle_report(scorecard, plans)
        self._reports.append(report)

        return report

    def _generate_cycle_report(
        self,
        scorecard: Scorecard,
        plans: list[ImprovementPlan],
    ) -> DailyReport:
        """Generate a report for this cycle."""
        findings = []
        recommendations = []

        # Analyze scorecard
        if scorecard.overall_score > 0.8:
            findings.append(f"Strong overall performance: {scorecard.overall_score:.2f}")
        elif scorecard.overall_score < 0.5:
            findings.append(f"Low overall performance: {scorecard.overall_score:.2f}")
            recommendations.append("Focus on fundamental improvements")

        # Analyze categories
        for cat, score in scorecard.category_scores.items():
            if score < 0.6:
                findings.append(f"Category {cat} underperforming: {score:.2f}")
                recommendations.append(f"Prioritize {cat} improvements")

        # Analyze trends
        if len(self._scorecard_history) >= 2:
            trends = self.aggregator.compute_trend(self._scorecard_history)
            if trends.get("overall_trend", 0) > 0:
                findings.append("Positive trend detected")
            elif trends.get("overall_trend", 0) < 0:
                findings.append("Negative trend detected")
                recommendations.append("Investigate regression causes")

        return DailyReport(
            id="",
            date=datetime.now().strftime("%Y-%m-%d"),
            cycle_number=self._cycle_number,
            scorecards=[scorecard],
            improvements_attempted=len(plans),
            improvements_succeeded=0,  # Updated after execution
            key_findings=findings,
            recommendations=recommendations,
        )


# ───────────────────────── 5. ExecutiveAgent ─────────────────────────


class ExecutiveAgent:
    """Top-level agent that coordinates all benchmark solving and improvement."""

    def __init__(self, max_concurrent: int = 4) -> None:
        self.orchestrator = BenchmarkOrchestrator(max_concurrent=max_concurrent)
        self.aggregator = ScoreAggregator()
        self.planner = ImprovementPlanner()
        self.daily_cycle = DailyCycle(self.orchestrator, self.aggregator, self.planner)
        self._benchmarks: dict[str, Any] = {}

    def register_benchmark(
        self,
        name: str,
        func: Callable[..., Awaitable[dict]],
        category: str = "general",
        weight: float = 1.0,
    ) -> None:
        """Register a benchmark function."""
        self.orchestrator.register_benchmark(name, func, category, weight)

    def add_task(self, task: BenchmarkTask) -> None:
        """Add a benchmark task."""
        self.orchestrator.add_task(task)

    def get_benchmark(self, name: str) -> Any:
        """Get a registered benchmark."""
        return self._benchmarks.get(name)

    def list_benchmarks(self) -> list[str]:
        """List all registered benchmark names."""
        return list(self.orchestrator._benchmarks.keys())

    def get_results(self) -> list[BenchmarkResult]:
        """Get all benchmark results."""
        return self.orchestrator.get_results()

    def get_scorecard_history(self) -> list[Scorecard]:
        """Get scorecard history."""
        return self.daily_cycle.scorecard_history

    @property
    def cycle_number(self) -> int:
        """Get current cycle number."""
        return self.daily_cycle.cycle_number

    def get_progress_summary(self) -> dict:
        """Get summary of progress across all cycles."""
        if not self._scorecard_history:
            return {"cycles": 0}

        scores = [s.overall_score for s in self._scorecard_history]
        return {
            "cycles": self._cycle_number,
            "latest_score": scores[-1],
            "best_score": max(scores),
            "worst_score": min(scores),
            "average_score": statistics.mean(scores),
            "score_trend": scores[-1] - scores[0] if len(scores) > 1 else 0.0,
        }


# ────────────────────── 5. ReportGenerator ────────────────────────────


class ReportGenerator:
    """Generates human-readable reports from daily cycles."""

    def generate_daily_report(self, report: DailyReport) -> str:
        """Generate a markdown daily report."""
        lines = [
            f"# Daily Report — Cycle {report.cycle_number}",
            f"**Date:** {report.date}",
            f"**Generated:** {datetime.fromtimestamp(report.generated_at).strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
        ]
        if report.scorecards:
            lines.extend([
                f"- **Overall Score:** {report.scorecards[-1].overall_score:.4f}",
                f"- **Benchmarks Run:** {len(report.scorecards[-1].benchmark_results)}",
            ])
        lines.extend([
            f"- **Improvements Attempted:** {report.improvements_attempted}",
            f"- **Improvements Succeeded:** {report.improvements_succeeded}",
            "",
            "## Category Scores",
        ])

        if report.scorecards:
            for cat, score in report.scorecards[-1].category_scores.items():
                bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
                lines.append(f"- **{cat}:** {bar} {score:.4f}")

        lines.extend([
            "",
            "## Key Findings",
        ])
        for finding in report.key_findings:
            lines.append(f"- {finding}")

        lines.extend([
            "",
            "## Recommendations",
        ])
        for rec in report.recommendations:
            lines.append(f"- {rec}")

        return "\n".join(lines)

    def generate_progress_report(
        self,
        history: list[Scorecard],
    ) -> str:
        """Generate a progress report across multiple cycles."""
        if not history:
            return "# Progress Report\n\nNo data available."

        scores = [s.overall_score for s in history]
        best = max(scores)
        worst = min(scores)
        avg = statistics.mean(scores)

        lines = [
            "# Progress Report",
            "",
            f"**Cycles Completed:** {len(history)}",
            f"**Best Score:** {best:.4f}",
            f"**Worst Score:** {worst:.4f}",
            f"**Average Score:** {avg:.4f}",
            f"**Current Score:** {scores[-1]:.4f}",
            "",
            "## Score History",
            "",
            "| Cycle | Score | Change |",
            "|-------|-------|--------|",
        ]

        for i, score in enumerate(scores):
            change = ""
            if i > 0:
                delta = score - scores[i - 1]
                change = f"{delta:+.4f}"
            lines.append(f"| {i + 1} | {score:.4f} | {change} |")

        return "\n".join(lines)

    def generate_improvement_report(
        self,
        plans: list[ImprovementPlan],
    ) -> str:
        """Generate an improvement plan report."""
        lines = [
            "# Improvement Plan",
            "",
            f"**Total Plans:** {len(plans)}",
            "",
            "## Prioritized Improvements",
            "",
            "| Priority | Target | Current | Target Score | Strategies |",
            "|----------|--------|---------|--------------|------------|",
        ]

        for plan in plans:
            strategies_str = ", ".join(plan.strategies[:2]) + "..."
            lines.append(
                f"| {plan.priority} | {plan.target_benchmark} | "
                f"{plan.current_score:.4f} | {plan.target_score:.4f} | "
                f"{strategies_str} |"
            )

        return "\n".join(lines)

    def export_json(self, report: DailyReport) -> str:
        """Export report as JSON."""
        return json.dumps(report.to_dict(), indent=2)

    def save_report(self, report: DailyReport, output_dir: str = "./reports") -> str:
        """Save report to file."""
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)

        filename = f"daily_report_{report.date}_cycle_{report.cycle_number}.md"
        filepath = path / filename

        content = self.generate_daily_report(report)
        filepath.write_text(content)

        return str(filepath)
