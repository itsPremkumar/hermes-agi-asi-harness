"""Safety Auditor — audit safety compliance and generate compliance reports.

Part of the Advanced Safety Module. The :class:`SafetyAuditor` records
compliance checks against :class:`ComplianceStandard` baselines, evaluates
enforcement/incident history, and produces :class:`AuditReport` objects with
findings, pass/fail metrics, and remediation recommendations.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from safety.incident_responder import Incident, IncidentLevel, IncidentResponder
from safety.risk_assessor import RiskLevel, RiskProfile
from safety.safety_enforcer import EnforcementResult, SafetyEnforcer

logger = logging.getLogger(__name__)

__all__ = [
    "AuditSeverity",
    "ComplianceStandard",
    "AuditFinding",
    "AuditReport",
    "SafetyAuditor",
]


class AuditSeverity(Enum):
    """Severity of an audit finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceStandard(Enum):
    """Compliance baselines the auditor can check against."""

    ISO_27001 = "iso_27001"
    SOC_2 = "soc_2"
    NIST_CSF = "nist_csf"
    INTERNAL = "internal"
    NONE = "none"


@dataclass
class AuditFinding:
    """A single finding from a compliance audit."""

    finding_id: str
    severity: AuditSeverity
    standard: ComplianceStandard
    category: str
    description: str
    impact: str
    recommendation: str
    status: str = "open"  # open | in_progress | resolved | accepted
    evidence: dict[str, Any] = field(default_factory=dict)
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity.value,
            "standard": self.standard.value,
            "category": self.category,
            "description": self.description,
            "impact": self.impact,
            "recommendation": self.recommendation,
            "status": self.status,
            "evidence": dict(self.evidence),
            "detected_at": self.detected_at,
        }


@dataclass
class AuditReport:
    """A compliance audit report."""

    report_id: str
    auditor: str
    standard: ComplianceStandard
    findings: list[AuditFinding] = field(default_factory=list)
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    overall_status: str = "pending"  # pending | pass | fail | warn
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AuditSeverity.CRITICAL)

    def by_severity(self, severity: AuditSeverity) -> list[AuditFinding]:
        return [f for f in self.findings if f.severity == severity]

    def pass_rate(self) -> float:
        if self.total_checks == 0:
            return 1.0
        return self.passed_checks / self.total_checks

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "auditor": self.auditor,
            "standard": self.standard.value,
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "overall_status": self.overall_status,
            "pass_rate": round(self.pass_rate(), 4),
            "findings": [f.to_dict() for f in self.findings],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


# A compliance check is a callable: (auditor, standard) -> AuditFinding | None
ComplianceCheck = Callable[["SafetyAuditor", ComplianceStandard], AuditFinding | None]


