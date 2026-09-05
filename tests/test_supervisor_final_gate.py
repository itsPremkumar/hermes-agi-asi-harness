"""Tests for Final Gate and Multi-Scenario Verification."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supervisor.final_gate import (
    FinalDecision,
    FinalGateOrchestrator,
    WorkerCompletionState,
)
from core.supervisor.multi_scenario import (
    MultiScenarioVerifier,
    Scenario,
    ScenarioMatrix,
    ScenarioType,
)

# ---------------------------------------------------------------------------
# Final Gate tests
# ---------------------------------------------------------------------------

class TestFinalGateOrchestrator:
    def test_create_orchestrator(self):
        gate = FinalGateOrchestrator()
        assert gate is not None

    def test_verify_all_pass(self):
        gate = FinalGateOrchestrator()
        expected = {"key1": "value1", "key2": "value2"}
        actual = {"key1": "value1", "key2": "value2"}
        record = gate.verify("m1", {"version": "v1"}, expected, actual)
        assert record.final_decision == FinalDecision.VERIFIED_COMPLETE

    def test_verify_with_failures(self):
        gate = FinalGateOrchestrator()
        expected = {"key1": "value1", "key2": "value2"}
        actual = {"key1": "wrong", "key2": "value2"}
        record = gate.verify("m1", {"version": "v1"}, expected, actual)
        # With mismatches, verification will fail
        assert record.final_decision in (
            FinalDecision.IMPROVEMENT_REQUIRED,
            FinalDecision.REWORK_REQUIRED,
            FinalDecision.REDESIGN_REQUIRED,
            FinalDecision.ROLLBACK_REQUIRED,
        )

    def test_verify_empty_states(self):
        gate = FinalGateOrchestrator()
        record = gate.verify("m1", {"version": "v1"}, {}, {})
        assert record.final_decision is not None

    def test_scenario_coverage(self):
        gate = FinalGateOrchestrator()
        expected = {"key1": "value1"}
        actual = {"key1": "value1"}
        record = gate.verify("m1", {"version": "v1"}, expected, actual)
        assert record.scenario_coverage["total"] > 0

    def test_improvement_analysis(self):
        gate = FinalGateOrchestrator()
        expected = {"key1": "value1", "key2": "value2"}
        actual = {"key1": "wrong", "key2": "value2"}
        record = gate.verify("m1", {"version": "v1"}, expected, actual)
        assert record.improvement_analysis is not None

    def test_get_history(self):
        gate = FinalGateOrchestrator()
        gate.verify("m1", {"version": "v1"}, {"k": "v"}, {"k": "v"})
        history = gate.get_history()
        assert len(history) == 1

    def test_worker_completion_states(self):
        assert WorkerCompletionState.WORKER_CLAIMED_COMPLETE == "worker_claimed_complete"
        assert WorkerCompletionState.VERIFIED_COMPLETE == "verified_complete"
        assert WorkerCompletionState.VERIFICATION_FAILED == "verification_failed"


# ---------------------------------------------------------------------------
# Multi-Scenario Verifier tests
# ---------------------------------------------------------------------------

class TestMultiScenarioVerifier:
    def test_create_verifier(self):
        verifier = MultiScenarioVerifier()
        assert verifier is not None

    def test_run_all_passes(self):
        verifier = MultiScenarioVerifier()
        expected = {"key1": "value1"}
        actual = {"key1": "value1"}
        results = verifier.run_all_passes(expected, actual)
        assert len(results) == 12

    def test_register_custom_pass(self):
        verifier = MultiScenarioVerifier()
        verifier.register_pass("custom", lambda e, a: {"status": "pass"})
        results = verifier.run_all_passes({}, {})
        assert "custom" in results

    def test_generate_scenario_matrix(self):
        verifier = MultiScenarioVerifier()
        matrix = verifier.generate_scenario_matrix(["login", "signup"])
        assert len(matrix.scenarios) > 0

    def test_scenario_coverage(self):
        verifier = MultiScenarioVerifier()
        matrix = verifier.generate_scenario_matrix(["login"])
        coverage = matrix.get_coverage()
        assert "normal" in coverage
        assert "edge" in coverage

    def test_get_by_type(self):
        verifier = MultiScenarioVerifier()
        matrix = verifier.generate_scenario_matrix(["login"])
        normal_scenarios = matrix.get_by_type(ScenarioType.NORMAL)
        assert len(normal_scenarios) > 0


# ---------------------------------------------------------------------------
# Scenario Matrix tests
# ---------------------------------------------------------------------------

class TestScenarioMatrix:
    def test_create_matrix(self):
        matrix = ScenarioMatrix()
        assert matrix is not None

    def test_add_scenario(self):
        matrix = ScenarioMatrix()
        scenario = Scenario(name="test", scenario_type=ScenarioType.NORMAL)
        matrix.add_scenario(scenario)
        assert len(matrix.scenarios) == 1

    def test_get_results(self):
        matrix = ScenarioMatrix()
        matrix.add_scenario(Scenario(name="s1", passed=True))
        matrix.add_scenario(Scenario(name="s2", passed=False))
        results = matrix.get_results()
        assert results["total"] == 2
        assert results["passed"] == 1
        assert results["failed"] == 1
