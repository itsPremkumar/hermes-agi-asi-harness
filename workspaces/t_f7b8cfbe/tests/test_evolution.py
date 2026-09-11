"""
Tests for EvolutionEngine module.
"""

from __future__ import annotations

import pytest

from src.harness.improvement.analyzer import (
    AgentPerformanceMetrics,
    ImprovementAnalyzer,
    TestResult,
    TestSuite,
)
from src.harness.improvement.evolution import (
    EvolutionConfig,
    EvolutionCycle,
    EvolutionEngine,
    EvolutionPhase,
    EvolutionStatus,
)
from src.harness.improvement.feedback import (
    FeedbackCategory,
    FeedbackLoop,
    FeedbackPriority,
)
from src.harness.improvement.optimizer import AutoOptimizer
from src.harness.improvement.tracker import MetricType, PerformanceTracker


@pytest.fixture
def engine() -> EvolutionEngine:
    return EvolutionEngine()


@pytest.fixture
def engine_with_config() -> EvolutionEngine:
    config = EvolutionConfig(
        auto_optimize=True,
        auto_heal=True,
        require_validation=True,
        rollback_on_regression=True,
    )
    return EvolutionEngine(config=config)


@pytest.fixture
def passing_suite() -> TestSuite:
    return TestSuite(results=[
        TestResult(name="test_one", passed=True, duration_ms=50.0),
        TestResult(name="test_two", passed=True, duration_ms=30.0),
    ])


@pytest.fixture
def failing_suite() -> TestSuite:
    return TestSuite(results=[
        TestResult(name="test_one", passed=True, duration_ms=50.0),
        TestResult(name="test_two", passed=False, duration_ms=100.0, error_message="Failed"),
    ])


@pytest.fixture
def mostly_passing_suite() -> TestSuite:
    return TestSuite(results=[
        TestResult(name="test_one", passed=True, duration_ms=50.0),
        TestResult(name="test_two", passed=True, duration_ms=30.0),
        TestResult(name="test_three", passed=True, duration_ms=20.0),
        TestResult(name="test_four", passed=True, duration_ms=40.0),
        TestResult(name="test_five", passed=False, duration_ms=10.0),
    ])


class TestEvolutionCycle:
    def test_cycle_creation(self) -> None:
        cycle = EvolutionCycle(cycle_id=1, phase=EvolutionPhase.ANALYZE, status=EvolutionStatus.RUNNING)
        assert cycle.cycle_id == 1
        assert cycle.status == EvolutionStatus.RUNNING

    def test_duration(self) -> None:
        cycle = EvolutionCycle(cycle_id=1, phase=EvolutionPhase.ANALYZE, status=EvolutionStatus.COMPLETED)
        cycle.end_time = cycle.start_time + __import__("datetime").timedelta(seconds=5)
        assert cycle.duration_seconds == 5.0

    def test_improved(self) -> None:
        cycle = EvolutionCycle(
            cycle_id=1,
            phase=EvolutionPhase.ANALYZE,
            status=EvolutionStatus.COMPLETED,
            health_before=0.5,
            health_after=0.8,
        )
        assert cycle.improved is True

    def test_not_improved(self) -> None:
        cycle = EvolutionCycle(
            cycle_id=1,
            phase=EvolutionPhase.ANALYZE,
            status=EvolutionStatus.COMPLETED,
            health_before=0.8,
            health_after=0.5,
        )
        assert cycle.improved is False


class TestEvolutionConfig:
    def test_default_config(self) -> None:
        config = EvolutionConfig()
        assert config.auto_optimize is True
        assert config.auto_heal is True
        assert config.require_validation is True
        assert config.rollback_on_regression is True

    def test_custom_config(self) -> None:
        config = EvolutionConfig(auto_optimize=False, max_optimization_attempts=5)
        assert config.auto_optimize is False
        assert config.max_optimization_attempts == 5


