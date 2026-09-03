"""Architecture Risk Analysis."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any


class RiskCategory(str, Enum):
    FAILURE_MODE = "failure_mode"
    COUPLING = "coupling"
    SCALING = "scaling"
    SECURITY = "security"
    OPERATIONAL = "operational"
    MIGRATION = "migration"
    OBSERVABILITY = "observability"
    SINGLE_POINT = "single_point"

class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Risk:
    id: str
    category: RiskCategory
    description: str
    severity: RiskSeverity
    likelihood: float = 0.5
    impact: float = 0.5
    mitigation: str = ""
    @property
    def risk_score(self) -> float:
        return self.likelihood * self.impact

class ArchitectureRiskAnalyzer:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.risks: list[Risk] = []
    
    def add_risk(self, category: RiskCategory, description: str,
                 severity: RiskSeverity, likelihood: float = 0.5,
                 impact: float = 0.5, mitigation: str = "") -> Risk:
        risk = Risk(id=str(uuid.uuid4()), category=category,
                   description=description, severity=severity,
                   likelihood=likelihood, impact=impact, mitigation=mitigation)
        self.risks.append(risk)
        return risk
    
    def get_high_risks(self) -> list[Risk]:
        return [r for r in self.risks if r.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)]
    
    def get_overall_risk(self) -> float:
        return sum(r.risk_score for r in self.risks) / max(len(self.risks), 1)
    
    def get_state(self) -> dict[str, Any]:
        return {"total_risks": len(self.risks), "high": len(self.get_high_risks()),
                "overall_risk": self.get_overall_risk()}
