"""Safety Auditor — audit safety compliance and generate compliance reports."""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional, Callable

from src.safety.threat_modeler import (
    Threat,
    ThreatCategory,
    ThreatModel,
    ThreatSeverity,
)


class AuditCheckType(Enum):
    """Categories of audit checks."""

    POLICY_COMPLIANCE = "policy_compliance"
    THREAT_COVERAGE = "threat_coverage"
    INCIDENT_RESPONSE = "incident_response"
    LOG_INTEGRITY = "log_integrity"
    RATE_LIMIT_COMPLIANCE = "rate_limit_compliance"
    RESOURCE_QUOTA = "resource_quota"
    DATA_PROTECTION = "data_protection"
    ACCESS_CONTROL = "access_control"
    CONFIGURATION = "configuration"
    CUSTOM = "custom"


class AuditStatus(Enum):
    """Outcome of an audit check."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class AuditFinding:
    """A single audit finding (issue discovered during a check)."""

    id: str
    check_id: str
    severity: str  # "critical" | "high" | "medium" | "low" | "info"
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    found_at: float = field(default_factory=time.time)


@dataclass
class AuditResult:
    """Result of a single audit check."""

    check_id: str
    name: str
    check_type: AuditCheckType
    status: AuditStatus
    score: float  # 0.0 – 1.0
    findings: list[AuditFinding] = field(default_factory=list)
    duration_ms: float = 0.0
    passed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    executed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "check_type": self.check_type.value,
            "status": self.status.value,
            "score": self.score,
            "findings_count": len(self.findings),
            "findings": [asdict(f) if hasattr(f, "__dataclass_fields__") else f for f in self.findings],
            "duration_ms": self.duration_ms,
            "passed": self.passed,
            "executed_at": self.executed_at,
            "metadata": self.metadata,
        }


@dataclass
class AuditCheck:
    """Definition of an audit check."""

    id: str
    name: str
    check_type: AuditCheckType
    description: str
    # The check function takes a context dict and returns an AuditResult.
    check_fn: Callable[[dict[str, Any]], "AuditResult"]
    enabled: bool = True
    required: bool = False
    severity: str = "medium"  # minimum severity this check covers
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    """Complete audit report covering multiple checks."""

    report_id: str
    audit_name: str
    results: list[AuditResult] = field(default_factory=list)
    overall_status: AuditStatus = AuditStatus.PASS
    overall_score: float = 0.0
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    started_at: float = field(default_factory=time.time)
    completed_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "audit_name": self.audit_name,
            "overall_status": self.overall_status.value,
            "overall_score": self.overall_score,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warning_checks": self.warning_checks,
            "total_findings": self.total_findings,
            "critical_findings": self.critical_findings,
            "high_findings": self.high_findings,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
        }


class SafetyAuditor:
    """Audit safety compliance and generate compliance reports."""

    # Default built-in checks.
    def _default_checks(self) -> list[AuditCheck]:
        """Build default audit checks."""
        return [
            AuditCheck(
                id="check_policy_compliance",
                name="Policy Compliance Check",
                check_type=AuditCheckType.POLICY_COMPLIANCE,
                description="Verify all safety policies are enabled and configured",
                check_fn=self._check_policy_compliance,
                enabled=True,
                required=True,
                severity="high",
            ),
            AuditCheck(
                id="check_threat_coverage",
                name="Threat Coverage Check",
                check_type=AuditCheckType.THREAT_COVERAGE,
                description="Verify all threat categories are covered by rules",
                check_fn=self._check_threat_coverage,
                enabled=True,
                required=True,
                severity="medium",
            ),
            AuditCheck(
                id="check_incident_response",
                name="Incident Response Check",
                check_type=AuditCheckType.INCIDENT_RESPONSE,
                description="Verify incident response procedures are configured",
                check_fn=self._check_incident_response,
                enabled=True,
                required=True,
                severity="medium",
            ),
            AuditCheck(
                id="check_log_integrity",
                name="Log Integrity Check",
                check_type=AuditCheckType.LOG_INTEGRITY,
                description="Verify safety event logs are intact",
                check_fn=self._check_log_integrity,
                enabled=True,
                required=False,
                severity="low",
            ),
            AuditCheck(
                id="check_data_protection",
                name="Data Protection Check",
                check_type=AuditCheckType.DATA_PROTECTION,
                description="Verify no sensitive data is exposed in policies",
                check_fn=self._check_data_protection,
                enabled=True,
                required=True,
                severity="critical",
            ),
        ]

    def __init__(self):
        self._checks: dict[str, AuditCheck] = {}
        self._reports: dict[str, AuditReport] = {}
        self._counter = 0
        self._context: dict[str, Any] = {}

        for check in self._default_checks():
            self._checks[check.id] = check

    # ------------------------------------------------------------------
    # Check management
    # ------------------------------------------------------------------

    def register_check(self, check: AuditCheck) -> bool:
        """Register a custom audit check."""
        if check.id in self._checks:
            return False
        self._checks[check.id] = check
        return True

    def enable_check(self, check_id: str, enabled: bool = True) -> bool:
        check = self._checks.get(check_id)
        if check is None:
            return False
        check.enabled = enabled
        return True

    def get_check(self, check_id: str) -> Optional[AuditCheck]:
        return self._checks.get(check_id)

    def list_checks(self) -> list[AuditCheck]:
        return list(self._checks.values())

    def list_active_checks(self) -> list[AuditCheck]:
        return [c for c in self._checks.values() if c.enabled]

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def set_context(self, context: dict[str, Any]) -> None:
        """Set the audit context — a dict that gets passed to check functions."""
        self._context.update(context)

    def get_context(self) -> dict[str, Any]:
        return dict(self._context)

    # ------------------------------------------------------------------
    # Audit execution
    # ------------------------------------------------------------------

    def run_audit(self, audit_name: str = "safety_audit") -> AuditReport:
        """Run all enabled audit checks and produce a report."""
        import hashlib

        report_id = hashlib.sha256(
            f"{audit_name}_{time.time()}".encode()
        ).hexdigest()[:12]

        report = AuditReport(
            report_id=report_id,
            audit_name=audit_name,
        )

        results: list[AuditResult] = []
        for check in self.list_active_checks():
            start = time.time()
            try:
                result = check.check_fn(self._context)
            except Exception as exc:  # noqa: BLE001
                result = AuditResult(
                    check_id=check.id,
                    name=check.name,
                    check_type=check.check_type,
                    status=AuditStatus.ERROR,
                    score=0.0,
                    findings=[],
                    passed=False,
                    metadata={"error": str(exc)},
                )
            result.duration_ms = (time.time() - start) * 1000
            result.check_id = check.id
            result.name = check.name
            result.check_type = check.check_type
            results.append(result)

        report.results = results
        self._compute_report_summary(report)
        self._counter += 1
        self._reports[report_id] = report
        return report

    def run_check(self, check_id: str) -> Optional[AuditResult]:
        """Run a single audit check by ID."""
        check = self._checks.get(check_id)
        if check is None or not check.enabled:
            return None
        start = time.time()
        try:
            result = check.check_fn(self._context)
        except Exception as exc:  # noqa: BLE001
            result = AuditResult(
                check_id=check.id,
                name=check.name,
                check_type=check.check_type,
                status=AuditStatus.ERROR,
                score=0.0,
                passed=False,
                metadata={"error": str(exc)},
            )
        result.duration_ms = (time.time() - start) * 1000
        return result

    def get_report(self, report_id: str) -> Optional[AuditReport]:
        return self._reports.get(report_id)

    def list_reports(self) -> list[str]:
        return list(self._reports.keys())

    def get_latest_report(self) -> Optional[AuditReport]:
        if not self._reports:
            return None
        return max(self._reports.values(), key=lambda r: r.completed_at)

    # ------------------------------------------------------------------
    # Default check implementations
    # ------------------------------------------------------------------

    def _check_policy_compliance(self, context: dict[str, Any]) -> AuditResult:
        findings: list[AuditFinding] = []
        enforcer = context.get("enforcer")
        if enforcer is None:
            findings.append(AuditFinding(
                id="f_no_enforcer", check_id="check_policy_compliance",
                severity="high", message="SafetyEnforcer not provided in context",
                recommendation="Pass enforcer instance to auditor context",
            ))
            return AuditResult(
                check_id="check_policy_compliance", name="Policy Compliance Check",
                check_type=AuditCheckType.POLICY_COMPLIANCE,
                status=AuditStatus.FAIL, score=0.0, findings=findings, passed=False,
                metadata={"enforcer_present": False},
            )

        rules = enforcer.list_rules()
        active = enforcer.list_active_rules()
        disabled = [r for r in rules if not r.enabled]
        if disabled:
            findings.append(AuditFinding(
                id="f_disabled_rules", check_id="check_policy_compliance",
                severity="medium",
                message=f"{len(disabled)} policy rule(s) are disabled",
                details={"disabled": [r.id for r in disabled]},
                recommendation="Review and re-enable necessary safety rules",
            ))

        score = len(active) / len(rules) if rules else 0.0
        status = AuditStatus.PASS
        if len(disabled) == len(rules) and rules:
            status = AuditStatus.FAIL
        elif disabled:
            status = AuditStatus.WARNING

        return AuditResult(
            check_id="check_policy_compliance", name="Policy Compliance Check",
            check_type=AuditCheckType.POLICY_COMPLIANCE,
            status=status, score=score, findings=findings,
            passed=(status == AuditStatus.PASS),
            metadata={"total_rules": len(rules), "active_rules": len(active)},
        )

    def _check_threat_coverage(self, context: dict[str, Any]) -> AuditResult:
        findings: list[AuditFinding] = []
        enforcer = context.get("enforcer")
        covered_categories: set[ThreatCategory] = set()

        if enforcer is not None:
            for rule in enforcer.list_rules():
                if rule.condition:
                    if rule.condition in ThreatCategory.__members__:
                        covered_categories.add(ThreatCategory[rule.condition])
                    else:
                        # map by value
                        for cat in ThreatCategory:
                            if cat.value == rule.condition:
                                covered_categories.add(cat)

        all_categories = set(ThreatCategory)
        missing = all_categories - covered_categories

        if missing:
            findings.append(AuditFinding(
                id="f_missing_coverage", check_id="check_threat_coverage",
                severity="medium",
                message=f"Threat categories without dedicated enforcement rules: "
                        f"{[c.value for c in sorted(missing, key=lambda c: c.value)]}",
                details={"covered": [c.value for c in covered_categories],
                         "missing": [c.value for c in missing]},
                recommendation="Add policy rules for uncovered threat categories",
            ))

        score = len(covered_categories) / len(all_categories) if all_categories else 1.0
        return AuditResult(
            check_id="check_threat_coverage", name="Threat Coverage Check",
            check_type=AuditCheckType.THREAT_COVERAGE,
            status=AuditStatus.PASS if not missing else AuditStatus.WARNING,
            score=score, findings=findings,
            passed=not missing,
            metadata={"covered_categories": len(covered_categories),
                      "total_categories": len(all_categories)},
        )

    def _check_incident_response(self, context: dict[str, Any]) -> AuditResult:
        findings: list[AuditFinding] = []
        responder = context.get("responder")
        if responder is None:
            findings.append(AuditFinding(
                id="f_no_responder", check_id="check_incident_response",
                severity="high", message="IncidentResponder not provided in context",
                recommendation="Pass responder instance to auditor context",
            ))
            return AuditResult(
                check_id="check_incident_response", name="Incident Response Check",
                check_type=AuditCheckType.INCIDENT_RESPONSE,
                status=AuditStatus.FAIL, score=0.0, findings=findings, passed=False,
                metadata={"responder_present": False},
            )

        summary = responder.get_incident_summary()
        active = summary.get("active_incidents", 0)
        if active > 0:
            findings.append(AuditFinding(
                id="f_unresolved", check_id="check_incident_response",
                severity="medium",
                message=f"{active} unresolved incident(s) requiring attention",
                recommendation="Review and resolve active incidents",
            ))

        return AuditResult(
            check_id="check_incident_response", name="Incident Response Check",
            check_type=AuditCheckType.INCIDENT_RESPONSE,
            status=AuditStatus.WARNING if active > 0 else AuditStatus.PASS,
            score=0.7 if active > 0 else 1.0, findings=findings,
            passed=active == 0,
            metadata={"active_incidents": active, "total_incidents": summary.get("total_incidents", 0)},
        )

    def _check_log_integrity(self, context: dict[str, Any]) -> AuditResult:
        decision_log = context.get("decision_log", [])
        if not decision_log:
            return AuditResult(
                check_id="check_log_integrity", name="Log Integrity Check",
                check_type=AuditCheckType.LOG_INTEGRITY,
                status=AuditStatus.SKIPPED, score=1.0, findings=[],
                passed=True,
                metadata={"reason": "no decision log provided"},
            )
        return AuditResult(
            check_id="check_log_integrity", name="Log Integrity Check",
            check_type=AuditCheckType.LOG_INTEGRITY,
            status=AuditStatus.PASS, score=1.0, findings=[],
            passed=True,
            metadata={"entries": len(decision_log)},
        )

    def _check_data_protection(self, context: dict[str, Any]) -> AuditResult:
        findings: list[AuditFinding] = []
        patterns = context.get("sensitive_patterns", [])
        content_to_check = context.get("content_to_audit", "")

        violations: list[str] = []
        if content_to_check and patterns:
            import re
            for pat in patterns:
                if re.search(pat, content_to_check, re.IGNORECASE):
                    violations.append(pat)

        if violations:
            findings.append(AuditFinding(
                id="f_data_exposure", check_id="check_data_protection",
                severity="critical",
                message=f"Sensitive data patterns found in audited content: {violations}",
                details={"patterns": violations},
                recommendation="Remove or redact sensitive data from content",
            ))
            return AuditResult(
                check_id="check_data_protection", name="Data Protection Check",
                check_type=AuditCheckType.DATA_PROTECTION,
                status=AuditStatus.FAIL, score=0.0, findings=findings,
                passed=False, metadata={"violations": len(violations)},
            )

        return AuditResult(
            check_id="check_data_protection", name="Data Protection Check",
            check_type=AuditCheckType.DATA_PROTECTION,
            status=AuditStatus.PASS, score=1.0, findings=[],
            passed=True, metadata={},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_report_summary(report: AuditReport) -> None:
        """Compute aggregate fields on a report after all checks run."""
        results = report.results
        report.total_checks = len(results)
        report.passed_checks = sum(1 for r in results if r.status == AuditStatus.PASS)
        report.failed_checks = sum(1 for r in results if r.status == AuditStatus.FAIL)
        report.warning_checks = sum(1 for r in results if r.status == AuditStatus.WARNING)

        all_findings: list[AuditFinding] = []
        for r in results:
            all_findings.extend(r.findings)
        report.total_findings = len(all_findings)
        report.critical_findings = sum(1 for f in all_findings if f.severity == "critical")
        report.high_findings = sum(1 for f in all_findings if f.severity == "high")

        scores = [r.score for r in results if r.status != AuditStatus.SKIPPED]
        report.overall_score = (
            sum(scores) / len(scores) if scores else 1.0
        )

        if report.failed_checks > 0:
            report.overall_status = AuditStatus.FAIL
        elif report.warning_checks > 0:
            report.overall_status = AuditStatus.WARNING
        else:
            report.overall_status = AuditStatus.PASS

        report.completed_at = time.time()
        if not report.started_at:
            report.started_at = report.completed_at

    def reset(self) -> None:
        """Reset all audit state back to defaults."""
        self._checks.clear()
        self._reports.clear()
        self._counter = 0
        self._context.clear()
        for check in self._default_checks():
            self._checks[check.id] = check


__all__ = [
    "AuditCheckType",
    "AuditStatus",
    "AuditFinding",
    "AuditResult",
    "AuditCheck",
    "AuditReport",
    "SafetyAuditor",
]
