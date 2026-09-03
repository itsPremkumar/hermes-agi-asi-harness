"""
Architecture Synthesis — Generate competing architectures, tradeoff analysis, selection.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ArchitectureStyle(str, Enum):
    MONOLITH = "monolith"
    MODULAR_MONOLITH = "modular_monolith"
    MICROSERVICES = "microservices"
    EVENT_DRIVEN = "event_driven"
    QUEUE_BASED = "queue_based"
    SERVERLESS = "serverless"
    PLUGIN = "plugin"
    LAYERED = "layered"
    HEXAGONAL = "hexagonal"
    CQRS = "cqrs"
    EVENT_SOURCING = "event_sourcing"

@dataclass
class TradeoffAnalysis:
    dimensions: list[str] = field(default_factory=lambda: [
        "correctness", "speed", "cost", "maintainability", "risk", "reversibility"
    ])
    scores: dict[str, dict[str, float]] = field(default_factory=dict)
    winner: str = ""

@dataclass
class ArchitectureCandidate:
    id: str
    style: ArchitectureStyle
    description: str
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    tradeoffs: dict[str, float] = field(default_factory=dict)
    suitability_score: float = 0.0

class ArchitectureSynthesizer:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.candidates: list[ArchitectureCandidate] = []
    
    def generate_candidates(self, requirements: dict[str, Any]) -> list[ArchitectureCandidate]:
        candidates = []
        styles = self._select_styles(requirements)
        for style in styles:
            candidate = ArchitectureCandidate(
                id=str(uuid.uuid4()),
                style=style,
                description=f"{style.value} architecture",
                pros=self._get_pros(style),
                cons=self._get_cons(style),
                tradeoffs=self._get_tradeoffs(style),
            )
            candidates.append(candidate)
        self.candidates = candidates
        return candidates
    
    def _select_styles(self, requirements: dict[str, Any]) -> list[ArchitectureStyle]:
        styles = [ArchitectureStyle.MONOLITH, ArchitectureStyle.MODULAR_MONOLITH]
        if requirements.get("scale", 0) > 0.7:
            styles.append(ArchitectureStyle.MICROSERVICES)
        if requirements.get("event_driven", False):
            styles.append(ArchitectureStyle.EVENT_DRIVEN)
        if requirements.get("team_size", 1) > 5:
            styles.append(ArchitectureStyle.MICROSERVICES)
        return list(set(styles))
    
    def _get_pros(self, style: ArchitectureStyle) -> list[str]:
        pros_map = {
            ArchitectureStyle.MONOLITH: ["Simple deployment", "Easy debugging", "Low operational overhead"],
            ArchitectureStyle.MODULAR_MONOLITH: ["Clear boundaries", "Easier to split later", "Single deploy"],
            ArchitectureStyle.MICROSERVICES: ["Independent scaling", "Team autonomy", "Technology diversity"],
            ArchitectureStyle.EVENT_DRIVEN: ["Loose coupling", "Scalability", "Audit trail"],
        }
        return pros_map.get(style, ["Flexible", "Extensible"])
    
    def _get_cons(self, style: ArchitectureStyle) -> list[str]:
        cons_map = {
            ArchitectureStyle.MONOLITH: ["Scaling limits", "Technology lock-in", "Long build times"],
            ArchitectureStyle.MODULAR_MONOLITH: ["Still single deploy", "Module boundaries can blur"],
            ArchitectureStyle.MICROSERVICES: ["Operational complexity", "Network latency", "Data consistency"],
            ArchitectureStyle.EVENT_DRIVEN: ["Eventual complexity", "Debugging difficulty", "Schema evolution"],
        }
        return cons_map.get(style, ["Complexity", "Learning curve"])
    
    def _get_tradeoffs(self, style: ArchitectureStyle) -> dict[str, float]:
        tradeoffs_map = {
            ArchitectureStyle.MONOLITH: {"correctness": 0.8, "speed": 0.9, "cost": 0.9, "maintainability": 0.6, "risk": 0.7},
            ArchitectureStyle.MODULAR_MONOLITH: {"correctness": 0.8, "speed": 0.8, "cost": 0.8, "maintainability": 0.8, "risk": 0.8},
            ArchitectureStyle.MICROSERVICES: {"correctness": 0.7, "speed": 0.7, "cost": 0.5, "maintainability": 0.9, "risk": 0.6},
            ArchitectureStyle.EVENT_DRIVEN: {"correctness": 0.7, "speed": 0.7, "cost": 0.6, "maintainability": 0.8, "risk": 0.6},
        }
        return tradeoffs_map.get(style, {"correctness": 0.7, "speed": 0.7, "cost": 0.7, "maintainability": 0.7, "risk": 0.7})
    
    def select_best(self) -> ArchitectureCandidate | None:
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda c: sum(c.tradeoffs.values()))
    
    def analyze_tradeoffs(self) -> TradeoffAnalysis:
        """Analyze tradeoffs between candidates."""
        analysis = TradeoffAnalysis()
        for candidate in self.candidates:
            analysis.scores[candidate.style.value] = candidate.tradeoffs
        if analysis.scores:
            best_style = max(analysis.scores, key=lambda s: sum(analysis.scores[s].values()))
            analysis.winner = best_style
        return analysis
    
    def get_state(self) -> dict[str, Any]:
        return {"candidates": len(self.candidates)}
