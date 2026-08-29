"""Risk scoring engine — quantifies compliance risk across frameworks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from compliance_as_code.engine import (
    ComplianceFramework,
    ComplianceReport,
    ControlStatus,
    Severity,
)

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Overall risk classification."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    MINIMAL = "MINIMAL"


# Weight factors for risk calculation
SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 10,
    Severity.HIGH: 7,
    Severity.MEDIUM: 4,
    Severity.LOW: 2,
    Severity.INFO: 1,
}

STATUS_MULTIPLIERS = {
    ControlStatus.FAIL: 1.0,
    ControlStatus.WARNING: 0.5,
    ControlStatus.ERROR: 0.8,
    ControlStatus.PASS: 0.0,
    ControlStatus.NOT_APPLICABLE: 0.0,
}


@dataclass
class ControlRisk:
    """Risk score for a single control."""
    control_id: str
    framework: ComplianceFramework
    severity: Severity
    status: ControlStatus
    risk_score: float
    weighted_impact: float
    likelihood: float = 0.5
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "framework": self.framework.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "risk_score": round(self.risk_score, 2),
            "weighted_impact": round(self.weighted_impact, 2),
            "likelihood": round(self.likelihood, 2),
            "notes": self.notes,
        }


@dataclass
class RiskScore:
    """Aggregated risk score for a framework."""
    framework: ComplianceFramework
    overall_score: float  # 0-100, higher = more risk
    risk_level: RiskLevel
    control_risks: list[ControlRisk] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework": self.framework.value,
            "overall_score": round(self.overall_score, 2),
            "risk_level": self.risk_level.value,
            "generated_at": self.generated_at.isoformat(),
            "control_risks": [cr.to_dict() for cr in self.control_risks],
            "recommendations": self.recommendations,
        }


class RiskScoringEngine:
    """Calculates compliance risk scores from control evaluation results."""

    def __init__(self, custom_weights: dict[Severity, int] | None = None):
        self.weights = custom_weights or SEVERITY_WEIGHTS

    def calculate_risk(self, report: ComplianceReport) -> RiskScore:
        """Calculate risk score from a compliance report."""
        control_risks: list[ControlRisk] = []
        total_weighted_risk = 0.0
        max_possible_risk = 0.0

        for result in report.results:
            if result.status == ControlStatus.NOT_APPLICABLE:
                continue

            severity_weight = self.weights.get(result.severity, 4)
            status_mult = STATUS_MULTIPLIERS.get(result.status, 0.5)

            # Risk = severity_weight * status_multiplier * likelihood
            likelihood = self._estimate_likelihood(result)
            risk_score = severity_weight * status_mult * likelihood
            weighted_impact = severity_weight * status_mult

            control_risk = ControlRisk(
                control_id=result.control_id,
                framework=report.framework,
                severity=result.severity,
                status=result.status,
                risk_score=risk_score,
                weighted_impact=weighted_impact,
                likelihood=likelihood,
                notes=self._generate_note(result),
            )
            control_risks.append(control_risk)
            total_weighted_risk += risk_score
            max_possible_risk += severity_weight * 1.0  # max multiplier

        # Normalize to 0-100 scale
        overall_score = (
            (total_weighted_risk / max_possible_risk * 100)
            if max_possible_risk > 0
            else 0.0
        )

        risk_level = self._classify_risk(overall_score)
        recommendations = self._generate_recommendations(control_risks, overall_score)

        return RiskScore(
            framework=report.framework,
            overall_score=overall_score,
            risk_level=risk_level,
            control_risks=control_risks,
            recommendations=recommendations,
        )

    def _estimate_likelihood(self, result: Any) -> float:
        """Estimate likelihood of exploitation/occurrence (0-1)."""
        if result.status == ControlStatus.FAIL:
            return 0.8
        elif result.status == ControlStatus.WARNING:
            return 0.4
        elif result.status == ControlStatus.ERROR:
            return 0.6
        return 0.1

    def _classify_risk(self, score: float) -> RiskLevel:
        """Classify overall risk level from score."""
        if score >= 75:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 25:
            return RiskLevel.MEDIUM
        elif score >= 10:
            return RiskLevel.LOW
        return RiskLevel.MINIMAL

    def _generate_note(self, result: Any) -> str:
        """Generate a human-readable note for a control risk."""
        if result.status == ControlStatus.FAIL:
            return f"{result.control_id}: FAILED — immediate remediation required"
        elif result.status == ControlStatus.WARNING:
            return f"{result.control_id}: WARNING — partial compliance, review needed"
        elif result.status == ControlStatus.ERROR:
            return f"{result.control_id}: ERROR — evaluation could not complete"
        return f"{result.control_id}: PASS"

    def _generate_recommendations(
        self, control_risks: list[ControlRisk], overall_score: float
    ) -> list[str]:
        """Generate prioritized remediation recommendations."""
        recommendations: list[str] = []

        # Sort by risk score descending
        sorted_risks = sorted(control_risks, key=lambda r: r.risk_score, reverse=True)

        for cr in sorted_risks:
            if cr.risk_score >= 5.0:
                recommendations.append(
                    f"[CRITICAL] {cr.control_id}: {cr.notes}"
                )
            elif cr.risk_score >= 2.0:
                recommendations.append(
                    f"[HIGH] {cr.control_id}: {cr.notes}"
                )

        if overall_score >= 50:
            recommendations.insert(0, "OVERALL: Critical risk level — executive escalation recommended")
        elif overall_score >= 25:
            recommendations.insert(0, "OVERALL: Elevated risk — prioritize remediation within 30 days")

        return recommendations
