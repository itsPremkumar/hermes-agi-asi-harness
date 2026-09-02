"""Tests for Advanced Safety Enforcer."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from safety.advanced_enforcer import (
    AdvancedSafetyEnforcer,
    SafetyRule,
    Incident,
    ThreatModel,
    RiskLevel,
    IncidentStatus,
)


class TestSafetyRule:
    def test_create(self):
        rule = SafetyRule("r1", "No deletes", "Prevent data deletion", RiskLevel.HIGH)
        assert rule.rule_id == "r1"
        assert rule.enabled is True
        assert rule.action == "block"


class TestIncident:
    def test_create(self):
        incident = Incident("i1", "Test", "Description", RiskLevel.MEDIUM)
        assert incident.incident_id == "i1"
        assert incident.status == IncidentStatus.OPEN


class TestThreatModel:
    def test_create(self):
        model = ThreatModel("tm1", "Data Breach")
        assert model.model_id == "tm1"
        assert model.threats == []


class TestAdvancedSafetyEnforcer:
    def test_create(self):
        se = AdvancedSafetyEnforcer()
        assert se is not None

    def test_add_rule(self):
        se = AdvancedSafetyEnforcer()
        rule = SafetyRule("r1", "No deletes", "Prevent deletion", RiskLevel.HIGH)
        se.add_rule(rule)
        assert len(se.get_rules()) == 1

    def test_remove_rule(self):
        se = AdvancedSafetyEnforcer()
        rule = SafetyRule("r1", "No deletes", "Prevent deletion", RiskLevel.HIGH)
        se.add_rule(rule)
        se.remove_rule("r1")
        assert len(se.get_rules()) == 0

    def test_enable_disable_rule(self):
        se = AdvancedSafetyEnforcer()
        rule = SafetyRule("r1", "Test", "Desc", RiskLevel.LOW)
        se.add_rule(rule)
        assert se.disable_rule("r1") is True
        assert se.get_rules()[0].enabled is False
        assert se.enable_rule("r1") is True
        assert se.get_rules()[0].enabled is True

    def test_check_action_no_rules(self):
        se = AdvancedSafetyEnforcer()
        result = se.check_action("delete", {})
        assert result["allowed"] is True

    def test_check_action_with_violation(self):
        se = AdvancedSafetyEnforcer()
        rule = SafetyRule("r1", "Block deletes", "Prevent deletion", RiskLevel.HIGH, condition="delete")
        se.add_rule(rule)
        result = se.check_action("delete", {})
        assert result["allowed"] is False
        assert len(result["violations"]) == 1

    def test_check_action_warn(self):
        se = AdvancedSafetyEnforcer()
        rule = SafetyRule("r1", "Warn", "Warning", RiskLevel.MEDIUM, action="warn", condition="risky")
        se.add_rule(rule)
        result = se.check_action("risky_action", {})
        assert len(result["violations"]) == 1

    def test_report_incident(self):
        se = AdvancedSafetyEnforcer()
        incident = Incident("i1", "Test", "Desc", RiskLevel.HIGH)
        se.report_incident(incident)
        assert len(se.get_incidents()) == 1

    def test_resolve_incident(self):
        se = AdvancedSafetyEnforcer()
        incident = Incident("i1", "Test", "Desc", RiskLevel.HIGH)
        se.report_incident(incident)
        assert se.resolve_incident("i1", "Fixed") is True
        assert se.get_incidents()[0].status == IncidentStatus.RESOLVED

    def test_escalate_incident(self):
        se = AdvancedSafetyEnforcer()
        incident = Incident("i1", "Test", "Desc", RiskLevel.CRITICAL)
        se.report_incident(incident)
        assert se.escalate_incident("i1") is True
        assert se.get_incidents()[0].status == IncidentStatus.ESCALATED

    def test_create_threat_model(self):
        se = AdvancedSafetyEnforcer()
        model = ThreatModel("tm1", "Data Breach")
        se.create_threat_model(model)
        assert len(se._threat_models) == 1

    def test_assess_risk(self):
        se = AdvancedSafetyEnforcer()
        rule = SafetyRule("r1", "Block deletes", "Prevent deletion", RiskLevel.HIGH, condition="delete")
        se.add_rule(rule)
        result = se.assess_risk("delete", {})
        assert result["risk_level"] == "high"
        assert result["recommendation"] == "block"

    def test_get_action_log(self):
        se = AdvancedSafetyEnforcer()
        rule = SafetyRule("r1", "Block", "Block", RiskLevel.HIGH, condition="x")
        se.add_rule(rule)
        se.check_action("x", {})
        assert len(se.get_action_log()) == 1

    def test_get_stats(self):
        se = AdvancedSafetyEnforcer()
        se.add_rule(SafetyRule("r1", "Test", "Desc", RiskLevel.LOW))
        se.report_incident(Incident("i1", "Test", "Desc", RiskLevel.HIGH))
        stats = se.get_stats()
        assert stats["total_rules"] == 1
        assert stats["total_incidents"] == 1
        assert stats["open_incidents"] == 1
