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
    "RiskLevel",
    "Risk",
    "RiskProfile",
    "RiskAssessor",
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
    mitigations: list[str] = field(default_factory=list)
    assessed_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

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
