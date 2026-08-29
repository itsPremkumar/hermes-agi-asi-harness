"""Remediation playbooks — automated and guided remediation for compliance failures."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from compliance_as_code.engine import (
    ComplianceFramework,
    ControlResult,
    ControlStatus,
    Severity,
)

logger = logging.getLogger(__name__)


class RemediationStatus(str, Enum):
    """Status of a remediation action."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"


class RemediationType(str, Enum):
    """Type of remediation action."""
    AUTOMATED = "AUTOMATED"
    SEMI_AUTOMATED = "SEMI_AUTOMATED"
    MANUAL = "MANUAL"


@dataclass
class RemediationAction:
    """A single remediation action for a compliance failure."""
    action_id: str
    control_id: str
    framework: ComplianceFramework
    title: str
    description: str
    remediation_type: RemediationType
    steps: list[str] = field(default_factory=list)
    status: RemediationStatus = RemediationStatus.PENDING
    estimated_effort_hours: float = 0.0
    priority: int = 0  # 1 = highest
    _executor: Callable[..., bool] | None = field(default=None, repr=False)

    def execute(self, context: dict[str, Any] | None = None) -> bool:
        """Execute the remediation action if automated."""
        if self.remediation_type == RemediationType.MANUAL:
            self.status = RemediationStatus.MANUAL_REQUIRED
            logger.info("Action %s requires manual intervention", self.action_id)
            return False

        if self._executor is None:
            self.status = RemediationStatus.MANUAL_REQUIRED
            return False

        self.status = RemediationStatus.IN_PROGRESS
        try:
            success = self._executor(context or {})
            self.status = RemediationStatus.COMPLETED if success else RemediationStatus.FAILED
            return success
        except Exception as exc:
            logger.error("Remediation action %s failed: %s", self.action_id, exc)
            self.status = RemediationStatus.FAILED
            return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "control_id": self.control_id,
            "framework": self.framework.value,
            "title": self.title,
            "description": self.description,
            "remediation_type": self.remediation_type.value,
            "steps": self.steps,
            "status": self.status.value,
            "estimated_effort_hours": self.estimated_effort_hours,
            "priority": self.priority,
        }


@dataclass
class RemediationPlan:
    """A plan containing multiple remediation actions."""
    plan_id: str
    title: str
    framework: ComplianceFramework
    actions: list[RemediationAction] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_actions(self) -> int:
        return len(self.actions)

    @property
    def automated_actions(self) -> int:
        return sum(
            1 for a in self.actions
            if a.remediation_type == RemediationType.AUTOMATED
        )

    @property
    def total_effort_hours(self) -> float:
        return sum(a.estimated_effort_hours for a in self.actions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "framework": self.framework.value,
            "created_at": self.created_at.isoformat(),
            "summary": {
                "total_actions": self.total_actions,
                "automated_actions": self.automated_actions,
                "total_effort_hours": self.total_effort_hours,
            },
            "actions": [a.to_dict() for a in self.actions],
        }


# ─── Playbook Registry ──────────────────────────────────────────────────────


def generate_remediation_plan(
    results: list[ControlResult],
) -> RemediationPlan:
    """Generate a remediation plan from control evaluation results."""
    if not results:
        return RemediationPlan(
            plan_id="empty",
            title="No Remediation Needed",
            framework=ComplianceFramework.SOC2,
        )

    framework = results[0].framework
    actions: list[RemediationAction] = []

    for result in results:
        if result.status == ControlStatus.PASS:
            continue
        action = _create_action_for_failure(result)
        if action:
            actions.append(action)

    # Sort by priority (severity-based)
    actions.sort(key=lambda a: a.priority)

    plan_id = f"plan-{framework.value}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    return RemediationPlan(
        plan_id=plan_id,
        title=f"{framework.value} Remediation Plan",
        framework=framework,
        actions=actions,
    )


def _create_action_for_failure(result: ControlResult) -> RemediationAction | None:
    """Create a remediation action for a failed control."""
    priority = _severity_to_priority(result.severity)

    # Map control IDs to specific playbooks
    playbooks = {
        # SOC2
        "SOC2-CC6.1": _playbook_soc2_rbac,
        "SOC2-CC6.7": _playbook_soc2_encryption,
        "SOC2-CC8.1": _playbook_soc2_change_mgmt,
        "SOC2-CC7.4": _playbook_soc2_incident_response,
        # HIPAA
        "HIPAA-164.312(a)(1)": _playbook_hipaa_access,
        "HIPAA-164.404": _playbook_hipaa_breach,
        # GDPR
        "GDPR-Art7": _playbook_gdpr_consent,
        "GDPR-Art20": _playbook_gdpr_portability,
        "GDPR-Art17": _playbook_gdpr_erasure,
        # PCI-DSS
        "PCI-DSS-Req1": _playbook_pci_firewall,
        "PCI-DSS-Req4": _playbook_pci_encryption,
        "PCI-DSS-Req7": _playbook_pci_access,
        "PCI-DSS-Req6": _playbook_pci_vuln_mgmt,
    }

    playbook_fn = playbooks.get(result.control_id)
    if playbook_fn:
        return playbook_fn(result.control_id, priority)

    # Generic fallback
    return RemediationAction(
        action_id=f"generic-{result.control_id}",
        control_id=result.control_id,
        framework=result.framework,
        title=f"Remediate {result.control_id}",
        description=result.description,
        remediation_type=RemediationType.MANUAL,
        steps=[result.remediation or "Review and remediate this control."],
        estimated_effort_hours=4.0,
        priority=priority,
    )