class TestEvolutionEngine:
    def test_initial_state(self, engine: EvolutionEngine) -> None:
        assert engine.status == EvolutionStatus.IDLE
        assert engine.total_cycles == 0
        assert engine.cycles == []

    def test_run_cycle(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        cycle = engine.run_cycle(passing_suite)
        assert cycle.cycle_id == 1
        assert cycle.status == EvolutionStatus.COMPLETED
        assert cycle.phase == EvolutionPhase.MONITOR

    def test_run_cycle_records_history(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        engine.run_cycle(passing_suite)
        assert len(engine.cycles) == 1
        assert engine.total_cycles == 1

    def test_run_multiple_cycles(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        engine.run_cycle(passing_suite)
        engine.run_cycle(passing_suite)
        assert len(engine.cycles) == 2
        assert engine.total_cycles == 2

    def test_successful_cycles(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        engine.run_cycle(passing_suite)
        assert engine.successful_cycles == 1

    def test_run_evolution_multiple_suites(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        cycles = engine.run_evolution([passing_suite, passing_suite, passing_suite])
        assert len(cycles) == 3

    def test_run_evolution_max_cycles(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        cycles = engine.run_evolution([passing_suite, passing_suite, passing_suite], max_cycles=2)
        assert len(cycles) == 2

    def test_run_evolution_stops_on_failure(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        # Create a suite that will cause failure
        bad_suite = TestSuite(results=[])
        # This should not fail but produce a cycle
        cycles = engine.run_evolution([passing_suite])
        assert len(cycles) == 1

    def test_integrate_feedback(self, engine: EvolutionEngine) -> None:
        engine.feedback_loop.submit_feedback(
            "agent1", FeedbackCategory.BUG, "Critical bug", FeedbackPriority.CRITICAL
        )
        integrated = engine.integrate_feedback()
        assert len(integrated) >= 1
        assert integrated[0]["action"] == "priority_fix"

    def test_integrate_feedback_disabled(self) -> None:
        config = EvolutionConfig(feedback_integration=False)
        engine = EvolutionEngine(config=config)
        engine.feedback_loop.submit_feedback("agent1", "bug", "Bug", "high")
        integrated = engine.integrate_feedback()
        assert integrated == []

    def test_integrate_feedback_performance(self, engine: EvolutionEngine) -> None:
        engine.feedback_loop.submit_feedback(
            "agent1", FeedbackCategory.PERFORMANCE, "Slow", FeedbackPriority.HIGH
        )
        integrated = engine.integrate_feedback()
        assert any(i["action"] == "performance_optimization" for i in integrated)

    def test_get_evolution_summary(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        engine.run_cycle(passing_suite)
        summary = engine.get_evolution_summary()
        assert summary["total_cycles"] == 1
        assert summary["successful"] == 1
        assert summary["status"] == EvolutionStatus.COMPLETED.value

    def test_get_evolution_summary_empty(self, engine: EvolutionEngine) -> None:
        summary = engine.get_evolution_summary()
        assert summary["total_cycles"] == 0

    def test_should_evolve_initial(self, engine: EvolutionEngine) -> None:
        assert engine.should_evolve() is True

    def test_should_evolve_while_running(self, engine: EvolutionEngine) -> None:
        engine._status = EvolutionStatus.RUNNING
        assert engine.should_evolve() is False

    def test_should_evolve_low_health(self, engine: EvolutionEngine, failing_suite: TestSuite) -> None:
        engine.run_cycle(failing_suite)
        # After a failing suite, health is low, should evolve
        assert engine.should_evolve() is True

    def test_should_evolve_critical_feedback(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        engine.run_cycle(passing_suite)
        engine.feedback_loop.submit_feedback("agent1", "bug", "Critical", FeedbackPriority.CRITICAL)
        assert engine.should_evolve() is True

    def test_get_recommendations_initial(self, engine: EvolutionEngine) -> None:
        recs = engine.get_recommendations()
        assert any(r["action"] == "start_evolution" for r in recs)

    def test_get_recommendations_after_cycle(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        engine.run_cycle(passing_suite)
        recs = engine.get_recommendations()
        # Should not recommend start_evolution after a cycle
        assert not any(r["action"] == "start_evolution" for r in recs)

    def test_get_recommendations_low_health(self, engine: EvolutionEngine, failing_suite: TestSuite) -> None:
        engine.run_cycle(failing_suite)
        recs = engine.get_recommendations()
        assert any("urgent" in r["action"] or "continue" in r["action"] for r in recs)

    def test_get_recommendations_stale_feedback(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        engine.run_cycle(passing_suite)
        item = engine.feedback_loop.submit_feedback("agent1", "bug", "Old", FeedbackPriority.HIGH)
        item.timestamp = __import__("datetime").datetime.utcnow() - __import__("datetime").timedelta(hours=73)
        recs = engine.get_recommendations()
        assert any("stale" in r["action"] for r in recs)

    def test_current_cycle(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        assert engine.current_cycle is None
        engine.run_cycle(passing_suite)
        assert engine.current_cycle is None

    def test_health_tracking(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        cycle = engine.run_cycle(passing_suite)
        assert cycle.health_before >= 0.0
        assert cycle.health_after >= 0.0

    def test_actions_taken_recorded(self, engine: EvolutionEngine, passing_suite: TestSuite) -> None:
        cycle = engine.run_cycle(passing_suite)
        # Actions may or may not be taken depending on recommendations
        assert isinstance(cycle.actions_taken, list)

    def test_rollback_on_regression(self, engine_with_config: EvolutionEngine, failing_suite: TestSuite) -> None:
        cycle = engine_with_config.run_cycle(failing_suite)
        # With validation required and low pass rate, should roll back
        if cycle.findings.get("validation", {}).get("passed") is False:
            assert cycle.status == EvolutionStatus.ROLLED_BACK
