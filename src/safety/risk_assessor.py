"""Risk Assessor — Evaluate and score risks with full Risk/RiskProfile support."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from safety.threat_modeler import ThreatSeverity


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Risk:
    """A single risk item."""
    risk_id: str
    title: str
    category: str
    description: str
    score: float
    level: RiskLevel
    likelihood: float
    impact: str
    mitigations: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "score": self.score,
            "level": self.level.value,
            "likelihood": self.likelihood,
            "impact": self.impact,
            "mitigations": self.mitigations,
            "timestamp": self.timestamp,
        }


@dataclass
class RiskProfile:
    """A risk assessment profile for a target system."""
    profile_id: str
    target_system: str
    risks: list[Risk] = field(default_factory=list)
    overall_score: float = 0.0
    overall_level: RiskLevel = RiskLevel.NONE
    timestamp: float = field(default_factory=time.time)

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "target_system": self.target_system,
            "total_risks": self.total_risks,
            "overall_score": self.overall_score,
            "overall_level": self.overall_level.value,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "risks": [r.to_dict() for r in self.risks],
            "timestamp": self.timestamp,
        }


def score_to_level(score: float) -> RiskLevel:
    """Convert a numeric score to a RiskLevel."""
    if score >= 0.8:
        return RiskLevel.CRITICAL
    elif score >= 0.6:
        return RiskLevel.HIGH
    elif score >= 0.3:
        return RiskLevel.MEDIUM
    elif score > 0.0:
        return RiskLevel.LOW
    return RiskLevel.NONE


class RiskAssessor:
    """Assess and score risks for agent systems."""

    # Weight mapping for risk assessment (used in profile computation)
    _RISK_WEIGHT = {
        ThreatSeverity.CRITICAL: 1.0,
        ThreatSeverity.HIGH: 0.75,
        ThreatSeverity.MEDIUM: 0.5,
        ThreatSeverity.LOW: 0.2,
        ThreatSeverity.INFO: 0.05,
    }

    def __init__(self):
        self._profiles: dict[str, RiskProfile] = {}

    def assess(self, title: str, likelihood: float, impact: float, mitigations: list[str] | None = None) -> RiskAssessment:
        """Assess a single risk (backward compat)."""
        score = likelihood * impact
        level = score_to_level(score) if score > 0.0 else RiskLevel.LOW
        return RiskAssessment(
            risk_id=f"risk-{int(time.time() * 1000)}",
            title=title,
            level=level,
            score=score,
            likelihood=likelihood,
            impact=impact,
            mitigations=mitigations or [],
        )

    def assess_model(self, model: Any) -> RiskProfile:
        """Assess all threats in a ThreatModel."""
        risks = []
        for threat in model.threats:
            # Use internal weight mapping for profile score
            score = self._RISK_WEIGHT.get(threat.severity, 0.5) * threat.likelihood
            level = score_to_level(score)
            risk = Risk(
                risk_id=threat.threat_id,
                title=threat.name,
                category=threat.category.value,
                description=threat.description,
                score=score,
                level=level,
                likelihood=threat.likelihood,
                impact=threat.impact,
                mitigations=threat.mitigations,
            )
            risks.append(risk)

        overall_score = sum(r.score for r in risks) / len(risks) if risks else 0.0
        overall_level = score_to_level(overall_score) if risks else RiskLevel.NONE

        profile = RiskProfile(
            profile_id=f"profile-{uuid.uuid4().hex[:8]}",
            target_system=model.target_system,
            risks=risks,
            overall_score=overall_score,
            overall_level=overall_level,
        )
        self._profiles[profile.profile_id] = profile
        return profile

    def assess_threats(self, threats: list[Any], target_system: str = "unknown") -> RiskProfile:
        """Assess a list of threats directly."""
        risks = []
        for threat in threats:
            # Use internal weight mapping for profile score
            score = self._RISK_WEIGHT.get(threat.severity, 0.5) * threat.likelihood
            level = score_to_level(score)
            risk = Risk(
                risk_id=threat.threat_id,
                title=threat.name,
                category=threat.category.value,
                description=threat.description,
                score=score,
                level=level,
                likelihood=threat.likelihood,
                impact=threat.impact,
                mitigations=threat.mitigations,
            )
            risks.append(risk)

        overall_score = sum(r.score for r in risks) / len(risks) if risks else 0.0
        overall_level = score_to_level(overall_score) if risks else RiskLevel.NONE

        profile = RiskProfile(
            profile_id=f"profile-{uuid.uuid4().hex[:8]}",
            target_system=target_system,
            risks=risks,
            overall_score=overall_score,
            overall_level=overall_level,
        )
        self._profiles[profile.profile_id] = profile
        return profile

    def is_acceptable(self, assessment: Any, threshold: float = 0.5) -> bool:
        """Check if a risk is acceptable."""
        return assessment.score < threshold

    def get_profile(self, profile_id: str) -> Optional[RiskProfile]:
        """Get a profile by ID."""
        return self._profiles.get(profile_id)

    def list_profiles(self) -> list[RiskProfile]:
        """List all profiles."""
        return list(self._profiles.values())

    def generate_report(self, profile_id: str) -> dict[str, Any]:
        """Generate a report for a profile."""
        profile = self._profiles.get(profile_id)
        if profile is None:
            return {"error": f"Profile not found: {profile_id}"}

        top_risks = sorted(profile.risks, key=lambda r: r.score, reverse=True)[:5]
        return {
            "profile_id": profile.profile_id,
            "target_system": profile.target_system,
            "total_risks": profile.total_risks,
            "overall_score": profile.overall_score,
            "overall_level": profile.overall_level.value,
            "critical_count": profile.critical_count,
            "high_count": profile.high_count,
            "medium_count": profile.medium_count,
            "low_count": profile.low_count,
            "top_risks": [r.to_dict() for r in top_risks],
        }


# Backward compat
@dataclass
class RiskAssessment:
    """Backward compat for old tests."""
    risk_id: str
    title: str
    level: Any
    score: float
    likelihood: float
    impact: float
    mitigations: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
