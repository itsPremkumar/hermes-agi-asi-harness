"""Tests for Improvement Analysis + Version Management + Rework Decision Engine."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supervisor.improvement import (
    ImprovementAnalyzer, VersionManager, VersionInfo, ReworkDecisionEngine,
    ReworkDecision, ReworkType, FailureClassification, FinalJudgmentSystem,
    ImprovementArea,
)


# ---------------------------------------------------------------------------
# Improvement Analyzer tests
# ---------------------------------------------------------------------------

class TestImprovementAnalyzer:
    def test_create_analyzer(self):
        analyzer = ImprovementAnalyzer()
        assert analyzer is not None

    def test_analyze_no_issues(self):
        analyzer = ImprovementAnalyzer()
        record = type('obj', (object,), {
            'structural': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'security': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'edge_cases': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'performance': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
        })
        result = analyzer.analyze(record)
        assert result["can_be_better"] == False

    def test_analyze_with_issues(self):
        analyzer = ImprovementAnalyzer()
        record = type('obj', (object,), {
            'structural': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'security': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'edge_cases': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'performance': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
        })
        result = analyzer.analyze(record)
        assert result["can_be_better"] == True
        assert len(result["improvement_areas"]) > 0


# ---------------------------------------------------------------------------
# Version Manager tests
# ---------------------------------------------------------------------------

class TestVersionManager:
    def test_create_manager(self):
        manager = VersionManager()
        assert manager is not None

    def test_register_version(self):
        manager = VersionManager()
        version = VersionInfo(version="v1", status="stable")
        manager.register_version(version)
        assert manager.get_stable() is None  # Not set as stable yet

    def test_set_stable(self):
        manager = VersionManager()
        version = VersionInfo(version="v1")
        manager.register_version(version)
        manager.set_stable(version.id)
        assert manager.get_stable() is not None

    def test_rollback(self):
        manager = VersionManager()
        v1 = VersionInfo(version="v1")
        v2 = VersionInfo(version="v2")
        manager.register_version(v1)
        manager.register_version(v2)
        manager.set_best_verified(v1.id)
        manager.set_candidate(v2.id)
        rolled_back = manager.rollback()
        assert rolled_back is not None

    def test_promote_candidate(self):
        manager = VersionManager()
        v1 = VersionInfo(version="v1")
        manager.register_version(v1)
        manager.set_candidate(v1.id)
        manager.promote_candidate()
        assert manager.get_stable() is not None


# ---------------------------------------------------------------------------
# Rework Decision Engine tests
# ---------------------------------------------------------------------------

class TestReworkDecisionEngine:
    def test_create_engine(self):
        engine = ReworkDecisionEngine()
        assert engine is not None

    def test_classify_minor(self):
        engine = ReworkDecisionEngine()
        record = type('obj', (object,), {
            'structural': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'integration': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'system': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
        })
        classification = engine.classify_failure(record)
        assert classification == FailureClassification.MINOR_DEFECT

    def test_classify_fundamentally_bad(self):
        engine = ReworkDecisionEngine()
        record = type('obj', (object,), {
            'structural': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'integration': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'system': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'regression': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'security': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
        })
        classification = engine.classify_failure(record)
        assert classification == FailureClassification.FUNDAMENTALLY_BAD

    def test_decide_rework_patch(self):
        engine = ReworkDecisionEngine()
        decision = engine.decide_rework("task_1", FailureClassification.MINOR_DEFECT)
        assert decision.rework_type == ReworkType.PATCH

    def test_decide_rework_redesign(self):
        engine = ReworkDecisionEngine()
        decision = engine.decide_rework("task_1", FailureClassification.ARCHITECTURAL_DEFECT)
        assert decision.rework_type == ReworkType.REDESIGN

    def test_should_stop_patching(self):
        engine = ReworkDecisionEngine()
        for _ in range(3):
            engine.decide_rework("task_1", FailureClassification.MINOR_DEFECT)
        assert engine.should_stop_patching("task_1")


# ---------------------------------------------------------------------------
# Final Judgment System tests
# ---------------------------------------------------------------------------

class TestFinalJudgmentSystem:
    def test_create_system(self):
        system = FinalJudgmentSystem()
        assert system is not None

    def test_judge_accept(self):
        system = FinalJudgmentSystem()
        record = type('obj', (object,), {
            'structural': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'static': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'unit': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'integration': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'system': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'regression': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'edge_cases': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'adversarial': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'security': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'performance': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'real_environment': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
            'independent_review': type('p', (object,), {'status': type('s', (object,), {'value': 'passed'})()})(),
        })
        result = system.judge(record, {})
        assert result["decision"] in ("accept", "accept_with_improvements")

    def test_judge_rework(self):
        system = FinalJudgmentSystem()
        record = type('obj', (object,), {
            'structural': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'static': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'unit': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'integration': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'system': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'regression': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'edge_cases': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'adversarial': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'security': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'performance': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'real_environment': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
            'independent_review': type('p', (object,), {'status': type('s', (object,), {'value': 'failed'})()})(),
        })
        result = system.judge(record, {"task_id": "t1"})
        assert result["decision"] == "rework"
