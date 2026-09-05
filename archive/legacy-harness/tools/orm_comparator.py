"""ORM Comparison Tool — compare ORMs and recommend one."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ORMProfile:
    name: str
    language: str
    score_performance: float = 0.0
    score_features: float = 0.0
    score_ecosystem: float = 0.0
    score_learning: float = 0.0
    score_typing: float = 0.0
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    orms: list[ORMProfile]
    winner: str
    reasoning: str
    scores: dict[str, float]


class ORMComparator:
    """Compare ORMs and recommend one."""

    def __init__(self):
        self._orms: dict[str, ORMProfile] = {}
        self._criteria_weights = {
            "performance": 0.25,
            "features": 0.25,
            "ecosystem": 0.20,
            "learning": 0.15,
            "typing": 0.15,
        }

    def add_orm(self, orm: ORMProfile) -> None:
        self._orms[orm.name] = orm

    def compare(self) -> ComparisonResult:
        if not self._orms:
            return ComparisonResult([], "none", "No ORMs to compare", {})

        scores = {}
        for name, orm in self._orms.items():
            score = (
                orm.score_performance * self._criteria_weights["performance"]
                + orm.score_features * self._criteria_weights["features"]
                + orm.score_ecosystem * self._criteria_weights["ecosystem"]
                + orm.score_learning * self._criteria_weights["learning"]
                + orm.score_typing * self._criteria_weights["typing"]
            )
            scores[name] = round(score, 2)

        winner = max(scores, key=scores.get)
        reasoning = f"{winner} scored highest ({scores[winner]}) across weighted criteria"

        return ComparisonResult(
            orms=list(self._orms.values()),
            winner=winner,
            reasoning=reasoning,
            scores=scores,
        )

    def get_recommendation(self, priority: str = "balanced") -> str:
        if priority == "performance":
            self._criteria_weights = {
                "performance": 0.40,
                "features": 0.20,
                "ecosystem": 0.15,
                "learning": 0.10,
                "typing": 0.15,
            }
        elif priority == "ease":
            self._criteria_weights = {
                "performance": 0.15,
                "features": 0.20,
                "ecosystem": 0.20,
                "learning": 0.30,
                "typing": 0.15,
            }
        result = self.compare()
        return f"Recommendation: {result.winner} — {result.reasoning}"
