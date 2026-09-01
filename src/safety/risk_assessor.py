"""Risk Assessor — Evaluate and score risks."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RiskAssessment:
    risk_id: str
    title: str
    level: RiskLevel
    score: float
    likelihood: float
    impact: float
    mitigations: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class RiskAssessor:
    def assess(self, title: str, likelihood: float, impact: float, mitigations: list[str] | None = None) -> RiskAssessment:
        score = likelihood * impact
        level = RiskLevel.LOW
        if score >= 0.8:
            level = RiskLevel.CRITICAL
        elif score >= 0.6:
            level = RiskLevel.HIGH
        elif score >= 0.3:
            level = RiskLevel.MEDIUM
        return RiskAssessment(
            risk_id=f"risk-{int(time.time() * 1000)}",
            title=title,
            level=level,
            score=score,
            likelihood=likelihood,
            impact=impact,
            mitigations=mitigations or [],
        )

    def is_acceptable(self, assessment: RiskAssessment, threshold: float = 0.5) -> bool:
        return assessment.score < threshold
