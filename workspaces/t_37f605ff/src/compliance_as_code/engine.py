"""Core compliance engine — orchestrates policy evaluation, evidence collection, and reporting."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    SOC2 = "SOC2"
    HIPAA = "HIPAA"
    GDPR = "GDPR"
    PCI_DSS = "PCI-DSS"


class ControlStatus(str, Enum):
    """Status of a compliance control evaluation."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"


class Severity(str, Enum):
    """Risk severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class ControlResult:
    """Result of evaluating a single compliance control."""
    control_id: str
    framework: ComplianceFramework
    status: ControlStatus
    description: str
    evidence: list[str] = field(default_factory=list)
    severity: Severity = Severity.MEDIUM
    remediation: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "framework": self.framework.value,
            "status": self.status.value,
            "description": self.description,
            "evidence": self.evidence,
            "severity": self.severity.value,
            "remediation": self.remediation,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ComplianceReport:
    """Aggregated compliance report across all evaluated controls."""
    report_id: str
    generated_at: datetime
    framework: ComplianceFramework
    results: list[ControlResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_controls(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == ControlStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == ControlStatus.FAIL)

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == ControlStatus.WARNING)

    @property
    def compliance_score(self) -> float:
        if not self.results:
            return 0.0
        applicable = [r for r in self.results if r.status != ControlStatus.NOT_APPLICABLE]
        if not applicable:
            return 100.0
        return round((self.passed / len(applicable)) * 100, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "framework": self.framework.value,
            "summary": {
                "total_controls": self.total_controls,
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "compliance_score": self.compliance_score,
            },
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


class ComplianceEngine:
    """Main engine for running compliance checks across frameworks."""

    def __init__(self, policy_dir: str | Path | None = None):
        self.policy_dir = Path(policy_dir) if policy_dir else Path("policies")
        self._controls: dict[ComplianceFramework, list["BaseControl"]] = {}
        self._evidence_collectors: list["BaseEvidenceCollector"] = []

    def register_control(self, control: "BaseControl") -> None:
        """Register a compliance control for evaluation."""
        framework = control.framework
        if framework not in self._controls:
            self._controls[framework] = []
        self._controls[framework].append(control)
        logger.info("Registered control %s for %s", control.control_id, framework.value)

    def register_evidence_collector(self, collector: "BaseEvidenceCollector") -> None:
        """Register an evidence collector."""
        self._evidence_collectors.append(collector)

    def evaluate(
        self,
        framework: ComplianceFramework,
        context: dict[str, Any] | None = None,
    ) -> ComplianceReport:
        """Evaluate all controls for a given framework."""
        ctx = context or {}
        report = ComplianceReport(
            report_id=f"{framework.value}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            generated_at=datetime.now(timezone.utc),
            framework=framework,
        )

        controls = self._controls.get(framework, [])
        if not controls:
            logger.warning("No controls registered for %s", framework.value)
            return report

        for control in controls:
            try:
                result = control.evaluate(ctx)
                report.results.append(result)
            except Exception as exc:
                logger.error("Control %s evaluation failed: %s", control.control_id, exc)
                report.results.append(ControlResult(
                    control_id=control.control_id,
                    framework=framework,
                    status=ControlStatus.ERROR,
                    description=f"Evaluation error: {exc}",
                    severity=Severity.HIGH,
                ))

        return report

    def evaluate_all(self, context: dict[str, Any] | None = None) -> dict[ComplianceFramework, ComplianceReport]:
        """Evaluate all registered controls across all frameworks."""
        return {
            fw: self.evaluate(fw, context)
            for fw in self._controls
        }


class BaseControl:
    """Base class for compliance controls."""

    def __init__(
        self,
        control_id: str,
        framework: ComplianceFramework,
        description: str,
        severity: Severity = Severity.MEDIUM,
        remediation: str | None = None,
    ):
        self.control_id = control_id
        self.framework = framework
        self.description = description
        self.severity = severity
        self.remediation = remediation

    def evaluate(self, context: dict[str, Any]) -> ControlResult:
        """Evaluate the control against the provided context."""
        raise NotImplementedError("Subclasses must implement evaluate()")


class BaseEvidenceCollector:
    """Base class for evidence collectors."""

    def __init__(self, name: str, framework: ComplianceFramework):
        self.name = name
        self.framework = framework

    def collect(self, context: dict[str, Any]) -> list[str]:
        """Collect evidence artifacts."""
        raise NotImplementedError("Subclasses must implement collect()")
