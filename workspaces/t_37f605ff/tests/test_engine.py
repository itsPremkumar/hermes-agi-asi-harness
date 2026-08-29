"""Tests for the compliance engine and controls."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from compliance_as_code.engine import (
    BaseControl,
    ComplianceEngine,
    ComplianceFramework,
    ComplianceReport,
    ControlResult,
    ControlStatus,
    Severity,
)
from compliance_as_code.policies import (
    get_all_controls,
    get_controls_by_framework,
    SOC2LogicalAccessControl,
    SOC2EncryptionAtRestControl,
    HIPAASafeguardsControl,
    GDPRConsentControl,
    PCIDSSFirewallControl,
)


class TestComplianceEngine:
    """Tests for the ComplianceEngine class."""

    def test_register_control(self):
        engine = ComplianceEngine()
        control = SOC2LogicalAccessControl()
        engine.register_control(control)
        assert ComplianceFramework.SOC2 in engine._controls
        assert len(engine._controls[ComplianceFramework.SOC2]) == 1

    def test_evaluate_all_pass(self):
        engine = ComplianceEngine()
        for control in get_all_controls():
            engine.register_control(control)

        context = {
            "rbac_enabled": True,
            "mfa_enforced": True,
            "access_reviews_conducted": True,
            "encryption_at_rest": True,
            "encryption_algorithm": "AES-256-GCM",
            "key_management": "AWS KMS",
            "change_approval_required": True,
            "peer_review_required": True,
            "test_environment_separate": True,
            "incident_response_plan": True,
            "ir_plan_tested": True,
            "notification_sla_hours": 48,
            "unique_user_ids": True,
            "emergency_access_procedure": True,
            "auto_logoff_minutes": 15,
            "ephi_encrypted": True,
            "breach_notification_procedure": True,
            "breach_notification_days": 30,
            "breach_log_maintained": True,
            "consent_records_maintained": True,
            "consent_withdrawal_mechanism": True,
            "explicit_consent_required": True,
            "data_export_formats": ["JSON", "CSV"],
            "data_export_api": True,
            "automated_export": True,
            "erasure_procedure": True,
            "erasure_timeline_days": 14,
            "erasure_verification": True,
            "firewall_enabled": True,
            "default_deny_policy": True,
            "firewall_rules_reviewed": True,
            "tls_version": "1.3",
            "weak_protocols_disabled": True,
            "certificate_valid": True,
            "need_to_know_enforced": True,
            "access_review_frequency_days": 60,
            "patch_sla_days": 14,
            "vulnerability_scanning": True,
            "secure_development_practices": True,
        }

        reports = engine.evaluate_all(context)
        assert len(reports) == 4

        for fw, report in reports.items():
            assert report.compliance_score == 100.0
            assert report.failed == 0
            assert report.passed == len(report.results)

    def test_evaluate_all_fail(self):
        engine = ComplianceEngine()
        for control in get_all_controls():
            engine.register_control(control)

        # Empty context — everything should fail
        report = engine.evaluate(ComplianceFramework.SOC2, {})
        assert report.failed > 0

    def test_compliance_report_to_dict(self):
        report = ComplianceReport(
            report_id="test-001",
            generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            framework=ComplianceFramework.SOC2,
        )
        report.results.append(ControlResult(
            control_id="SOC2-CC6.1",
            framework=ComplianceFramework.SOC2,
            status=ControlStatus.PASS,
            description="Test",
        ))

        data = report.to_dict()
        assert data["report_id"] == "test-001"
        assert data["summary"]["total_controls"] == 1
        assert data["summary"]["compliance_score"] == 100.0


class TestSOC2Controls:
    """Tests for SOC2 compliance controls."""

    def test_logical_access_full_compliance(self):
        control = SOC2LogicalAccessControl()
        result = control.evaluate({
            "rbac_enabled": True,
            "mfa_enforced": True,
            "access_reviews_conducted": True,
        })
        assert result.status == ControlStatus.PASS

    def test_logical_access_partial_compliance(self):
        control = SOC2LogicalAccessControl()
        result = control.evaluate({
            "rbac_enabled": True,
            "mfa_enforced": False,
            "access_reviews_conducted": False,
        })
        assert result.status == ControlStatus.WARNING

    def test_logical_access_fail(self):
        control = SOC2LogicalAccessControl()
        result = control.evaluate({
            "rbac_enabled": False,
            "mfa_enforced": False,
        })
        assert result.status == ControlStatus.FAIL

    def test_encryption_at_rest_pass(self):
        control = SOC2EncryptionAtRestControl()
        result = control.evaluate({
            "encryption_at_rest": True,
            "encryption_algorithm": "AES-256-GCM",
            "key_management": "AWS KMS",
        })
        assert result.status == ControlStatus.PASS

    def test_encryption_at_rest_fail(self):
        control = SOC2EncryptionAtRestControl()
        result = control.evaluate({
            "encryption_at_rest": False,
        })
        assert result.status == ControlStatus.FAIL


class TestHIPAAControls:
    """Tests for HIPAA compliance controls."""

    def test_safeguards_pass(self):
        control = HIPAASafeguardsControl()
        result = control.evaluate({
            "unique_user_ids": True,
            "emergency_access_procedure": True,
            "auto_logoff_minutes": 15,
            "ephi_encrypted": True,
        })
        assert result.status == ControlStatus.PASS

    def test_safeguards_fail_no_encryption(self):
        control = HIPAASafeguardsControl()
        result = control.evaluate({
            "unique_user_ids": True,
            "emergency_access_procedure": True,
            "auto_logoff_minutes": 15,
            "ephi_encrypted": False,
        })
        assert result.status == ControlStatus.FAIL


class TestGDPRControls:
    """Tests for GDPR compliance controls."""

    def test_consent_pass(self):
        control = GDPRConsentControl()
        result = control.evaluate({
            "consent_records_maintained": True,
            "consent_withdrawal_mechanism": True,
            "explicit_consent_required": True,
        })
        assert result.status == ControlStatus.PASS

    def test_consent_fail(self):
        control = GDPRConsentControl()
        result = control.evaluate({
            "consent_records_maintained": False,
        })
        assert result.status == ControlStatus.FAIL


class TestPCIDSSControls:
    """Tests for PCI-DSS compliance controls."""

    def test_firewall_pass(self):
        control = PCIDSSFirewallControl()
        result = control.evaluate({
            "firewall_enabled": True,
            "default_deny_policy": True,
            "firewall_rules_reviewed": True,
        })
        assert result.status == ControlStatus.PASS

    def test_firewall_fail(self):
        control = PCIDSSFirewallControl()
        result = control.evaluate({
            "firewall_enabled": False,
        })
        assert result.status == ControlStatus.FAIL


class TestControlRegistry:
    """Tests for the control registry functions."""

    def test_get_all_controls(self):
        controls = get_all_controls()
        assert len(controls) == 13  # 4 SOC2 + 2 HIPAA + 3 GDPR + 4 PCI-DSS

    def test_get_controls_by_framework(self):
        soc2_controls = get_controls_by_framework(ComplianceFramework.SOC2)
        assert len(soc2_controls) == 4

        hipaa_controls = get_controls_by_framework(ComplianceFramework.HIPAA)
        assert len(hipaa_controls) == 2

        gdpr_controls = get_controls_by_framework(ComplianceFramework.GDPR)
        assert len(gdpr_controls) == 3

        pci_controls = get_controls_by_framework(ComplianceFramework.PCI_DSS)
        assert len(pci_controls) == 4
