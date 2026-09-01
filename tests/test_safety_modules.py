"""Tests for Advanced Safety Module — risk_assessor, safety_enforcer, incident_responder, safety_auditor."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.safety.risk_assessor import RiskAssessor, RiskLevel
from src.safety.safety_enforcer import PolicyAction, PolicyRule, SafetyEnforcer
from src.safety.incident_responder import IncidentResponder, IncidentSeverity, IncidentStatus
from src.safety.safety_auditor import AuditStatus, SafetyAuditor


class TestRiskAssessor(unittest.TestCase):
    def setUp(self):
        self.assessor = RiskAssessor()

    def test_assess_low_risk(self):
        result = self.assessor.assess("Low risk", 0.2, 0.3)
        self.assertEqual(result.level, RiskLevel.LOW)

    def test_assess_medium_risk(self):
        result = self.assessor.assess("Medium risk", 0.5, 0.6)
        self.assertEqual(result.level, RiskLevel.MEDIUM)

    def test_assess_high_risk(self):
        result = self.assessor.assess("High risk", 0.8, 0.8)
        self.assertEqual(result.level, RiskLevel.HIGH)

    def test_assess_critical_risk(self):
        result = self.assessor.assess("Critical risk", 1.0, 1.0)
        self.assertEqual(result.level, RiskLevel.CRITICAL)

    def test_score_calculation(self):
        result = self.assessor.assess("Test", 0.5, 0.4)
        self.assertAlmostEqual(result.score, 0.2)

    def test_is_acceptable_true(self):
        result = self.assessor.assess("Low", 0.2, 0.3)
        self.assertTrue(self.assessor.is_acceptable(result))

    def test_is_acceptable_false(self):
        result = self.assessor.assess("High", 0.9, 0.9)
        self.assertFalse(self.assessor.is_acceptable(result))

    def test_mitigations(self):
        result = self.assessor.assess("Test", 0.5, 0.5, ["mit1", "mit2"])
        self.assertEqual(len(result.mitigations), 2)


class TestSafetyEnforcer(unittest.TestCase):
    def setUp(self):
        self.enforcer = SafetyEnforcer()

    def test_add_rule(self):
        rule = PolicyRule("r1", "test", "pattern", PolicyAction.DENY)
        self.enforcer.add_rule(rule)
        self.assertEqual(len(self.enforcer._rules), 1)

    def test_check_match(self):
        rule = PolicyRule("r1", "test", "badword", PolicyAction.DENY)
        self.enforcer.add_rule(rule)
        result = self.enforcer.check("this has badword in it")
        self.assertIsNotNone(result)
        self.assertEqual(result.action, PolicyAction.DENY)

    def test_check_no_match(self):
        rule = PolicyRule("r1", "test", "badword", PolicyAction.DENY)
        self.enforcer.add_rule(rule)
        result = self.enforcer.check("clean text")
        self.assertIsNone(result)

    def test_check_disabled_rule(self):
        rule = PolicyRule("r1", "test", "badword", PolicyAction.DENY, enabled=False)
        self.enforcer.add_rule(rule)
        result = self.enforcer.check("this has badword")
        self.assertIsNone(result)

    def test_check_all(self):
        self.enforcer.add_rule(PolicyRule("r1", "rule1", "bad", PolicyAction.DENY))
        self.enforcer.add_rule(PolicyRule("r2", "rule2", "worse", PolicyAction.WARN))
        results = self.enforcer.check_all("bad and worse")
        self.assertEqual(len(results), 2)


class TestIncidentResponder(unittest.TestCase):
    def setUp(self):
        self.responder = IncidentResponder()

    def test_create_incident(self):
        inc_id = self.responder.create_incident("Test", IncidentSeverity.HIGH, "Description")
        self.assertIsNotNone(inc_id)

    def test_get_incident(self):
        inc_id = self.responder.create_incident("Test", IncidentSeverity.HIGH, "Description")
        incident = self.responder.get_incident(inc_id)
        self.assertIsNotNone(incident)
        self.assertEqual(incident.title, "Test")

    def test_get_incident_not_found(self):
        self.assertIsNone(self.responder.get_incident("nonexistent"))

    def test_update_status(self):
        inc_id = self.responder.create_incident("Test", IncidentSeverity.HIGH, "Description")
        result = self.responder.update_status(inc_id, IncidentStatus.INVESTIGATING)
        self.assertTrue(result)
        self.assertEqual(self.responder.get_incident(inc_id).status, IncidentStatus.INVESTIGATING)

    def test_update_status_not_found(self):
        result = self.responder.update_status("nonexistent", IncidentStatus.INVESTIGATING)
        self.assertFalse(result)

    def test_resolve(self):
        inc_id = self.responder.create_incident("Test", IncidentSeverity.HIGH, "Description")
        result = self.responder.resolve(inc_id, "Fixed the issue")
        self.assertTrue(result)
        self.assertEqual(self.responder.get_incident(inc_id).status, IncidentStatus.RESOLVED)
        self.assertEqual(self.responder.get_incident(inc_id).resolution, "Fixed the issue")

    def test_add_action(self):
        inc_id = self.responder.create_incident("Test", IncidentSeverity.HIGH, "Description")
        self.responder.add_action(inc_id, "Restarted service")
        actions = self.responder.get_actions(inc_id)
        self.assertEqual(len(actions), 1)

    def test_list_incidents(self):
        self.responder.create_incident("Test1", IncidentSeverity.HIGH, "Desc1")
        self.responder.create_incident("Test2", IncidentSeverity.LOW, "Desc2")
        incidents = self.responder.list_incidents()
        self.assertEqual(len(incidents), 2)

    def test_list_incidents_by_status(self):
        inc_id = self.responder.create_incident("Test", IncidentSeverity.HIGH, "Desc")
        self.responder.update_status(inc_id, IncidentStatus.RESOLVED)
        resolved = self.responder.list_incidents(status=IncidentStatus.RESOLVED)
        self.assertEqual(len(resolved), 1)


class TestSafetyAuditor(unittest.TestCase):
    def setUp(self):
        self.auditor = SafetyAuditor()

    def test_create_report(self):
        report_id = self.auditor.create_report("Test Report")
        self.assertIsNotNone(report_id)

    def test_add_finding(self):
        report_id = self.auditor.create_report("Test Report")
        self.auditor.add_finding(report_id, "Finding 1", AuditStatus.PASS, "Desc", "Rec")
        report = self.auditor.get_report(report_id)
        self.assertEqual(len(report.findings), 1)

    def test_get_report_not_found(self):
        self.assertIsNone(self.auditor.get_report("nonexistent"))

    def test_list_reports(self):
        self.auditor.create_report("Report 1")
        self.auditor.create_report("Report 2")
        reports = self.auditor.list_reports()
        self.assertEqual(len(reports), 2)

    def test_summary(self):
        report_id = self.auditor.create_report("Test Report")
        self.auditor.add_finding(report_id, "F1", AuditStatus.PASS, "D", "R")
        self.auditor.add_finding(report_id, "F2", AuditStatus.FAIL, "D", "R")
        summary = self.auditor.summary(report_id)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["pass"], 1)
        self.assertEqual(summary["fail"], 1)
        self.assertFalse(summary["overall_pass"])

    def test_overall_pass_true(self):
        report_id = self.auditor.create_report("Test Report")
        self.auditor.add_finding(report_id, "F1", AuditStatus.PASS, "D", "R")
        report = self.auditor.get_report(report_id)
        self.assertTrue(report.overall_pass)

    def test_summary_not_found(self):
        summary = self.auditor.summary("nonexistent")
        self.assertIn("error", summary)


class TestRiskAssessorEdgeCases(unittest.TestCase):
    def setUp(self):
        self.assessor = RiskAssessor()

    def test_assess_zero_likelihood(self):
        result = self.assessor.assess("Zero", 0.0, 1.0)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.level, RiskLevel.LOW)

    def test_assess_zero_impact(self):
        result = self.assessor.assess("Zero", 1.0, 0.0)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.level, RiskLevel.LOW)

    def test_assess_exact_medium_threshold(self):
        result = self.assessor.assess("Exact", 0.3, 1.0)
        self.assertAlmostEqual(result.score, 0.3)
        self.assertEqual(result.level, RiskLevel.MEDIUM)

    def test_assess_exact_high_threshold(self):
        result = self.assessor.assess("Exact", 0.6, 1.0)
        self.assertAlmostEqual(result.score, 0.6)
        self.assertEqual(result.level, RiskLevel.HIGH)

    def test_assess_exact_critical_threshold(self):
        result = self.assessor.assess("Exact", 0.8, 1.0)
        self.assertAlmostEqual(result.score, 0.8)
        self.assertEqual(result.level, RiskLevel.CRITICAL)


class TestSafetyEnforcerEdgeCases(unittest.TestCase):
    def setUp(self):
        self.enforcer = SafetyEnforcer()

    def test_multiple_rules_same_pattern(self):
        self.enforcer.add_rule(PolicyRule("r1", "rule1", "bad", PolicyAction.DENY))
        self.enforcer.add_rule(PolicyRule("r2", "rule2", "bad", PolicyAction.WARN))
        results = self.enforcer.check_all("bad text")
        self.assertEqual(len(results), 2)

    def test_empty_input(self):
        self.enforcer.add_rule(PolicyRule("r1", "rule1", "bad", PolicyAction.DENY))
        result = self.enforcer.check("")
        self.assertIsNone(result)


class TestIncidentResponderEdgeCases(unittest.TestCase):
    def setUp(self):
        self.responder = IncidentResponder()

    def test_get_actions_empty(self):
        actions = self.responder.get_actions("nonexistent")
        self.assertEqual(len(actions), 0)

    def test_add_multiple_actions(self):
        inc_id = self.responder.create_incident("Test", IncidentSeverity.HIGH, "Desc")
        self.responder.add_action(inc_id, "Action 1")
        self.responder.add_action(inc_id, "Action 2")
        self.responder.add_action(inc_id, "Action 3")
        actions = self.responder.get_actions(inc_id)
        self.assertEqual(len(actions), 3)


if __name__ == "__main__":
    unittest.main()
