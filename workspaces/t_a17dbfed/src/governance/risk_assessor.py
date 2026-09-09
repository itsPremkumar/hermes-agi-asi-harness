"""Risk assessor module — Risk scoring and assessment for AI systems."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskAssessment:
    """A risk assessment."""
    id: str
    title: str
    likelihood: str
    impact: str
    risk_level: str
    mitigations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class RiskAssessor:
    """Manage risk assessments and scoring."""

    def __init__(self) -> None:
        self._risks: dict[str, RiskAssessment] = {}

    def add(self, risk: RiskAssessment) -> None:
        self._risks[risk.id] = risk

    def get(self, id: str) -> RiskAssessment | None:
        return self._risks.get(id)

    def get_all(self) -> list[RiskAssessment]:
        return list(self._risks.values())

    def get_by_level(self, level: str) -> list[RiskAssessment]:
        return [r for r in self._risks.values() if r.risk_level == level]

    def get_high_risks(self) -> list[RiskAssessment]:
        return [r for r in self._risks.values() if r.risk_level in ["high", "critical"]]

    def calculate_risk_level(self, likelihood: str, impact: str) -> str:
        """Calculate risk level from likelihood and impact."""
        levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        score = levels.get(likelihood, 1) * levels.get(impact, 1)
        if score >= 12:
            return "critical"
        if score >= 6:
            return "high"
        if score >= 3:
            return "medium"
        return "low"

    def add_mitigation(self, id: str, mitigation: str) -> None:
        risk = self._risks.get(id)
        if risk:
            risk.mitigations.append(mitigation)
