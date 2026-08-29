"""Policy library — compliance controls for SOC2, HIPAA, GDPR, and PCI-DSS."""

from __future__ import annotations

import logging
from typing import Any

from compliance_as_code.engine import (
    BaseControl,
    ComplianceFramework,
    ControlResult,
    ControlStatus,
    Severity,
)

logger = logging.getLogger(__name__)


# ─── SOC2 Controls ──────────────────────────────────────────────────────────


class SOC2LogicalAccessControl(BaseControl):
    """CC6.1 — Logical and physical access controls."""

    def __init__(self):
        super().__init__(
            control_id="SOC2-CC6.1",
            framework=ComplianceFramework.SOC2,
            description="Logical access to system components is restricted through role-based access control (RBAC) and least-privilege principles.",
            severity=Severity.HIGH,
            remediation="Implement RBAC with least-privilege access. Review and revoke excessive permissions quarterly.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        rbac_enabled = context.get("rbac_enabled", False)
        mfa_enforced = context.get("mfa_enforced", False)
        access_reviews = context.get("access_reviews_conducted", False)

        evidence = []
        if rbac_enabled:
            evidence.append("RBAC is enabled")
        if mfa_enforced:
            evidence.append("MFA is enforced for all users")
        if access_reviews:
            evidence.append("Quarterly access reviews are conducted")

        if rbac_enabled and mfa_enforced and access_reviews:
            status = ControlStatus.PASS
        elif rbac_enabled or mfa_enforced:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


class SOC2EncryptionAtRestControl(BaseControl):
    """CC6.7 — Encryption of data at rest."""

    def __init__(self):
        super().__init__(
            control_id="SOC2-CC6.7",
            framework=ComplianceFramework.SOC2,
            description="Data at rest is encrypted using industry-standard algorithms (AES-256 or equivalent).",
            severity=Severity.CRITICAL,
            remediation="Enable encryption at rest for all data stores using AES-256-GCM or equivalent.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        encryption_enabled = context.get("encryption_at_rest", False)
        algorithm = context.get("encryption_algorithm", "")
        key_management = context.get("key_management", "")

        evidence = []
        if encryption_enabled:
            evidence.append(f"Encryption enabled with algorithm: {algorithm}")
        if key_management:
            evidence.append(f"Key management: {key_management}")

        if encryption_enabled and algorithm in ("AES-256-GCM", "AES-256", "ChaCha20-Poly1305"):
            status = ControlStatus.PASS
        elif encryption_enabled:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


class SOC2ChangeManagementControl(BaseControl):
    """CC8.1 — Change management and authorization."""

    def __init__(self):
        super().__init__(
            control_id="SOC2-CC8.1",
            framework=ComplianceFramework.SOC2,
            description="System changes are authorized, tested, tested in a non-production environment, and approved before deployment to production.",
            severity=Severity.HIGH,
            remediation="Implement a formal change management process with peer review, testing gates, and approval workflows.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        change_approval = context.get("change_approval_required", False)
        peer_review = context.get("peer_review_required", False)
        test_env = context.get("test_environment_separate", False)

        evidence = []
        if change_approval:
            evidence.append("Change approval process is enforced")
        if peer_review:
            evidence.append("Peer review is required for all changes")
        if test_env:
            evidence.append("Separate test environment is used")

        if change_approval and peer_review and test_env:
            status = ControlStatus.PASS
        elif change_approval or peer_review:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


class SOC2IncidentResponseControl(BaseControl):
    """CC7.4 — Incident response and notification."""

    def __init__(self):
        super().__init__(
            control_id="SOC2-CC7.4",
            framework=ComplianceFramework.SOC2,
            description="The entity responds to identified security incidents by executing an incident response plan and notifying affected parties within defined timelines.",
            severity=Severity.CRITICAL,
            remediation="Establish and document an incident response plan with defined roles, escalation paths, and notification timelines.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        ir_plan = context.get("incident_response_plan", False)
        ir_testing = context.get("ir_plan_tested", False)
        notification_sla = context.get("notification_sla_hours", 999)

        evidence = []
        if ir_plan:
            evidence.append("Incident response plan is documented")
        if ir_testing:
            evidence.append("IR plan has been tested within the last 12 months")
        if notification_sla <= 72:
            evidence.append(f"Notification SLA: {notification_sla} hours")

        if ir_plan and ir_testing and notification_sla <= 72:
            status = ControlStatus.PASS
        elif ir_plan:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


# ─── HIPAA Controls ─────────────────────────────────────────────────────────


class HIPAASafeguardsControl(BaseControl):
    """164.312(a)(1) — Access Control."""

    def __init__(self):
        super().__init__(
            control_id="HIPAA-164.312(a)(1)",
            framework=ComplianceFramework.HIPAA,
            description="Implement technical policies and procedures for electronic information systems that maintain ePHI to allow access only to those persons or software programs that have been granted access rights.",
            severity=Severity.CRITICAL,
            remediation="Implement unique user identification, emergency access procedures, automatic logoff, and encryption/decryption for ePHI.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        unique_users = context.get("unique_user_ids", False)
        emergency_access = context.get("emergency_access_procedure", False)
        auto_logoff = context.get("auto_logoff_minutes", 0)
        ephi_encrypted = context.get("ephi_encrypted", False)

        evidence = []
        if unique_users:
            evidence.append("Unique user identification is enforced")
        if emergency_access:
            evidence.append("Emergency access procedure is documented")
        if auto_logoff > 0 and auto_logoff <= 30:
            evidence.append(f"Auto logoff after {auto_logoff} minutes of inactivity")
        if ephi_encrypted:
            evidence.append("ePHI is encrypted at rest and in transit")

        if unique_users and emergency_access and auto_logoff <= 30 and ephi_encrypted:
            status = ControlStatus.PASS
        elif unique_users and ephi_encrypted:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


class HIPAABreachNotificationControl(BaseControl):
    """164.404 — Notification to individuals."""

    def __init__(self):
        super().__init__(
            control_id="HIPAA-164.404",
            framework=ComplianceFramework.HIPAA,
            description="In the case of a breach of unsecured PHI, the covered entity shall notify each individual whose unsecured PHI has been accessed, acquired, used, or disclosed.",
            severity=Severity.CRITICAL,
            remediation="Establish breach notification procedures with 60-day maximum notification timeline.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        breach_procedure = context.get("breach_notification_procedure", False)
        notification_timeline = context.get("breach_notification_days", 999)
        breach_log = context.get("breach_log_maintained", False)

        evidence = []
        if breach_procedure:
            evidence.append("Breach notification procedure is documented")
        if notification_timeline <= 60:
            evidence.append(f"Notification timeline: {notification_timeline} days")
        if breach_log:
            evidence.append("Breach log is maintained")

        if breach_procedure and notification_timeline <= 60 and breach_log:
            status = ControlStatus.PASS
        elif breach_procedure:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


# ─── GDPR Controls ──────────────────────────────────────────────────────────


class GDPRConsentControl(BaseControl):
    """Art. 7 — Conditions for consent."""

    def __init__(self):
        super().__init__(
            control_id="GDPR-Art7",
            framework=ComplianceFramework.GDPR,
            description="Where processing is based on consent, the controller shall be able to demonstrate that the data subject has consented to processing of their personal data.",
            severity=Severity.HIGH,
            remediation="Implement a consent management system that records when, how, and what consent was given.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        consent_records = context.get("consent_records_maintained", False)
        consent_withdrawal = context.get("consent_withdrawal_mechanism", False)
        explicit_consent = context.get("explicit_consent_required", False)

        evidence = []
        if consent_records:
            evidence.append("Consent records are maintained with timestamps")
        if consent_withdrawal:
            evidence.append("Consent withdrawal mechanism is available")
        if explicit_consent:
            evidence.append("Explicit consent is required for sensitive data")

        if consent_records and consent_withdrawal and explicit_consent:
            status = ControlStatus.PASS
        elif consent_records:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


class GDPRDataPortabilityControl(BaseControl):
    """Art. 20 — Right to data portability."""

    def __init__(self):
        super().__init__(
            control_id="GDPR-Art20",
            framework=ComplianceFramework.GDPR,
            description="The data subject shall have the right to receive the personal data concerning them in a structured, commonly used and machine-readable format.",
            severity=Severity.MEDIUM,
            remediation="Implement data export functionality in standard formats (JSON, CSV).",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        export_formats = context.get("data_export_formats", [])
        export_api = context.get("data_export_api", False)
        export_automated = context.get("automated_export", False)

        evidence = []
        if export_formats:
            evidence.append(f"Export formats available: {', '.join(export_formats)}")
        if export_api:
            evidence.append("Data export API is available")
        if export_automated:
            evidence.append("Automated data export is supported")

        if export_api and len(export_formats) >= 2 and export_automated:
            status = ControlStatus.PASS
        elif export_api or export_formats:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


class GDPRRightToErasureControl(BaseControl):
    """Art. 17 — Right to erasure (right to be forgotten)."""

    def __init__(self):
        super().__init__(
            control_id="GDPR-Art17",
            framework=ComplianceFramework.GDPR,
            description="The data subject shall have the right to obtain from the controller the erasure of personal data without undue delay.",
            severity=Severity.HIGH,
            remediation="Implement data deletion workflows that can completely remove a data subject's personal data.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        erasure_procedure = context.get("erasure_procedure", False)
        erasure_timeline = context.get("erasure_timeline_days", 999)
        erasure_verification = context.get("erasure_verification", False)

        evidence = []
        if erasure_procedure:
            evidence.append("Erasure procedure is documented")
        if erasure_timeline <= 30:
            evidence.append(f"Erasure timeline: {erasure_timeline} days")
        if erasure_verification:
            evidence.append("Erasure verification is performed")

        if erasure_procedure and erasure_timeline <= 30 and erasure_verification:
            status = ControlStatus.PASS
        elif erasure_procedure:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


# ─── PCI-DSS Controls ───────────────────────────────────────────────────────


class PCIDSSFirewallControl(BaseControl):
    """Req 1 — Install and maintain a firewall configuration."""

    def __init__(self):
        super().__init__(
            control_id="PCI-DSS-Req1",
            framework=ComplianceFramework.PCI_DSS,
            description="Install and maintain a firewall configuration to protect cardholder data, restricting connections between untrusted networks and any system in the cardholder data environment.",
            severity=Severity.CRITICAL,
            remediation="Implement and document firewall rules that restrict all traffic except explicitly allowed protocols.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        firewall_enabled = context.get("firewall_enabled", False)
        default_deny = context.get("default_deny_policy", False)
        firewall_reviewed = context.get("firewall_rules_reviewed", False)

        evidence = []
        if firewall_enabled:
            evidence.append("Firewall is enabled at network boundaries")
        if default_deny:
            evidence.append("Default-deny policy is in place")
        if firewall_reviewed:
            evidence.append("Firewall rules are reviewed at least every 6 months")

        if firewall_enabled and default_deny and firewall_reviewed:
            status = ControlStatus.PASS
        elif firewall_enabled:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


class PCIDSSDataEncryptionControl(BaseControl):
    """Req 4 — Encrypt transmission of cardholder data."""

    def __init__(self):
        super().__init__(
            control_id="PCI-DSS-Req4",
            framework=ComplianceFramework.PCI_DSS,
            description="Use strong cryptography and security protocols to safeguard sensitive cardholder data during transmission over open, public networks.",
            severity=Severity.CRITICAL,
            remediation="Enforce TLS 1.2+ for all transmissions of cardholder data. Disable SSL and early TLS versions.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        tls_version = context.get("tls_version", "")
        weak_disabled = context.get("weak_protocols_disabled", False)
        cert_valid = context.get("certificate_valid", False)

        evidence = []
        if tls_version:
            evidence.append(f"TLS version: {tls_version}")
        if weak_disabled:
            evidence.append("Weak protocols (SSL, TLS 1.0/1.1) are disabled")
        if cert_valid:
            evidence.append("Valid TLS certificate is in use")

        if tls_version in ("1.2", "1.3") and weak_disabled and cert_valid:
            status = ControlStatus.PASS
        elif tls_version in ("1.2", "1.3"):
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


class PCIDSSAccessControlControl(BaseControl):
    """Req 7 — Restrict access to cardholder data."""

    def __init__(self):
        super().__init__(
            control_id="PCI-DSS-Req7",
            framework=ComplianceFramework.PCI_DSS,
            description="Limit access to system components and cardholder data only to those individuals whose job requires such access, using need-to-know principles.",
            severity=Severity.CRITICAL,
            remediation="Implement role-based access control with least privilege for all systems in the cardholder data environment.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        rbac = context.get("rbac_enabled", False)
        need_to_know = context.get("need_to_know_enforced", False)
        access_review = context.get("access_review_frequency_days", 999)

        evidence = []
        if rbac:
            evidence.append("Role-based access control is implemented")
        if need_to_know:
            evidence.append("Need-to-know principle is enforced")
        if access_review <= 90:
            evidence.append(f"Access reviews conducted every {access_review} days")

        if rbac and need_to_know and access_review <= 90:
            status = ControlStatus.PASS
        elif rbac:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


class PCIDSSVulnerabilityManagementControl(BaseControl):
    """Req 6 — Develop and maintain secure systems."""

    def __init__(self):
        super().__init__(
            control_id="PCI-DSS-Req6",
            framework=ComplianceFramework.PCI_DSS,
            description="Ensure that all system components and software are protected from known vulnerabilities by installing applicable security patches and following secure development practices.",
            severity=Severity.HIGH,
            remediation="Implement automated patch management and vulnerability scanning with defined SLAs for remediation.",
        )

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        patch_sla = context.get("patch_sla_days", 999)
        vuln_scanning = context.get("vulnerability_scanning", False)
        secure_dev = context.get("secure_development_practices", False)

        evidence = []
        if patch_sla <= 30:
            evidence.append(f"Patch SLA: {patch_sla} days")
        if vuln_scanning:
            evidence.append("Regular vulnerability scanning is performed")
        if secure_dev:
            evidence.append("Secure development practices (SAST/DAST) are in place")

        if patch_sla <= 30 and vuln_scanning and secure_dev:
            status = ControlStatus.PASS
        elif vuln_scanning:
            status = ControlStatus.WARNING
        else:
            status = ControlStatus.FAIL

        return ControlResult(
            control_id=self.control_id,
            framework=self.framework,
            status=status,
            description=self.description,
            evidence=evidence,
            severity=self.severity,
            remediation=self.remediation,
        )


# ─── Registry ───────────────────────────────────────────────────────────────


def get_all_controls() -> list[BaseControl]:
    """Return all available compliance controls."""
    return [
        # SOC2
        SOC2LogicalAccessControl(),
        SOC2EncryptionAtRestControl(),
        SOC2ChangeManagementControl(),
        SOC2IncidentResponseControl(),
        # HIPAA
        HIPAASafeguardsControl(),
        HIPAABreachNotificationControl(),
        # GDPR
        GDPRConsentControl(),
        GDPRDataPortabilityControl(),
        GDPRRightToErasureControl(),
        # PCI-DSS
        PCIDSSFirewallControl(),
        PCIDSSDataEncryptionControl(),
        PCIDSSAccessControlControl(),
        PCIDSSVulnerabilityManagementControl(),
    ]


def get_controls_by_framework(framework: ComplianceFramework) -> list[BaseControl]:
    """Return controls filtered by framework."""
    return [c for c in get_all_controls() if c.framework == framework]