def _severity_to_priority(severity: Severity) -> int:
    """Convert severity to priority (1 = highest)."""
    return {
        Severity.CRITICAL: 1,
        Severity.HIGH: 2,
        Severity.MEDIUM: 3,
        Severity.LOW: 4,
        Severity.INFO: 5,
    }.get(severity, 3)


# ─── SOC2 Playbooks ──────────────────────────────────────────────────────────


def _playbook_soc2_rbac(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"soc2-rbac-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.SOC2,
        title="Implement RBAC with Least Privilege",
        description="Deploy role-based access control and enforce multi-factor authentication",
        remediation_type=RemediationType.SEMI_AUTOMATED,
        steps=[
            "Inventory all user accounts and their current permissions",
            "Define roles based on job functions (admin, developer, auditor, etc.)",
            "Map permissions to roles following least-privilege principle",
            "Enable MFA for all user accounts",
            "Configure automated quarterly access reviews",
            "Document RBAC policy and assign ownership",
        ],
        estimated_effort_hours=16.0,
        priority=priority,
    )


def _playbook_soc2_encryption(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"soc2-encryption-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.SOC2,
        title="Enable AES-256 Encryption at Rest",
        description="Configure encryption for all data stores using industry-standard algorithms",
        remediation_type=RemediationType.AUTOMATED,
        steps=[
            "Identify all data stores (databases, file systems, object storage)",
            "Enable encryption at rest using AES-256-GCM",
            "Configure key management service (KMS) for key rotation",
            "Verify encryption status across all stores",
            "Document encryption configuration and key custody",
        ],
        estimated_effort_hours=8.0,
        priority=priority,
    )


def _playbook_soc2_change_mgmt(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"soc2-changemgmt-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.SOC2,
        title="Establish Change Management Process",
        description="Implement formal change approval, peer review, and testing gates",
        remediation_type=RemediationType.MANUAL,
        steps=[
            "Define change management policy and procedures",
            "Implement change approval workflow in deployment pipeline",
            "Require peer review for all production changes",
            "Provision separate test/staging environment",
            "Configure automated testing gates before production deployment",
            "Document rollback procedures for each change type",
        ],
        estimated_effort_hours=24.0,
        priority=priority,
    )


def _playbook_soc2_incident_response(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"soc2-ir-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.SOC2,
        title="Establish Incident Response Plan",
        description="Create and test an incident response plan with defined roles and SLAs",
        remediation_type=RemediationType.MANUAL,
        steps=[
            "Define incident severity levels and classification criteria",
            "Assign incident response team roles (lead, comms, technical, legal)",
            "Document escalation paths and contact information",
            "Establish 72-hour notification SLA for affected parties",
            "Schedule annual IR tabletop exercise",
            "Configure automated incident detection and alerting",
        ],
        estimated_effort_hours=20.0,
        priority=priority,
    )


# ─── HIPAA Playbooks ─────────────────────────────────────────────────────────


def _playbook_hipaa_access(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"hipaa-access-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.HIPAA,
        title="Implement HIPAA Access Controls",
        description="Deploy unique user identification, emergency access, and auto-logoff for ePHI",
        remediation_type=RemediationType.SEMI_AUTOMATED,
        steps=[
            "Assign unique user IDs for all users accessing ePHI",
            "Implement emergency access break-glass procedures",
            "Configure automatic logoff after 30 minutes of inactivity",
            "Enable encryption for all ePHI at rest and in transit",
            "Audit all access to ePHI systems",
        ],
        estimated_effort_hours=16.0,
        priority=priority,
    )


def _playbook_hipaa_breach(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"hipaa-breach-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.HIPAA,
        title="Establish Breach Notification Procedures",
        description="Create breach notification workflow with 60-day maximum timeline",
        remediation_type=RemediationType.MANUAL,
        steps=[
            "Document breach assessment and classification procedures",
            "Create notification templates for individuals, HHS, and media",
            "Establish 60-day maximum notification timeline",
            "Configure breach logging and tracking system",
            "Train staff on breach identification and escalation",
        ],
        estimated_effort_hours=12.0,
        priority=priority,
    )


