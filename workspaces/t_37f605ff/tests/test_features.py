"""Tests for drift detection, risk scoring, and remediation."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from compliance_as_code.drift import (
    DriftDetector,
    DriftReport,
    DriftEvent,
    DriftType,
    DriftSeverity,
)
from compliance_as_code.risk import (
    RiskScoringEngine,
    RiskLevel,
    RiskScore,
)
from compliance_as_code.remediation import (
    generate_remediation_plan,
    RemediationPlan,
    RemediationType,
    RemediationStatus,
)
from compliance_as_code.engine import (
    ComplianceEngine,
    ComplianceFramework,
    ControlResult,
    ControlStatus,
    Severity,
)


class TestDriftDetector:
    """Tests for the DriftDetector class."""

    def test_no_drift(self, tmp_path):
        baseline = {"rbac_enabled": True, "encryption_at_rest": True}
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps(baseline))

        detector = DriftDetector(baseline_path)
        report = detector.detect_drift({"rbac_enabled": True, "encryption_at_rest": True})

        assert report.total_drifts == 0

    def test_detect_configuration_drift(self, tmp_path):
        baseline = {"rbac_enabled": True, "encryption_at_rest": True}
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps(baseline))

        detector = DriftDetector(baseline_path)
        report = detector.detect_drift({"rbac_enabled": False, "encryption_at_rest": True})

        assert report.total_drifts == 1
        assert report.events[0].drift_type == DriftType.ACCESS

    def test_detect_encryption_drift(self, tmp_path):
        baseline = {"encryption_at_rest": True}
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps(baseline))

        detector = DriftDetector(baseline_path)
        report = detector.detect_drift({"encryption_at_rest": False})

        assert report.total_drifts == 1
        assert report.events[0].drift_type == DriftType.ENCRYPTION
        assert report.events[0].severity == DriftSeverity.CRITICAL

    def test_save_baseline(self, tmp_path):
        detector = DriftDetector()
        detector.set_baseline({"key": "value"})
        path = detector.save_baseline(tmp_path / "saved_baseline.json")

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["key"] == "value"


class TestRiskScoring:
    """Tests for the RiskScoringEngine class."""

    def test_all_pass_risk_score(self):
        engine = ComplianceEngine()
        risk_engine = RiskScoringEngine()

        for control in __import__("compliance_as_code.policies", fromlist=["get_all_controls"]).get_all_controls():
            engine.register_control(control)

        context = {
            "rbac_enabled": True, "mfa_enforced": True, "access_reviews_conducted": True,
            "encryption_at_rest": True, "encryption_algorithm": "AES-256-GCM",
            "change_approval_required": True, "peer_review_required": True,
            "test_environment_separate": True, "incident_response_plan": True,
            "ir_plan_tested": True, "notification_sla_hours": 48,
        }
        report = engine.evaluate(ComplianceFramework.SOC2, context)
        risk = risk_engine.calculate_risk(report)

        assert risk.overall_score == 0.0
        assert risk.risk_level == RiskLevel.MINIMAL

    def test_all_fail_risk_score(self):
        engine = ComplianceEngine()
        risk_engine = RiskScoringEngine()

        for control in __import__("compliance_as_code.policies", fromlist=["get_all_controls"]).get_all_controls():
            engine.register_control(control)

        report = engine.evaluate(ComplianceFramework.SOC2, {})
        risk = risk_engine.calculate_risk(report)

        assert risk.overall_score > 50.0
        assert risk.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH)

    def test_risk_recommendations(self):
        engine = ComplianceEngine()
        risk_engine = RiskScoringEngine()

        for control in __import__("compliance_as_code.policies", fromlist=["get_all_controls"]).get_all_controls():
            engine.register_control(control)

        report = engine.evaluate(ComplianceFramework.SOC2, {})
        risk = risk_engine.calculate_risk(report)

        assert len(risk.recommendations) > 0


class TestRemediation:
    """Tests for remediation plan generation."""

    def test_no_remediation_when_all_pass(self):
        engine = ComplianceEngine()
        for control in __import__("compliance_as_code.policies", fromlist=["get_all_controls"]).get_all_controls():
            engine.register_control(control)

        context = {
            "rbac_enabled": True, "mfa_enforced": True, "access_reviews_conducted": True,
            "encryption_at_rest": True, "encryption_algorithm": "AES-256-GCM",
            "change_approval_required": True, "peer_review_required": True,
            "test_environment_separate": True, "incident_response_plan": True,
            "ir_plan_tested": True, "notification_sla_hours": 48,
        }
        report = engine.evaluate(ComplianceFramework.SOC2, context)
        plan = generate_remediation_plan(report.results)

        assert plan.total_actions == 0

    def test_remediation_for_failures(self):
        engine = ComplianceEngine()
        for control in __import__("compliance_as_code.policies", fromlist=["get_all_controls"]).get_all_controls():
            engine.register_control(control)

        report = engine.evaluate(ComplianceFramework.SOC2, {})
        plan = generate_remediation_plan(report.results)

        assert plan.total_actions > 0
        assert plan.framework == ComplianceFramework.SOC2

    def test_remediation_action_types(self):
        engine = ComplianceEngine()
        for control in __import__("compliance_as_code.policies", fromlist=["get_all_controls"]).get_all_controls():
            engine.register_control(control)

        report = engine.evaluate(ComplianceFramework.SOC2, {})
        plan = generate_remediation_plan(report.results)

        for action in plan.actions:
            assert action.remediation_type in (
                RemediationType.AUTOMATED,
                RemediationType.SEMI_AUTOMATED,
                RemediationType.MANUAL,
            )
            assert action.estimated_effort_hours > 0
