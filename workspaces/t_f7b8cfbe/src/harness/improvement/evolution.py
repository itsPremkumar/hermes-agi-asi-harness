"""
EvolutionEngine — Drive the harness through continuous evolution cycles.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .analyzer import (
    AgentPerformanceMetrics,
    AnalysisReport,
    ImprovementAnalyzer,
    TestSuite,
)
from .feedback import FeedbackCategory, FeedbackLoop, FeedbackPriority
from .optimizer import AutoOptimizer, OptimizationPlan
from .tracker import MetricType, PerformanceTracker


class EvolutionPhase(str, Enum):
    ANALYZE = "analyze"
    PLAN = "plan"
    OPTIMIZE = "optimize"
    VALIDATE = "validate"
    DEPLOY = "deploy"
    MONITOR = "monitor"


class EvolutionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class EvolutionCycle:
    """Record of a single evolution cycle."""

    cycle_id: int
    phase: EvolutionPhase
    status: EvolutionStatus
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    findings: dict[str, Any] = field(default_factory=dict)
    actions_taken: list[dict[str, Any]] = field(default_factory=list)
    health_before: float = 0.0
    health_after: float = 0.0
    error: str = ""

    @property
    def duration_seconds(self) -> float:
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()

    @property
    def improved(self) -> bool:
        return self.health_after > self.health_before


@dataclass
class EvolutionConfig:
    """Configuration for the evolution engine."""

    auto_optimize: bool = True
    auto_heal: bool = True
    require_validation: bool = True
    max_optimization_attempts: int = 3
    health_improvement_threshold: float = 0.01
    rollback_on_regression: bool = True
    min_cycles_before_deploy: int = 2
    feedback_integration: bool = True


class EvolutionEngine:
    """Drives the harness through continuous evolution cycles."""

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        analyzer: ImprovementAnalyzer | None = None,
        optimizer: AutoOptimizer | None = None,
        tracker: PerformanceTracker | None = None,
        feedback_loop: FeedbackLoop | None = None,
    ) -> None:
        self.config = config or EvolutionConfig()
        self.analyzer = analyzer or ImprovementAnalyzer()
        self.optimizer = optimizer or AutoOptimizer()
        self.tracker = tracker or PerformanceTracker()
        self.feedback_loop = feedback_loop or FeedbackLoop()

        self._cycles: list[EvolutionCycle] = []
        self._current_cycle: EvolutionCycle | None = None
        self._cycle_counter = 0
        self._status = EvolutionStatus.IDLE

    @property
    def status(self) -> EvolutionStatus:
        return self._status

    @property
    def cycles(self) -> list[EvolutionCycle]:
        return list(self._cycles)

    @property
    def current_cycle(self) -> EvolutionCycle | None:
        return self._current_cycle

    @property
    def total_cycles(self) -> int:
        return self._cycle_counter

    @property
    def successful_cycles(self) -> int:
        return sum(1 for c in self._cycles if c.status == EvolutionStatus.COMPLETED)

    @property
    def failed_cycles(self) -> int:
        return sum(1 for c in self._cycles if c.status == EvolutionStatus.FAILED)

    def _next_cycle_id(self) -> int:
        self._cycle_counter += 1
        return self._cycle_counter

    def run_cycle(self, test_suite: TestSuite | None = None) -> EvolutionCycle:
        """Run a complete evolution cycle."""
        cycle = EvolutionCycle(
            cycle_id=self._next_cycle_id(),
            phase=EvolutionPhase.ANALYZE,
            status=EvolutionStatus.RUNNING,
        )
        self._current_cycle = cycle
        self._status = EvolutionStatus.RUNNING

        try:
            # Phase 1: Analyze
            cycle.phase = EvolutionPhase.ANALYZE
            cycle.health_before = self.analyzer.compute_health_score(test_suite)
            if test_suite:
                self.analyzer.record_test_suite(test_suite)

            report = self.analyzer.generate_report(test_suite)
            cycle.findings["analysis"] = {
                "health_score": report.overall_health_score,
                "recommendations_count": len(report.recommendations),
                "recommendations": report.recommendations[:5],
            }

            # Phase 2: Plan
            cycle.phase = EvolutionPhase.PLAN
            plans = self._create_optimization_plans(report)
            cycle.findings["plans"] = len(plans)

            # Phase 3: Optimize
            cycle.phase = EvolutionPhase.OPTIMIZE
            if self.config.auto_optimize and plans:
                opt_results = self.optimizer.apply_optimizations(plans)
                cycle.actions_taken.extend([
                    {
                        "type": "optimization",
                        "file": r.file_path,
                        "success": r.success,
                        "optimizations": len(r.optimizations_applied),
                    }
                    for r in opt_results
                ])

            # Phase 4: Validate
            cycle.phase = EvolutionPhase.VALIDATE
            if self.config.require_validation and test_suite:
                validation = self._validate(test_suite)
                cycle.findings["validation"] = validation

                if not validation["passed"] and self.config.rollback_on_regression:
                    cycle.status = EvolutionStatus.ROLLED_BACK
                    cycle.end_time = datetime.utcnow()
                    self._cycles.append(cycle)
                    self._current_cycle = None
                    self._status = EvolutionStatus.ROLLED_BACK
                    return cycle

            # Phase 5: Deploy (record metrics)
            cycle.phase = EvolutionPhase.DEPLOY
            cycle.health_after = self.analyzer.compute_health_score(test_suite)
            self.tracker.record_metric(
                name="evolution_health_score",
                value=cycle.health_after,
                metric_type=MetricType.RELIABILITY,
                labels={"cycle": str(cycle.cycle_id)},
            )

            # Phase 6: Monitor
            cycle.phase = EvolutionPhase.MONITOR
            cycle.status = EvolutionStatus.COMPLETED
            cycle.end_time = datetime.utcnow()

        except Exception as e:
            cycle.status = EvolutionStatus.FAILED
            cycle.error = str(e)
            cycle.end_time = datetime.utcnow()

        self._cycles.append(cycle)
        self._current_cycle = None
        self._status = cycle.status
        return cycle

    def _create_optimization_plans(self, report: AnalysisReport) -> list[OptimizationPlan]:
        """Create optimization plans from analysis report."""
        plans: list[OptimizationPlan] = []

        for rec in report.recommendations:
            if rec.get("action") == "investigate_failures":
                plans.append(OptimizationPlan(
                    file_path="",
                    target_issues=[rec],
                    estimated_impact="high",
                    auto_applicable=False,
                ))
            elif rec.get("action") == "reduce_complexity":
                plans.append(OptimizationPlan(
                    file_path="",
                    target_issues=[rec],
                    estimated_impact="medium",
                    auto_applicable=False,
                ))
            elif rec.get("action") == "deduplicate":
                plans.append(OptimizationPlan(
                    file_path="",
                    target_issues=[rec],
                    estimated_impact="medium",
                    auto_applicable=True,
                ))

        return plans

    def _validate(self, test_suite: TestSuite) -> dict[str, Any]:
        """Validate that optimizations didn't break anything."""
        return {
            "passed": test_suite.pass_rate >= 0.8,
            "pass_rate": test_suite.pass_rate,
            "failures": test_suite.failed,
            "threshold": 0.8,
        }

    def run_evolution(
        self,
        test_suites: list[TestSuite],
        max_cycles: int | None = None,
    ) -> list[EvolutionCycle]:
        """Run multiple evolution cycles over a series of test suites."""
        cycles: list[EvolutionCycle] = []

        for i, suite in enumerate(test_suites):
            if max_cycles and i >= max_cycles:
                break

            cycle = self.run_cycle(suite)
            cycles.append(cycle)

            if cycle.status == EvolutionStatus.FAILED:
                break

        return cycles

    def integrate_feedback(self) -> list[dict[str, Any]]:
        """Integrate feedback from the feedback loop into the evolution process."""
        if not self.config.feedback_integration:
            return []

        actionable = self.feedback_loop.get_actionable_items()
        integrated: list[dict[str, Any]] = []

        for item in actionable:
            if item["priority"] == FeedbackPriority.CRITICAL.value:
                integrated.append({
                    "feedback_id": item["id"],
                    "action": "priority_fix",
                    "message": item["message"],
                })
            elif item["category"] == FeedbackCategory.PERFORMANCE.value:
                integrated.append({
                    "feedback_id": item["id"],
                    "action": "performance_optimization",
                    "message": item["message"],
                })
            elif item["category"] == FeedbackCategory.BUG.value:
                integrated.append({
                    "feedback_id": item["id"],
                    "action": "bug_fix",
                    "message": item["message"],
                })

        return integrated

    def get_evolution_summary(self) -> dict[str, Any]:
        """Get a summary of all evolution cycles."""
        if not self._cycles:
            return {
                "total_cycles": 0,
                "successful": 0,
                "failed": 0,
                "status": self._status.value,
            }

        health_scores = [
            c.health_after for c in self._cycles if c.health_after > 0
        ]
        durations = [c.duration_seconds for c in self._cycles]

        return {
            "total_cycles": self._cycle_counter,
            "successful": self.successful_cycles,
            "failed": self.failed_cycles,
            "status": self._status.value,
            "avg_health": statistics.mean(health_scores) if health_scores else 0.0,
            "latest_health": health_scores[-1] if health_scores else 0.0,
            "health_trend": "improving" if len(health_scores) >= 2 and health_scores[-1] > health_scores[0] else "stable",
            "avg_cycle_duration_s": statistics.mean(durations) if durations else 0.0,
            "total_improvements": sum(1 for c in self._cycles if c.improved),
            "total_actions": sum(len(c.actions_taken) for c in self._cycles),
        }

    def should_evolve(self) -> bool:
        """Determine if another evolution cycle should run."""
        if self._status == EvolutionStatus.RUNNING:
            return False

        if not self._cycles:
            return True

        last_cycle = self._cycles[-1]

        # Evolve if health is below threshold
        if last_cycle.health_after < 0.8:
            return True

        # Evolve if there are unresolved critical feedback
        critical = self.feedback_loop.get_critical_unresolved()
        if critical:
            return True

        # Evolve if there are actionable items
        actionable = self.feedback_loop.get_actionable_items()
        if actionable:
            return True

        return False

    def get_recommendations(self) -> list[dict[str, Any]]:
        """Get evolution recommendations based on current state."""
        recs: list[dict[str, Any]] = []

        if not self._cycles:
            recs.append({
                "action": "start_evolution",
                "message": "No evolution cycles have been run yet. Run an initial cycle.",
            })
            return recs

        last = self._cycles[-1]

        if last.health_after < 0.5:
            recs.append({
                "action": "urgent_improvement",
                "message": f"Health score is critically low ({last.health_after:.2f}). Immediate action required.",
            })
        elif last.health_after < 0.8:
            recs.append({
                "action": "continue_evolution",
                "message": f"Health score ({last.health_after:.2f}) is below target. Continue evolution cycles.",
            })

        if last.status == EvolutionStatus.FAILED:
            recs.append({
                "action": "investigate_failure",
                "message": f"Last cycle failed: {last.error}",
            })

        if last.status == EvolutionStatus.ROLLED_BACK:
            recs.append({
                "action": "review_optimization",
                "message": "Last cycle was rolled back due to regression. Review optimization strategy.",
            })

        stale_feedback = self.feedback_loop.get_stale_feedback(max_age_hours=72)
        if stale_feedback:
            recs.append({
                "action": "address_stale_feedback",
                "message": f"{len(stale_feedback)} feedback items are unresolved after 72 hours.",
            })

        return recs
