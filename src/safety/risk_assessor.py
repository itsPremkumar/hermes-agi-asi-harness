<<<<<<< HEAD
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
=======
"""Risk Assessor — assess risk levels and categorize by severity.

Part of the Advanced Safety Module. Consumes threat models (from
:class:`~safety.threat_modeler.ThreatModeler`) and produces :class:`Risk`
objects with normalized severity levels and a composite :class:`RiskProfile`
for a target system.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from safety.threat_modeler import (
    Threat,
    ThreatModel,
    ThreatSeverity,
)

logger = logging.getLogger(__name__)

__all__ = [
    "Risk",
    "RiskAssessor",
    "RiskLevel",
    "RiskProfile",
]


class RiskLevel(Enum):
    """Normalized risk levels (ascending severity)."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Map threat severity into a numeric weight used by the risk scorer.
_THREAT_WEIGHT: dict[ThreatSeverity, float] = {
    ThreatSeverity.CRITICAL: 1.0,
    ThreatSeverity.HIGH: 0.75,
    ThreatSeverity.MEDIUM: 0.5,
    ThreatSeverity.LOW: 0.25,
    ThreatSeverity.INFO: 0.1,
}


def _threat_score(threat: Threat) -> float:
    """Composite score for a single threat in [0, 1]."""
    weight = _THREAT_WEIGHT.get(threat.severity, 0.5)
    return max(0.0, min(1.0, weight * threat.likelihood))


def score_to_level(score: float) -> RiskLevel:
    """Map a normalized [0, 1] risk *score* to a :class:`RiskLevel`."""
    if score <= 0.0:
        return RiskLevel.NONE
    if score < 0.3:
        return RiskLevel.LOW
    if score < 0.6:
        return RiskLevel.MEDIUM
    if score < 0.85:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


@dataclass
class Risk:
    """A quantified risk derived from one or more threats."""

    risk_id: str
    threat_id: str
    category: str
    description: str
    score: float
    level: RiskLevel
    likelihood: float
    impact: str
>>>>>>> 7bed5b11ca2c5b86bd3e0d48bfc3c28933c70109
    mitigations: list[str] = field(default_factory=list)
    assessed_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

<<<<<<< HEAD

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
=======
    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "threat_id": self.threat_id,
            "category": self.category,
            "description": self.description,
            "score": round(self.score, 4),
            "level": self.level.value,
            "likelihood": self.likelihood,
            "impact": self.impact,
            "mitigations": list(self.mitigations),
            "assessed_at": self.assessed_at,
        }


@dataclass
class RiskProfile:
    """Aggregated risk profile for a target system."""

    profile_id: str
    target_system: str
    risks: list[Risk] = field(default_factory=list)
    overall_score: float = 0.0
    overall_level: RiskLevel = RiskLevel.NONE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def total_risks(self) -> int:
        return len(self.risks)

    @property
    def critical_count(self) -> int:
        return sum(1 for r in self.risks if r.level == RiskLevel.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for r in self.risks if r.level == RiskLevel.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for r in self.risks if r.level == RiskLevel.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for r in self.risks if r.level == RiskLevel.LOW)

    def by_level(self, level: RiskLevel) -> list[Risk]:
        return [r for r in self.risks if r.level == level]

    def top_risks(self, n: int = 5) -> list[Risk]:
        return sorted(self.risks, key=lambda r: r.score, reverse=True)[:n]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "target_system": self.target_system,
            "total_risks": self.total_risks,
            "overall_score": round(self.overall_score, 4),
            "overall_level": self.overall_level.value,
            "critical_count": self.critical_count,
            "risks": [r.to_dict() for r in self.risks],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class RiskAssessor:
    """Assess risk from threat models and categorize by severity."""

    def __init__(self) -> None:
        self._profiles: dict[str, RiskProfile] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"risk-{self._counter:06d}"

    def _next_profile_id(self) -> str:
        self._counter += 1
        return f"rp-{self._counter:06d}"

    def assess_model(self, model: ThreatModel) -> RiskProfile:
        """Turn a :class:`ThreatModel` into a :class:`RiskProfile`.

        Each threat becomes one :class:`Risk`; the overall profile score is the
        mean of the per-risk scores (0 when there are no risks).
        """
        profile_id = self._next_profile_id()
        profile = RiskProfile(
            profile_id=profile_id,
            target_system=model.target_system,
        )

        for threat in model.threats:
            score = _threat_score(threat)
            level = score_to_level(score)
            risk = Risk(
                risk_id=self._next_id(),
                threat_id=threat.threat_id,
                category=threat.category.value,
                description=threat.description,
                score=score,
                level=level,
                likelihood=threat.likelihood,
                impact=threat.impact,
                mitigations=list(threat.mitigations),
            )
            profile.risks.append(risk)

        if profile.risks:
            profile.overall_score = sum(r.score for r in profile.risks) / len(profile.risks)
        else:
            profile.overall_score = 0.0
        profile.overall_level = score_to_level(profile.overall_score)
        profile.updated_at = time.time()

        self._profiles[profile_id] = profile
        logger.info(
            "Assessed %d threats for %s -> %s (score=%.3f)",
            profile.total_risks,
            model.target_system,
            profile.overall_level.value,
            profile.overall_score,
        )
        return profile

    def assess_threats(self, threats: list[Threat], target_system: str = "unknown") -> RiskProfile:
        """Convenience: assess a bare list of threats without a full ThreatModel."""
        model = ThreatModel(
            model_id="ad-hoc",
            target_system=target_system,
            threats=list(threats),
        )
        return self.assess_model(model)

    def get_profile(self, profile_id: str) -> RiskProfile | None:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> list[str]:
        return list(self._profiles.keys())

    def generate_report(self, profile_id: str) -> dict[str, Any]:
        profile = self._profiles.get(profile_id)
        if not profile:
            return {"error": "profile not found", "profile_id": profile_id}

        by_level = {lv.value: len(profile.by_level(lv)) for lv in RiskLevel}
        return {
            "profile_id": profile.profile_id,
            "target_system": profile.target_system,
            "total_risks": profile.total_risks,
            "overall_score": round(profile.overall_score, 4),
            "overall_level": profile.overall_level.value,
            "by_level": by_level,
            "critical_count": profile.critical_count,
            "top_risks": [r.to_dict() for r in profile.top_risks(5)],
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
>>>>>>> 7bed5b11ca2c5b86bd3e0d48bfc3c28933c70109
