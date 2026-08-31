"""Risk Assessor — assess risk levels for threats and categorize by severity."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.safety.threat_modeler import (
    Threat,
    ThreatCategory,
    ThreatSeverity,
)


class RiskLevel(Enum):
    """Overall risk levels for a system or component."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


# Maps each ThreatSeverity to a numeric weight used in aggregation.
_SEVERITY_WEIGHTS: dict[ThreatSeverity, float] = {
    ThreatSeverity.CRITICAL: 1.0,
    ThreatSeverity.HIGH: 0.8,
    ThreatSeverity.MEDIUM: 0.5,
    ThreatSeverity.LOW: 0.2,
    ThreatSeverity.INFO: 0.05,
}

# Threshold boundaries for the aggregate risk score → RiskLevel mapping.
#  high    >= 0.75
#  medium  >= 0.40
#  low     >= 0.10
#  none    <  0.10
_HIGH_THRESHOLD = 0.75
_MEDIUM_THRESHOLD = 0.40
_LOW_THRESHOLD = 0.10

# Category-level weighting — some categories are inherently more dangerous.
_CATEGORY_WEIGHTS: dict[ThreatCategory, float] = {
    ThreatCategory.PROMPT_INJECTION: 1.0,
    ThreatCategory.PRIVILEGE_ESCALATION: 1.0,
    ThreatCategory.DATA_EXFILTRATION: 0.9,
    ThreatCategory.CREDENTIAL_THEFT: 0.9,
    ThreatCategory.MODEL_MANIPULATION: 0.8,
    ThreatCategory.DENIAL_OF_SERVICE: 0.7,
    ThreatCategory.UNAUTHORIZED_ACCESS: 0.6,
    ThreatCategory.SIDE_CHANNEL: 0.5,
}


@dataclass
class RiskAssessment:
    """A complete risk assessment result."""

    threat_id: str
    category: ThreatCategory
    severity: ThreatSeverity
    likelihood: float
    raw_score: float
    adjusted_score: float
    risk_level: RiskLevel
    impact_score: float
    description: str
    mitigations: list[str] = field(default_factory=list)
    assessed_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregateRisk:
    """Aggregated risk across multiple threats or a system."""

    risk_level: RiskLevel
    aggregate_score: float
    threat_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_likelihood: float
    by_category: dict[str, float]
    assessment_ids: list[str]
    assessed_at: float = field(default_factory=time.time)


