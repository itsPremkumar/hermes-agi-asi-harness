<<<<<<< HEAD
"""Advanced Safety Module — threat modeling, risk assessment, policy enforcement,
incident response, and compliance auditing for AI agent systems."""

from __future__ import annotations

from src.safety.threat_modeler import (
=======
"""Advanced Safety Module for the Hermes AGI/ASI Harness.

Components:
- threat_modeler: model potential threats, identify attack vectors
- risk_assessor: assess risk levels, categorize by severity
- safety_enforcer: enforce safety policies, block dangerous operations
- incident_responder: respond to safety incidents, escalation paths
- safety_auditor: audit safety compliance, generate compliance reports
"""
from safety.threat_modeler import (
>>>>>>> 7bed5b11ca2c5b86bd3e0d48bfc3c28933c70109
    Threat,
    ThreatCategory,
    ThreatModel,
    ThreatModeler,
    ThreatSeverity,
)
<<<<<<< HEAD
from src.safety.risk_assessor import (
    RiskAssessment,
    RiskAssessor,
    RiskLevel,
)
from src.safety.safety_enforcer import (
    EnforcementAction,
    EnforcementResult,
    PolicyRule,
    PolicyType,
    SafetyEnforcer,
)
from src.safety.incident_responder import (
    Incident,
    IncidentResponder,
    IncidentSeverity,
    IncidentType,
)
from src.safety.safety_auditor import (
    AuditCheck,
    AuditCheckType,
    AuditFinding,
    AuditReport,
    AuditResult,
    AuditStatus,
=======
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
>>>>>>> 7bed5b11ca2c5b86bd3e0d48bfc3c28933c70109
    SafetyAuditor,
)

__all__ = [
<<<<<<< HEAD
    # threat_modeler
=======
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
>>>>>>> 7bed5b11ca2c5b86bd3e0d48bfc3c28933c70109
    "Threat",
    "ThreatCategory",
    "ThreatModel",
    "ThreatModeler",
    "ThreatSeverity",
<<<<<<< HEAD
    # risk_assessor
    "RiskAssessment",
    "RiskAssessor",
    "RiskLevel",
    # safety_enforcer
    "EnforcementAction",
    "EnforcementResult",
    "PolicyRule",
    "PolicyType",
    "SafetyEnforcer",
    # incident_responder
    "Incident",
    "IncidentResponder",
    "IncidentSeverity",
    "IncidentType",
    # safety_auditor
    "AuditCheck",
    "AuditCheckType",
    "AuditFinding",
    "AuditReport",
    "AuditResult",
    "AuditStatus",
    "SafetyAuditor",
]
=======
]

__version__ = "1.0.0"
>>>>>>> 7bed5b11ca2c5b86bd3e0d48bfc3c28933c70109
