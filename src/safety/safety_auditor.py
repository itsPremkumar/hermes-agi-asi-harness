"""Safety Auditor — Audit safety compliance and generate reports."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class AuditStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


# Alias for backward compatibility
class AuditSeverity(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceStandard(str, Enum):
    INTERNAL = "internal"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    NIST_CSF = "nist_csf"
    NIST = "nist"
    CIS = "cis"
    SOC_2 = "soc2"
    CUSTOM = "custom"


@dataclass
class AuditFinding:
    finding_id: str
    title: str
    status: AuditStatus
    description: str
    recommendation: str
    severity: AuditSeverity = AuditStatus.PASS
    timestamp: float = field(default_factory=time.time)


@dataclass
class AuditReport:
    report_id: str
    title: str = ""
    standard: ComplianceStandard = ComplianceStandard.INTERNAL
    findings: list[AuditFinding] = field(default_factory=list)
    overall_status: str = "pass"
    passed_checks: int = 0
    total_checks: int = 0
    pass_rate: float = 1.0
    created_at: float = field(default_factory=time.time)

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.findings if f.status == AuditStatus.FAIL)

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.findings if f.status == AuditStatus.PASS)

    @property
    def overall_pass(self) -> bool:
        return self.fail_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "title": self.title,
            "standard": self.standard.value,
            "overall_status": self.overall_status,
            "passed_checks": self.passed_checks,
            "total_checks": self.total_checks,
            "pass_rate": self.pass_rate,
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "title": f.title,
                    "status": f.status.value,
                    "severity": f.severity.value,
                    "description": f.description,
                }
                for f in self.findings
            ],
        }


class SafetyAuditor:
    def __init__(self, enforcer=None, responder=None):
        self._reports: list[AuditReport] = []
        self._enforcer = enforcer
        self._responder = responder
        self._checks: dict[ComplianceStandard, list] = {}
        
        # Register default checks
        self._checks[ComplianceStandard.INTERNAL] = [
            self._check_critical_risk,
            self._check_unresolved_critical_incidents,
        ]
    
    def _check_critical_risk(self, standard: ComplianceStandard, profile=None):
        """Check for critical risk levels."""
        if profile and hasattr(profile, 'overall_level'):
            level = profile.overall_level
            if hasattr(level, 'value'):
                level = level.value
            if level == 'critical':
                return AuditFinding(
                    finding_id=f"f-{uuid.uuid4().hex[:8]}",
                    title="Critical risk level detected",
                    status=AuditStatus.FAIL,
                    description="System has critical risk level",
                    recommendation="Review and mitigate critical risks",
                    severity=AuditSeverity.CRITICAL,
                )
        return None
    
    def _check_unresolved_critical_incidents(self, standard: ComplianceStandard, profile=None):
        """Check for unresolved critical incidents."""
        if self._responder:
            critical_active = [
                i for i in self._responder.active_incidents()
                if i.level.value == 'critical'
            ]
            if critical_active:
                return AuditFinding(
                    finding_id=f"f-{uuid.uuid4().hex[:8]}",
                    title="Unresolved critical incidents",
                    status=AuditStatus.FAIL,
                    description=f"{len(critical_active)} critical incidents unresolved",
                    recommendation="Resolve critical incidents immediately",
                    severity=AuditSeverity.CRITICAL,
                )
        return None

    def audit(self, standard: ComplianceStandard, target_system: str, profile=None) -> AuditReport:
        """Run audit against a compliance standard."""
        findings = []
        checks = self._checks.get(standard, [])
        
        for check_fn in checks:
            result = check_fn(standard, profile)
            if result:
                findings.append(result)
        
        # If no enforcer, we can't fully assess
        if self._enforcer is None:
            findings.append(AuditFinding(
                finding_id=f"f-{uuid.uuid4().hex[:8]}",
                title="No enforcer configured",
                status=AuditStatus.WARN,
                description="Safety enforcer not available for audit",
                recommendation="Configure safety enforcer",
                severity=AuditStatus.WARN,
            ))
        
        total_checks = len(checks) + (0 if self._enforcer else 1)
        passed_checks = total_checks - len(findings)
        
        # Determine overall status
        if any(f.status == AuditStatus.FAIL for f in findings):
            overall_status = "fail"
        elif any(f.status == AuditStatus.WARN for f in findings):
            overall_status = "warn"
        else:
            overall_status = "pass"
        
        report = AuditReport(
            report_id=f"audit-{uuid.uuid4().hex[:8]}",
            title=f"Audit: {standard.value} for {target_system}",
            standard=standard,
            findings=findings,
            overall_status=overall_status,
            passed_checks=passed_checks,
            total_checks=total_checks,
            pass_rate=passed_checks / total_checks if total_checks > 0 else 1.0,
        )
        self._reports.append(report)
        return report

    def get_report(self, report_id: str) -> AuditReport | None:
        return next((r for r in self._reports if r.report_id == report_id), None)

    def list_reports(self) -> list[AuditReport]:
        return list(self._reports)

    def compliance_summary(self) -> dict:
        """Get compliance summary across all reports."""
        total = len(self._reports)
        total_critical = sum(
            1 for r in self._reports
            for f in r.findings if f.severity == AuditStatus.FAIL
        )
        return {
            "total_reports": total,
            "total_critical": total_critical,
            "passing_reports": sum(1 for r in self._reports if r.overall_status == "pass"),
        }

    def create_report(self, title: str) -> str:
        report_id = f"audit-{int(time.time() * 1000)}"
        report = AuditReport(report_id=report_id, title=title)
        self._reports.append(report)
        return report_id

    def add_finding(
        self,
        report_id: str,
        title: str,
        status: AuditStatus,
        description: str,
        recommendation: str,
    ) -> None:
        report = self.get_report(report_id)
        if report:
            report.findings.append(AuditFinding(
                finding_id=f"f-{len(report.findings)}",
                title=title,
                status=status,
                description=description,
                recommendation=recommendation,
            ))

    def summary(self, report_id: str) -> dict:
        report = self.get_report(report_id)
        if not report:
            return {"error": "report not found"}
        return {
            "title": report.title,
            "total": len(report.findings),
            "pass": report.pass_count,
            "fail": report.fail_count,
            "overall_pass": report.overall_pass,
        }
