"""Tests for AI Governance & Ethics Framework."""
from __future__ import annotations

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from governance import (
    Policy,
    ComplianceCheck,
    RiskAssessment,
    EthicsReview,
    AuditTrail,
    PolicyEngine,
    RiskAssessor,
    EthicsReviewer,
    AuditLogger,
    Governance,
)


# ─── Policy Tests ──────────────────────────────────────────────────────────────

class TestPolicy:
    def test_create_policy(self):
        policy = Policy(id="1", name="Test", description="Test policy", category="security", severity="high")
        assert policy.id == "1"
        assert policy.name == "Test"
        assert policy.enabled is True


# ─── PolicyEngine Tests ────────────────────────────────────────────────────────

class TestPolicyEngine:
    def test_register_and_get(self):
        engine = PolicyEngine()
        policy = Policy(id="1", name="Test", description="Test", category="security", severity="high")
        engine.register(policy)
        assert engine.get("1").name == "Test"

    def test_get_all(self):
        engine = PolicyEngine()
        engine.register(Policy(id="1", name="P1", description="Test", category="security", severity="high"))
        engine.register(Policy(id="2", name="P2", description="Test", category="privacy", severity="medium"))
        assert len(engine.get_all()) == 2

    def test_get_enabled(self):
        engine = PolicyEngine()
        engine.register(Policy(id="1", name="P1", description="Test", category="security", severity="high", enabled=True))
        engine.register(Policy(id="2", name="P2", description="Test", category="privacy", severity="medium", enabled=False))
        assert len(engine.get_enabled()) == 1

    def test_get_by_category(self):
        engine = PolicyEngine()
        engine.register(Policy(id="1", name="P1", description="Test", category="security", severity="high"))
        engine.register(Policy(id="2", name="P2", description="Test", category="security", severity="medium"))
        engine.register(Policy(id="3", name="P3", description="Test", category="privacy", severity="low"))
        assert len(engine.get_by_category("security")) == 2

    def test_enable_disable(self):
        engine = PolicyEngine()
        engine.register(Policy(id="1", name="P1", description="Test", category="security", severity="high", enabled=True))
        engine.disable("1")
        assert engine.get("1").enabled is False
        engine.enable("1")
        assert engine.get("1").enabled is True

    def test_evaluate(self):
        engine = PolicyEngine()
        engine.register(Policy(id="1", name="P1", description="Test", category="security", severity="high"))
        checks = engine.evaluate("resource1", {})
        assert len(checks) == 1


# ─── RiskManager Tests ─────────────────────────────────────────────────────────

class TestRiskAssessor:
    def test_add_and_get(self):
        rm = RiskAssessor()
        risk = RiskAssessment(id="1", title="Test", likelihood="high", impact="high", risk_level="high")
        rm.add(risk)
        assert rm.get("1").title == "Test"

    def test_get_all(self):
        rm = RiskAssessor()
        rm.add(RiskAssessment(id="1", title="R1", likelihood="high", impact="high", risk_level="high"))
        rm.add(RiskAssessment(id="2", title="R2", likelihood="low", impact="low", risk_level="low"))
        assert len(rm.get_all()) == 2

    def test_get_by_level(self):
        rm = RiskAssessor()
        rm.add(RiskAssessment(id="1", title="R1", likelihood="high", impact="high", risk_level="high"))
        rm.add(RiskAssessment(id="2", title="R2", likelihood="low", impact="low", risk_level="low"))
        rm.add(RiskAssessment(id="3", title="R3", likelihood="high", impact="medium", risk_level="high"))
        assert len(rm.get_by_level("high")) == 2

    def test_get_high_risks(self):
        rm = RiskAssessor()
        rm.add(RiskAssessment(id="1", title="R1", likelihood="critical", impact="critical", risk_level="critical"))
        rm.add(RiskAssessment(id="2", title="R2", likelihood="low", impact="low", risk_level="low"))
        assert len(rm.get_high_risks()) == 1

    def test_calculate_risk_level(self):
        rm = RiskAssessor()
        assert rm.calculate_risk_level("critical", "critical") == "critical"
        assert rm.calculate_risk_level("high", "high") == "high"
        assert rm.calculate_risk_level("low", "low") == "low"
        assert rm.calculate_risk_level("medium", "medium") == "medium"


# ─── EthicsReviewer Tests ──────────────────────────────────────────────────────

class TestEthicsReviewer:
    def test_create(self):
        reviewer = EthicsReviewer()
        review = reviewer.create("Test Review", "Test description")
        assert review.title == "Test Review"
        assert review.status == "pending"

    def test_get_all(self):
        reviewer = EthicsReviewer()
        reviewer.create("R1", "D1")
        reviewer.create("R2", "D2")
        assert len(reviewer.get_all()) == 2

    def test_approve(self):
        reviewer = EthicsReviewer()
        review = reviewer.create("Test", "Desc")
        reviewer.approve(review.id)
        assert reviewer.get(review.id).status == "approved"

    def test_reject(self):
        reviewer = EthicsReviewer()
        review = reviewer.create("Test", "Desc")
        reviewer.reject(review.id)
        assert reviewer.get(review.id).status == "rejected"

    def test_add_finding(self):
        reviewer = EthicsReviewer()
        review = reviewer.create("Test", "Desc")
        reviewer.add_finding(review.id, "Finding 1")
        assert len(reviewer.get(review.id).findings) == 1

    def test_add_recommendation(self):
        reviewer = EthicsReviewer()
        review = reviewer.create("Test", "Desc")
        reviewer.add_recommendation(review.id, "Recommendation 1")
        assert len(reviewer.get(review.id).recommendations) == 1


# ─── AuditLogger Tests ─────────────────────────────────────────────────────────

class TestAuditLogger:
    def test_log(self):
        logger = AuditLogger()
        entry = logger.log("create", "user1", "resource1")
        assert entry.action == "create"
        assert entry.actor == "user1"

    def test_get_by_actor(self):
        logger = AuditLogger()
        logger.log("create", "user1", "r1")
        logger.log("delete", "user2", "r2")
        logger.log("update", "user1", "r3")
        assert len(logger.get_by_actor("user1")) == 2

    def test_get_by_resource(self):
        logger = AuditLogger()
        logger.log("create", "user1", "resource1")
        logger.log("update", "user2", "resource1")
        assert len(logger.get_by_resource("resource1")) == 2

    def test_get_by_action(self):
        logger = AuditLogger()
        logger.log("create", "user1", "r1")
        logger.log("create", "user2", "r2")
        logger.log("delete", "user3", "r3")
        assert len(logger.get_by_action("create")) == 2


# ─── Governance Tests ──────────────────────────────────────────────────────────

class TestGovernance:
    def test_compliance_report(self):
        g = Governance()
        g.policies.register(Policy(id="1", name="Test", description="Test", category="security", severity="high"))
        g.risks.add(RiskAssessment(id="1", title="R1", likelihood="high", impact="high", risk_level="high"))
        report = g.compliance_report()
        assert "total_policies" in report
        assert "enabled_policies" in report
        assert "total_risks" in report
        assert "high_risks" in report
        assert "ethics_reviews" in report
        assert "audit_entries" in report
