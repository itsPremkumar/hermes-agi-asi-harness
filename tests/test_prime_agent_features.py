"""
Unit tests for ported Prime Agent architectures:
- Scoped Continual Harness State (prompt, memory, skill, subagent) + Snapshot Rollback
- Autonomous Quality Gates & Continuation Enforcement
- OS-Level Process Tree Isolation (Win32 Job Objects)
- Semantic Branch Summarization
"""

from __future__ import annotations

import pytest

from hermes_agi.refine import (
    HarnessStateManager,
    HarnessEntry,
    RefinementEvent,
)
from hermes_agi.allocation import (
    AutonomousQualityGatePolicy,
    QualityGateVerdict,
    QualityGateFailure,
)
from hermes_agi.coding import ProcessIsolationManager
from hermes_agi.overnight import (
    SemanticBranchSummarizer,
    BranchSummary,
)


class TestScopedHarnessState:
    """Test 4-kind scoped harness state and snapshot rollback."""

    def test_add_and_filter_entries(self, tmp_path):
        mgr = HarnessStateManager(workspace_root=str(tmp_path))
        e1 = mgr.add_entry("prompt", "Safety Guide", "Never disable sandbox", scope="local")
        e2 = mgr.add_entry("subagent", "Deep Critic", "Adversarial verification", scope="local")
        e3 = mgr.add_entry("memory", "Host Topology", "Cluster node 1", scope="global")

        assert len(mgr.get_entries()) == 3
        assert len(mgr.get_entries(kind="prompt")) == 1
        assert len(mgr.get_entries(kind="subagent")) == 1
        assert len(mgr.get_entries(scope="global")) == 1

    def test_snapshot_and_rollback(self, tmp_path):
        mgr = HarnessStateManager(workspace_root=str(tmp_path))
        mgr.add_entry("skill", "Linter", "import ast")
        snap_id = mgr.create_snapshot()

        # Add another entry after snapshot
        mgr.add_entry("memory", "Temp Data", "to be rolled back")
        assert len(mgr.get_entries()) == 2

        # Rollback
        success = mgr.rollback_snapshot(snap_id)
        assert success is True
        assert len(mgr.get_entries()) == 1
        assert mgr.get_entries()[0].kind == "skill"


class TestQualityGates:
    """Test autonomous quality gates and continuation prompt injection."""

    def test_passing_gate(self):
        import sys
        policy = AutonomousQualityGatePolicy()
        verdict = policy.evaluate_gates([f'"{sys.executable}" -c "x = 10; assert x == 10"'])
        assert isinstance(verdict, QualityGateVerdict)
        assert verdict.passed is True
        assert verdict.continuation_directive == ""

    def test_failing_gate_injects_continuation(self):
        import sys
        policy = AutonomousQualityGatePolicy()
        verdict = policy.evaluate_gates([f'"{sys.executable}" -c "import sys; sys.exit(1)"'])
        assert verdict.passed is False
        assert len(verdict.failures) == 1
        assert "No human input is available in autonomous mode" in verdict.continuation_directive


class TestProcessIsolation:
    """Test process tree isolation."""

    def test_job_object_lifecycle(self):
        mgr = ProcessIsolationManager()
        if mgr.is_windows:
            assert mgr._job_handle is not None
        mgr.close()
        assert mgr._job_handle is None


class TestBranchSummarizer:
    """Test semantic branch summarization."""

    def test_branch_transition_summary(self):
        summarizer = SemanticBranchSummarizer()
        summary = summarizer.summarize_transition("main", "main", decisions=["Added safety invariants"])
        assert isinstance(summary, BranchSummary)
        md = summary.to_markdown()
        assert "Branch Context" in md
        assert "Added safety invariants" in md