# ─── GDPR Playbooks ──────────────────────────────────────────────────────────


def _playbook_gdpr_consent(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"gdpr-consent-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.GDPR,
        title="Implement Consent Management System",
        description="Deploy consent recording, withdrawal mechanisms, and explicit consent for sensitive data",
        remediation_type=RemediationType.SEMI_AUTOMATED,
        steps=[
            "Deploy consent management platform",
            "Record all consent with timestamps and method of collection",
            "Implement consent withdrawal mechanism (opt-out)",
            "Require explicit consent for sensitive data processing",
            "Configure consent expiration and re-consent workflows",
        ],
        estimated_effort_hours=20.0,
        priority=priority,
    )


def _playbook_gdpr_portability(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"gdpr-portability-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.GDPR,
        title="Implement Data Portability API",
        description="Provide data export in structured, machine-readable formats (JSON, CSV)",
        remediation_type=RemediationType.AUTOMATED,
        steps=[
            "Create data export API endpoint",
            "Support JSON and CSV export formats",
            "Implement automated export scheduling",
            "Verify exported data completeness and accuracy",
            "Document API for data subject access requests",
        ],
        estimated_effort_hours=12.0,
        priority=priority,
    )


def _playbook_gdpr_erasure(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"gdpr-erasure-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.GDPR,
        title="Implement Right to Erasure Workflow",
        description="Deploy data deletion workflows with 30-day SLA and verification",
        remediation_type=RemediationType.SEMI_AUTOMATED,
        steps=[
            "Map all locations where personal data is stored",
            "Implement cascading deletion across systems",
            "Configure 30-day maximum erasure timeline",
            "Add erasure verification and confirmation mechanism",
            "Document erasure procedures for audit trail",
        ],
        estimated_effort_hours=16.0,
        priority=priority,
    )


# ─── PCI-DSS Playbooks ───────────────────────────────────────────────────────


def _playbook_pci_firewall(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"pci-firewall-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.PCI_DSS,
        title="Configure Firewall for Cardholder Data Environment",
        description="Implement default-deny firewall rules restricting all traffic except explicitly allowed",
        remediation_type=RemediationType.AUTOMATED,
        steps=[
            "Document cardholder data environment network topology",
            "Implement default-deny firewall policy",
            "Allow only explicitly required protocols and ports",
            "Schedule firewall rule review every 6 months",
            "Configure firewall logging and alerting",
        ],
        estimated_effort_hours=12.0,
        priority=priority,
    )


def _playbook_pci_encryption(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"pci-encryption-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.PCI_DSS,
        title="Enforce TLS 1.2+ for Cardholder Data Transmission",
        description="Disable weak protocols and enforce strong cryptography for all transmissions",
        remediation_type=RemediationType.AUTOMATED,
        steps=[
            "Inventory all endpoints transmitting cardholder data",
            "Disable SSL, TLS 1.0, and TLS 1.1",
            "Configure TLS 1.2 or 1.3 as minimum",
            "Deploy valid TLS certificates from trusted CA",
            "Verify configuration with SSL/TLS scanning tools",
        ],
        estimated_effort_hours=8.0,
        priority=priority,
    )


def _playbook_pci_access(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"pci-access-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.PCI_DSS,
        title="Implement Need-to-Know Access Control",
        description="Deploy RBAC with least privilege for cardholder data environment",
        remediation_type=RemediationType.SEMI_AUTOMATED,
        steps=[
            "Inventory all users with access to cardholder data",
            "Define roles with minimum necessary access",
            "Implement need-to-know enforcement",
            "Conduct access reviews every 90 days",
            "Document access control matrix",
        ],
        estimated_effort_hours=16.0,
        priority=priority,
    )


def _playbook_pci_vuln_mgmt(control_id: str, priority: int) -> RemediationAction:
    return RemediationAction(
        action_id=f"pci-vuln-{control_id}",
        control_id=control_id,
        framework=ComplianceFramework.PCI_DSS,
        title="Establish Vulnerability Management Program",
        description="Deploy automated patch management and SAST/DAST security testing",
        remediation_type=RemediationType.SEMI_AUTOMATED,
        steps=[
            "Implement automated vulnerability scanning",
            "Define patch SLA: 30 days for critical vulnerabilities",
            "Integrate SAST into CI/CD pipeline",
            "Schedule quarterly DAST scans",
            "Document vulnerability remediation tracking process",
        ],
        estimated_effort_hours=20.0,
        priority=priority,
    )
