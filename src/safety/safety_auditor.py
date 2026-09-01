"""Safety Auditor — Audit safety compliance and generate reports."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class AuditStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class AuditFinding:
    finding_id: str
    title: str
    status: AuditStatus
    description: str
    recommendation: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class AuditReport:
    report_id: str
    title: str
    findings: list[AuditFinding] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.findings if f.status == AuditStatus.PASS)

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.findings if f.status == AuditStatus.FAIL)

    @property
    def overall_pass(self) -> bool:
        return self.fail_count == 0


class SafetyAuditor:
    def __init__(self):
        self._reports: list[AuditReport] = []

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
        report = next((r for r in self._reports if r.report_id == report_id), None)
        if report:
            report.findings.append(AuditFinding(
                finding_id=f"f-{len(report.findings)}",
                title=title,
                status=status,
                description=description,
                recommendation=recommendation,
            ))

    def get_report(self, report_id: str) -> AuditReport | None:
        return next((r for r in self._reports if r.report_id == report_id), None)

    def list_reports(self) -> list[AuditReport]:
        return list(self._reports)

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