class SafetyAuditor:
    """Audits safety compliance and generates compliance reports."""

    def __init__(self, enforcer: SafetyEnforcer | None = None,
                 responder: IncidentResponder | None = None) -> None:
        self._enforcer = enforcer
        self._responder = responder
        self._reports: dict[str, AuditReport] = {}
        self._checks: dict[ComplianceStandard, list[ComplianceCheck]] = {}
        self._counter = 0

    # -- check registration -------------------------------------------------

    def add_check(self, standard: ComplianceStandard, check: ComplianceCheck) -> None:
        self._checks.setdefault(standard, []).append(check)

    def clear_checks(self) -> None:
        self._checks.clear()

    # -- report generation --------------------------------------------------

    def _next_report_id(self) -> str:
        self._counter += 1
        return f"audit-{self._counter:06d}"

    def audit(
        self,
        standard: ComplianceStandard = ComplianceStandard.INTERNAL,
        target_system: str = "unknown",
        profile: RiskProfile | None = None,
    ) -> AuditReport:
        """Run all registered checks for *standard* and return an AuditReport."""
        report = AuditReport(
            report_id=self._next_report_id(),
            auditor="SafetyAuditor",
            standard=standard,
            metadata={"target_system": target_system, "standard": standard.value},
        )

        findings: list[AuditFinding] = []

        # Standard: policy must be enforced on critical risks.
        def _check_policy_enforcement(auditor: "SafetyAuditor", std: ComplianceStandard) -> AuditFinding | None:
            report.total_checks += 1
            if auditor._enforcer is None:
                report.failed_checks += 1
                return AuditFinding(
                    finding_id=f"find-{report.total_findings + 1}",
                    severity=AuditSeverity.HIGH,
                    standard=std,
                    category="policy",
                    description="No safety enforcer attached to auditor",
                    impact="No policy enforcement observed; operations may be unsafe",
                    recommendation="Attach a SafetyEnforcer to the SafetyAuditor",
                )
            report.passed_checks += 1
            return None

        # Standard: blocked incidents must exist for past blocks.
        def _check_incident_coverage(auditor: "SafetyAuditor", std: ComplianceStandard) -> AuditFinding | None:
            report.total_checks += 1
            if auditor._responder is None:
                report.failed_checks += 1
                return AuditFinding(
                    finding_id=f"find-{report.total_findings + 1}",
                    severity=AuditSeverity.MEDIUM,
                    standard=std,
                    category="incident",
                    description="No incident responder attached to auditor",
                    impact="Blocked operations are not tracked as incidents",
                    recommendation="Attach an IncidentResponder to the SafetyAuditor",
                )
            report.passed_checks += 1
            return None

        # Standard: no unresolved critical incidents.
        def _check_no_unresolved_critical(auditor: "SafetyAuditor", std: ComplianceStandard) -> AuditFinding | None:
            report.total_checks += 1
            if auditor._responder is None:
                report.passed_checks += 1
                return None
            critical_open = [
                i for i in auditor._responder.active_incidents()
                if i.level == IncidentLevel.CRITICAL
            ]
            if critical_open:
                report.failed_checks += 1
                return AuditFinding(
                    finding_id=f"find-{report.total_findings + 1}",
                    severity=AuditSeverity.CRITICAL,
                    standard=std,
                    category="incident",
                    description=f"{len(critical_open)} unresolved critical incident(s)",
                    impact="Critical safety incidents remain unresolved",
                    recommendation="Resolve or escalate critical incidents immediately",
                    evidence={"incident_ids": [i.incident_id for i in critical_open]},
                )
            report.passed_checks += 1
            return None

        # Standard: risk profile has no CRITICAL risks.
        def _check_no_critical_risks(auditor: "SafetyAuditor", std: ComplianceStandard) -> AuditFinding | None:
            report.total_checks += 1
            if profile is None:
                report.passed_checks += 1
                return None
            critical_risks = [r for r in profile.risks if r.level == RiskLevel.CRITICAL]
            if critical_risks:
                report.failed_checks += 1
                return AuditFinding(
                    finding_id=f"find-{report.total_findings + 1}",
                    severity=AuditSeverity.CRITICAL,
                    standard=std,
                    category="risk",
                    description=f"{len(critical_risks)} critical risk(s) in profile",
                    impact="Critical risks may violate safety policy",
                    recommendation="Remediate or escalate critical risks",
                    evidence={"risk_ids": [r.risk_id for r in critical_risks]},
                )
            report.passed_checks += 1
            return None

        # Register defaults if none present for this standard.
        if standard not in self._checks or not self._checks[standard]:
            self._checks[standard] = [
                _check_policy_enforcement,
                _check_incident_coverage,
                _check_no_unresolved_critical,
                _check_no_critical_risks,
            ]

        for check in self._checks[standard]:
            finding = check(self, standard)
            if finding is not None:
                findings.append(finding)

        report.findings = findings
        report.failed_checks = report.total_checks - report.passed_checks
        report.updated_at = time.time()

        # Determine overall status.
        if report.critical_count > 0:
            report.overall_status = "fail"
        elif report.total_checks > 0 and report.failed_checks == report.total_checks:
            report.overall_status = "fail"
        elif report.failed_checks > 0:
            report.overall_status = "warn"
        else:
            report.overall_status = "pass"

        self._reports[report.report_id] = report
        logger.info(
            "Audit %s: %d findings, %d/%d checks passed, status=%s",
            report.report_id, report.total_findings, report.passed_checks,
            report.total_checks, report.overall_status,
        )
        return report

    def get_report(self, report_id: str) -> AuditReport | None:
        return self._reports.get(report_id)

    def list_reports(self) -> list[AuditReport]:
        return list(self._reports.values())

    def compliance_summary(self) -> dict[str, Any]:
        """Aggregate summary across all reports."""
        reports = self._reports.values()
        return {
            "total_reports": len(self._reports),
            "total_findings": sum(len(r.findings) for r in reports),
            "total_critical": sum(r.critical_count for r in reports),
            "overall_pass_rate": round(
                sum(r.pass_rate() for r in reports) / len(reports) if reports else 1.0, 4
            ),
            "by_status": {
                r.report_id: r.overall_status for r in reports
            },
        }
