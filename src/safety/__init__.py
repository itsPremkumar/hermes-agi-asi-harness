"""Advanced Safety Module for the Hermes AGI/ASI Harness.

Components:
- threat_modeler: model potential threats, identify attack vectors
- risk_assessor: assess risk levels, categorize by severity
- safety_enforcer: enforce safety policies, block dangerous operations
- incident_responder: respond to safety incidents, escalation paths
- safety_auditor: audit safety compliance, generate compliance reports
"""
from safety.threat_modeler import (
    Threat,
    ThreatCategory,
    ThreatModel,
    ThreatModeler,
    ThreatSeverity,
)
from safety.risk_assessor import (
    Risk,
    RiskAssessor,
    RiskLevel,
    RiskProfile,
)
from safety.safety_enforcer import (
    EnforcementResult,
    PolicyAction,
    SafetyEnforcer,
    SafetyPolicy,
)
from safety.incident_responder import (
    Incident,
    IncidentLevel,
    IncidentResponder,
    IncidentStatus,
)
from safety.safety_auditor import (
    AuditReport,
    AuditSeverity,
    ComplianceStandard,
    SafetyAuditor,
)

__all__ = [
    "AuditReport",
    "AuditSeverity",
    "ComplianceStandard",
    "EnforcementResult",
    "Incident",
    "IncidentLevel",
    "IncidentResponder",
    "IncidentStatus",
    "PolicyAction",
    "Risk",
    "RiskAssessor",
    "RiskLevel",
    "RiskProfile",
    "SafetyAuditor",
    "SafetyEnforcer",
    "SafetyPolicy",
    "Threat",
    "ThreatCategory",
    "ThreatModel",
    "ThreatModeler",
    "ThreatSeverity",
]

__version__ = "1.0.0"
