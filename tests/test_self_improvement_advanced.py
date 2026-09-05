"""Tests for core.evolution.self_improvement_advanced."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.evolution.self_improvement_advanced import (
    AlignmentAudit,
    AlignmentPrinciple,
    AlignmentViolation,
    BoundaryRepair,
    BoundaryCheck,
    ClosedLoopSafetyGate,
    DiversityPressure,
    EvolutionCandidate,
    LineageRecord,
    LineageTracker,
    SelfImprovementBoundary,
    ViolationSeverity,
    BoundaryStatus,
)


# ---------------------------------------------------------------------------
# AlignmentAudit
# ---------------------------------------------------------------------------

def test_alignment_audit_accepts_good_scores():
    audit = AlignmentAudit(threshold=0.5)
    result = audit.audit("agent-1", {
        "harmlessness": 0.9,
        "helpfulness": 0.8,
        "honesty": 0.85,
    })
    assert result["passed"] is True
    assert result["score"] >= 0.5
    assert result["agent_id"] == "agent-1"


def test_alignment_audit_rejects_low_scores():
    audit = AlignmentAudit(threshold=0.75)
    result = audit.audit("agent-2", {
        "harmlessness": 0.1,
        "helpfulness": 0.2,
    })
    assert result["passed"] is False
    assert len(result["violations"]) > 0


def test_alignment_audit_critical_violation():
    audit = AlignmentAudit(threshold=0.75)
    result = audit.audit("agent-3", {
        "harmlessness": 0.05,
    })
    critical = [v for v in result["violations"] if v["severity"] == "critical"]
    assert len(critical) > 0


def test_alignment_audit_disable_principle():
    audit = AlignmentAudit()
    audit.disable_principle("harmlessness")
    result = audit.audit("agent-4", {"helpfulness": 0.9})
    assert result["passed"] is True


def test_alignment_audit_history():
    audit = AlignmentAudit()
    audit.audit("agent-5", {"harmlessness": 0.9, "honesty": 0.9})
    audit.audit("agent-6", {"harmlessness": 0.8, "honesty": 0.8})
    assert len(audit.audit_history) == 2


# ---------------------------------------------------------------------------
# BoundaryRepair
# ---------------------------------------------------------------------------

def test_boundary_repair_check_passes():
    repair = BoundaryRepair()
    repair.register_boundary("max_temp", {"temperature": 1.0})
    checks = repair.check_boundaries({"temperature": 0.5})
    assert all(c.passed for c in checks)


def test_boundary_repair_check_fails():
    repair = BoundaryRepair()
    repair.register_boundary("max_temp", {"temperature": 0.5})
    checks = repair.check_boundaries({"temperature": 0.9})
    assert not all(c.passed for c in checks)


def test_boundary_repair_status():
    repair = BoundaryRepair()
    assert repair.status == BoundaryStatus.HEALTHY
    repair.register_boundary("temp_limit", {"temperature": 0.5})
    repair.check_boundaries({"temperature": 0.9})
    assert repair.status in (BoundaryStatus.DEGRADED, BoundaryStatus.BREACHED)


def test_boundary_repair_history():
    repair = BoundaryRepair()
    repair.register_boundary("max_temp", {"temperature": 0.5})
    repair.check_boundaries({"temperature": 0.9})
    repairs = repair.repair(
        repair.check_boundaries({"temperature": 0.9}),
        {"temperature": 0.9},
    )
    assert len(repair.repair_history) >= 1


# ---------------------------------------------------------------------------
# ClosedLoopSafetyGate
# ---------------------------------------------------------------------------

def test_safety_gate_approves_passing():
    gate = ClosedLoopSafetyGate(min_alignment_score=0.5)
    candidate = EvolutionCandidate(
        candidate_id="cand-1",
        parent_agent_id="parent-1",
        mutations={"lr": 0.01},
        fitness_score=0.8,
    )
    result = gate.evaluate_candidate(candidate, {"harmlessness": 0.9})
    assert "approved" in result["decisions"]


def test_safety_gate_rejects_alignment_failure():
    gate = ClosedLoopSafetyGate(min_alignment_score=0.75)
    candidate = EvolutionCandidate(
        candidate_id="cand-2",
        parent_agent_id="parent-2",
        mutations={"lr": 0.01},
        fitness_score=0.8,
    )
    result = gate.evaluate_candidate(candidate, {
        "harmlessness": 0.1,
        "helpfulness": 0.1,
        "honesty": 0.1,
        "transparency": 0.1,
        "corrigibility": 0.1,
        "value_alignment": 0.1,
    })
    assert "alignment_failed" in result["decisions"]


def test_safety_gate_tracks_deployed():
    gate = ClosedLoopSafetyGate()
    candidate = EvolutionCandidate(
        candidate_id="cand-3",
        parent_agent_id="parent-3",
        mutations={},
        fitness_score=0.9,
    )
    gate.evaluate_candidate(candidate, {"harmlessness": 0.95})
    assert gate.deployed_version is not None


# ---------------------------------------------------------------------------
# DiversityPressure
# ---------------------------------------------------------------------------

def test_diversity_pressure_computes_diversity():
    dp = DiversityPressure()
    c1 = EvolutionCandidate("c1", "p1", {"a": 1})
    c2 = EvolutionCandidate("c2", "p1", {"b": 2})
    c1.diversity_score = dp.compute_diversity(c1)
    c2.diversity_score = dp.compute_diversity(c2)
    assert c1.diversity_score == 1.0  # first in empty population


def test_diversity_pressure_novelty_adjustment():
    dp = DiversityPressure(novelty_weight=0.2)
    c = EvolutionCandidate("c1", "p1", {"a": 1}, fitness_score=0.8)
    adjusted = dp.compute_novelty(c, 0.8)
    assert adjusted >= 0.8  # novelty bonus


def test_diversity_pressure_injects_mutations():
    dp = DiversityPressure(diversity_threshold=0.9)  # high threshold forces injection
    c = EvolutionCandidate("c1", "p1", {"a": 1}, fitness_score=0.8)
    candidates = dp.apply_diversity_pressure([c])
    assert len(candidates) == 1
    assert candidates[0].diversity_score > 0.0


def test_diversity_history():
    dp = DiversityPressure()
    c = EvolutionCandidate("c1", "p1", {"a": 1}, fitness_score=0.8)
    dp.apply_diversity_pressure([c])
    assert len(dp.diversity_history) == 1


# ---------------------------------------------------------------------------
# LineageTracker
# ---------------------------------------------------------------------------

def test_lineage_tracker_records():
    tracker = LineageTracker()
    r = tracker.track(
        agent_id="a1",
        parent_id=None,
        mutation_description="initial",
        fitness_score=0.8,
        alignment_score=0.9,
        diversity_score=1.0,
        safety_gate_passed=True,
    )
    assert r.generation == 0
    assert r.agent_id == "a1"


def test_lineage_tracker_generations():
    tracker = LineageTracker()
    tracker.track("a1", None, "init", 0.8, 0.9, 1.0, True)
    tracker.track("a2", "a1", "mut1", 0.85, 0.92, 0.8, True)
    tracker.track("a3", "a2", "mut2", 0.9, 0.95, 0.7, True)
    assert tracker.get_lineage("a3")[0].generation == 0
    assert tracker.get_lineage("a3")[1].generation == 1
    assert tracker.get_lineage("a3")[2].generation == 2


def test_lineage_stats():
    tracker = LineageTracker()
    tracker.track("a1", None, "init", 0.8, 0.9, 1.0, True)
    tracker.track("a2", "a1", "mut1", 0.85, 0.92, 0.8, True)
    stats = tracker.get_lineage_stats("a2")
    assert stats["count"] == 2
    assert stats["max_generation"] == 1
    assert stats["safety_pass_rate"] == 1.0


def test_lineage_common_ancestor():
    tracker = LineageTracker()
    tracker.track("a1", None, "init", 0.8, 0.9, 1.0, True)
    tracker.track("a2", "a1", "mut1", 0.85, 0.92, 0.8, True)
    tracker.track("a3", "a1", "mut2", 0.82, 0.88, 0.75, True)
    ancestor = tracker.find_common_ancestor("a2", "a3")
    assert ancestor == "a1"


def test_lineage_descendants():
    tracker = LineageTracker()
    tracker.track("a1", None, "init", 0.8, 0.9, 1.0, True)
    tracker.track("a2", "a1", "mut1", 0.85, 0.92, 0.8, True)
    tracker.track("a3", "a2", "mut2", 0.9, 0.95, 0.7, True)
    descendants = tracker.get_descendants("a1")
    assert len(descendants) == 2


# ---------------------------------------------------------------------------
# SelfImprovementBoundary (composed)
# ---------------------------------------------------------------------------

def test_self_improvement_boundary_evaluate():
    boundary = SelfImprovementBoundary()
    candidate = EvolutionCandidate(
        candidate_id="cand-10",
        parent_agent_id="parent-10",
        mutations={"lr": 0.001},
        fitness_score=0.85,
    )
    result = boundary.evaluate(candidate, {"harmlessness": 0.9, "honesty": 0.85})
    assert result["candidate"] is candidate
    assert result["gate_result"] is not None
    assert result["lineage_record"] is not None
    assert result["lineage_record"].agent_id == "cand-10"


def test_self_improvement_boundary_log():
    boundary = SelfImprovementBoundary()
    candidate = EvolutionCandidate(
        candidate_id="cand-11",
        parent_agent_id="parent-11",
        mutations={},
        fitness_score=0.9,
    )
    boundary.evaluate(candidate, {"harmlessness": 0.95})
    assert len(boundary.evaluation_log) == 1


def test_self_improvement_boundary_diversity_applied():
    boundary = SelfImprovementBoundary()
    candidate = EvolutionCandidate(
        candidate_id="cand-12",
        parent_agent_id="parent-12",
        mutations={"novel_param": 0.5},
        fitness_score=0.8,
    )
    result = boundary.evaluate(candidate, {"harmlessness": 0.9})
    assert result["candidate"].diversity_score >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
