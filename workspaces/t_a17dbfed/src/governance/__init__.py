"""AI Governance & Ethics Framework — Policies, Compliance, Risk Management."""
from __future__ import annotations

from governance.policy_engine import Policy, ComplianceCheck, PolicyEngine
from governance.risk_assessor import RiskAssessment, RiskAssessor
from governance.ethics_reviewer import EthicsReview, EthicsReviewer
from governance.audit import AuditTrail, AuditLogger

__all__ = [
    "Policy",
    "ComplianceCheck",
    "PolicyEngine",
    "RiskAssessment",
    "RiskAssessor",
    "EthicsReview",
    "EthicsReviewer",
    "AuditTrail",
    "AuditLogger",
    "Governance",
]


class Governance:
    """Main governance facade."""

    def __init__(self) -> None:
        self.policies = PolicyEngine()
        self.risks = RiskAssessor()
        self.ethics = EthicsReviewer()
        self.audit = AuditLogger()

    def compliance_report(self) -> dict:
        """Generate a compliance report."""
        return {
            "total_policies": len(self.policies.get_all()),
            "enabled_policies": len(self.policies.get_enabled()),
            "total_risks": len(self.risks.get_all()),
            "high_risks": len(self.risks.get_high_risks()),
            "ethics_reviews": len(self.ethics.get_all()),
            "audit_entries": len(self.audit.get_all()),
        }