class RiskAssessor:
    """Assess risk levels for threats and categorize by severity."""

    def __init__(self):
        self._assessments: dict[str, RiskAssessment] = {}
        self._aggregates: dict[str, AggregateRisk] = {}
        self._counter = 0

    # ------------------------------------------------------------------
    # Single-threat assessment
    # ------------------------------------------------------------------

    def assess(self, threat: Threat) -> RiskAssessment:
        """Assess the risk of a single Threat object.

        Computes a raw score (severity_weight * likelihood), applies a
        category multiplier, and maps the result to a RiskLevel.
        """
        severity_weight = _SEVERITY_WEIGHTS.get(threat.severity, 0.5)
        category_multiplier = _CATEGORY_WEIGHTS.get(threat.category, 0.5)

        raw_score = severity_weight * threat.likelihood
        adjusted_score = min(1.0, raw_score * category_multiplier)

        # Impact score: based on severity alone (0–1 scale).
        impact_score = severity_weight

        risk_level = self._score_to_level(adjusted_score)

        assessment = RiskAssessment(
            threat_id=threat.threat_id,
            category=threat.category,
            severity=threat.severity,
            likelihood=threat.likelihood,
            raw_score=raw_score,
            adjusted_score=adjusted_score,
            risk_level=risk_level,
            impact_score=impact_score,
            description=threat.description,
            mitigations=list(threat.mitigations),
            metadata=dict(threat.metadata),
        )

        self._counter += 1
        if not assessment.threat_id:
            assessment.threat_id = f"risk_{self._counter}"
        self._assessments[assessment.threat_id] = assessment
        return assessment

    def assess_by_severity(
        self,
        threat_id: str,
        category: ThreatCategory,
        severity: ThreatSeverity,
        likelihood: float,
        description: str = "",
        mitigations: Optional[list[str]] = None,
    ) -> RiskAssessment:
        """Convenience method: build a Threat-like assessment from raw fields."""
        threat = Threat(
            threat_id=threat_id,
            name=f"{category.value}_threat",
            category=category,
            severity=severity,
            description=description or f"Threat in {category.value}",
            attack_vector="",
            impact="Unknown",
            likelihood=max(0.0, min(1.0, likelihood)),
            mitigations=mitigations or [],
        )
        return self.assess(threat)

    def get_assessment(self, threat_id: str) -> Optional[RiskAssessment]:
        """Retrieve a previously stored assessment."""
        return self._assessments.get(threat_id)

    def get_all_assessments(self) -> list[RiskAssessment]:
        return list(self._assessments.values())

    # ------------------------------------------------------------------
    # Aggregate risk
    # ------------------------------------------------------------------

    def aggregate(self, threat_ids: list[str], aggregate_id: str = "") -> AggregateRisk:
        """Compute aggregate risk across a set of threat IDs."""
        scores: list[float] = []
        critical = high = medium = low = 0
        by_category: dict[str, list[float]] = {}
        assessment_ids: list[str] = []

        for tid in threat_ids:
            assessment = self._assessments.get(tid)
            if assessment is None:
                continue
            scores.append(assessment.adjusted_score)
            assessment_ids.append(tid)

            if assessment.severity == ThreatSeverity.CRITICAL:
                critical += 1
            elif assessment.severity == ThreatSeverity.HIGH:
                high += 1
            elif assessment.severity == ThreatSeverity.MEDIUM:
                medium += 1
            elif assessment.severity == ThreatSeverity.LOW:
                low += 1

            cat_name = assessment.category.value
            by_category.setdefault(cat_name, []).append(assessment.adjusted_score)

        if not scores:
            aggregate = AggregateRisk(
                risk_level=RiskLevel.NONE,
                aggregate_score=0.0,
                threat_count=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                total_likelihood=0.0,
                by_category={},
                assessment_ids=[],
            )
        else:
            avg_score = sum(scores) / len(scores)
            total_likelihood = sum(a.likelihood for a in (
                self._assessments.get(tid) for tid in threat_ids
            ) if a is not None)
            category_scores = {
                cat: sum(vals) / len(vals) for cat, vals in by_category.items()
            }
            aggregate = AggregateRisk(
                risk_level=self._score_to_level(avg_score),
                aggregate_score=round(avg_score, 4),
                threat_count=len(scores),
                critical_count=critical,
                high_count=high,
                medium_count=medium,
                low_count=low,
                total_likelihood=round(total_likelihood, 4),
                by_category={k: round(v, 4) for k, v in category_scores.items()},
                assessment_ids=assessment_ids,
            )

        agg_id = aggregate_id or f"agg_{self._counter}"
        self._aggregates[agg_id] = aggregate
        return aggregate

    def get_aggregate(self, aggregate_id: str) -> Optional[AggregateRisk]:
        return self._aggregates.get(aggregate_id)

    def list_aggregates(self) -> list[str]:
        return list(self._aggregates.keys())

    # ------------------------------------------------------------------
    # Batch convenience
    # ------------------------------------------------------------------

    def assess_threats(self, threats: list[Threat]) -> list[RiskAssessment]:
        """Assess multiple threats and return the list of assessments."""
        return [self.assess(t) for t in threats]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_level(score: float) -> RiskLevel:
        if score >= _HIGH_THRESHOLD:
            return RiskLevel.CRITICAL
        if score >= _MEDIUM_THRESHOLD:
            return RiskLevel.HIGH
        if score >= _LOW_THRESHOLD:
            return RiskLevel.MEDIUM
        if score > 0:
            return RiskLevel.LOW
        return RiskLevel.NONE

    def reset(self) -> None:
        """Clear all stored assessments and aggregates."""
        self._assessments.clear()
        self._aggregates.clear()
        self._counter = 0


__all__ = [
    "RiskAssessor",
    "RiskAssessment",
    "RiskLevel",
    "AggregateRisk",
]
