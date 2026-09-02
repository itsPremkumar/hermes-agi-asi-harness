"""Audit report generation — formatted compliance reports in multiple output formats."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from compliance_as_code.engine import (
    ComplianceFramework,
    ComplianceReport,
    ControlStatus,
)
from compliance_as_code.risk import RiskScore, RiskScoringEngine

logger = logging.getLogger(__name__)


@dataclass
class AuditReport:
    """Comprehensive audit report combining compliance, risk, and drift data."""
    report_id: str
    generated_at: datetime
    frameworks: list[ComplianceFramework]
    compliance_reports: dict[str, ComplianceReport] = field(default_factory=dict)
    risk_scores: dict[str, RiskScore] = field(default_factory=dict)
    drift_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def overall_compliance_score(self) -> float:
        """Calculate average compliance score across all frameworks."""
        if not self.compliance_reports:
            return 0.0
        scores = [r.compliance_score for r in self.compliance_reports.values()]
        return round(sum(scores) / len(scores), 2)

    @property
    def overall_risk_score(self) -> float:
        """Calculate average risk score across all frameworks."""
        if not self.risk_scores:
            return 0.0
        scores = [r.overall_score for r in self.risk_scores.values()]
        return round(sum(scores) / len(scores), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "frameworks": [f.value for f in self.frameworks],
            "overall_compliance_score": self.overall_compliance_score,
            "overall_risk_score": self.overall_risk_score,
            "compliance_reports": {
                k: v.to_dict() for k, v in self.compliance_reports.items()
            },
            "risk_scores": {k: v.to_dict() for k, v in self.risk_scores.items()},
            "drift_data": self.drift_data,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_markdown(self) -> str:
        """Generate a markdown audit report."""
        lines: list[str] = []
        lines.append(f"# Compliance Audit Report")
        lines.append(f"")
        lines.append(f"**Report ID:** {self.report_id}")
        lines.append(f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"**Frameworks:** {', '.join(f.value for f in self.frameworks)}")
        lines.append(f"")
        lines.append(f"## Executive Summary")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Overall Compliance Score | {self.overall_compliance_score}% |")
        lines.append(f"| Overall Risk Score | {self.overall_risk_score}/100 |")
        lines.append(f"")

        for fw_name, report in self.compliance_reports.items():
            lines.append(f"## {fw_name} Compliance")
            lines.append(f"")
            lines.append(f"| Control | Status | Severity | Description |")
            lines.append(f"|---------|--------|----------|-------------|")
            for result in report.results:
                status_icon = {
                    ControlStatus.PASS: "PASS",
                    ControlStatus.FAIL: "FAIL",
                    ControlStatus.WARNING: "WARN",
                    ControlStatus.ERROR: "ERR",
                    ControlStatus.NOT_APPLICABLE: "N/A",
                }.get(result.status, "?")
                lines.append(
                    f"| {result.control_id} | {status_icon} | {result.severity.value} | {result.description[:60]}... |"
                )
            lines.append(f"")

        if self.risk_scores:
            lines.append(f"## Risk Assessment")
            lines.append(f"")
            for fw_name, risk in self.risk_scores.items():
                lines.append(f"### {fw_name}")
                lines.append(f"- **Risk Level:** {risk.risk_level.value}")
                lines.append(f"- **Score:** {risk.overall_score}/100")
                if risk.recommendations:
                    lines.append(f"- **Recommendations:**")
                    for rec in risk.recommendations[:5]:
                        lines.append(f"  - {rec}")
                lines.append(f"")

        return "\n".join(lines)


class ReportGenerator:
    """Generates formatted compliance reports."""

    def __init__(self):
        self.risk_engine = RiskScoringEngine()

    def generate_audit_report(
        self,
        compliance_reports: dict[ComplianceFramework, ComplianceReport],
        include_risk: bool = True,
        drift_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditReport:
        """Generate a comprehensive audit report."""
        risk_scores: dict[str, RiskScore] = {}
        if include_risk:
            for fw, report in compliance_reports.items():
                risk_scores[fw.value] = self.risk_engine.calculate_risk(report)

        return AuditReport(
            report_id=f"audit-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            generated_at=datetime.now(timezone.utc),
            frameworks=list(compliance_reports.keys()),
            compliance_reports={fw.value: r for fw, r in compliance_reports.items()},
            risk_scores=risk_scores,
            drift_data=drift_data or {},
            metadata=metadata or {},
        )

    def save_report(
        self,
        report: AuditReport,
        output_dir: str | Path,
        formats: list[str] | None = None,
    ) -> dict[str, Path]:
        """Save report in multiple formats. Returns mapping of format to file path."""
        formats = formats or ["json", "markdown"]
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        saved: dict[str, Path] = {}

        if "json" in formats:
            json_path = output_dir / f"{report.report_id}.json"
            json_path.write_text(report.to_json(), encoding="utf-8")
            saved["json"] = json_path

        if "markdown" in formats:
            md_path = output_dir / f"{report.report_id}.md"
            md_path.write_text(report.to_markdown(), encoding="utf-8")
            saved["markdown"] = md_path

        logger.info("Saved audit report to %s", saved)
        return saved
