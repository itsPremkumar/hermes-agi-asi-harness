"""
Belief Engine Plugin — Bayesian Belief Management

Tracks beliefs with: statement, confidence, evidence, counter_evidence, last_verified.
Supports belief updating, confidence calculation, contradiction detection, and
downstream effect triggering.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class BeliefStatus(str, Enum):
    FACT = "fact"
    BELIEF = "belief"
    ASSUMPTION = "assumption"
    HYPOTHESIS = "hypothesis"
    PREDICTION = "prediction"
    UNKNOWN = "unknown"
    CONTRADICTION = "contradiction"


@dataclass
class Belief:
    id: str
    statement: str
    status: BeliefStatus = BeliefStatus.BELIEF
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    last_verified: float | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source: str = "inferred"
    downstream_effects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "status": self.status.value,
            "confidence": self.confidence,
            "evidence_count": len(self.evidence),
            "counter_evidence_count": len(self.counter_evidence),
            "last_verified": self.last_verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "downstream_effects": self.downstream_effects,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Belief":
        d = dict(d)
        if "status" in d:
            d["status"] = BeliefStatus(d["status"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class BayesianBeliefEngine:
    """Bayesian belief engine that updates confidence based on evidence."""

    def __init__(self):
        self._beliefs: dict[str, Belief] = {}
        self._contradictions: list[tuple] = []

    def add_belief(self, statement: str, confidence: float = 0.5,
                   status: BeliefStatus = BeliefStatus.BELIEF,
                   evidence: list[str] | None = None,
                   source: str = "inferred") -> Belief:
        belief_id = str(uuid.uuid4())
        belief = Belief(
            id=belief_id,
            statement=statement,
            status=status,
            confidence=min(1.0, max(0.0, confidence)),
            evidence=evidence or [],
            source=source,
            last_verified=time.time() if status == BeliefStatus.FACT else None,
        )
        self._beliefs[belief_id] = belief
        return belief

    def get_belief(self, belief_id: str) -> Belief | None:
        return self._beliefs.get(belief_id)

    def find_belief(self, statement_or_prefix: str) -> Belief | None:
        """Find a belief by statement or prefix match."""
        for belief in self._beliefs.values():
            if statement_or_prefix in belief.statement or belief.statement.startswith(statement_or_prefix):
                return belief
        return None

    def update_confidence(self, belief_id: str, evidence: str, is_supporting: bool = True,
                          evidence_strength: float = 0.1) -> Belief:
        """Update belief confidence with new evidence using Bayesian update."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return None

        if is_supporting:
            belief.evidence.append(evidence)
        else:
            belief.counter_evidence.append(evidence)

        # Bayesian-style update: adjust confidence based on evidence ratio
        total_ev = len(belief.evidence)
        total_ce = len(belief.counter_evidence)

        if total_ev + total_ce > 0:
            belief.confidence = total_ev / (total_ev + total_ce) * 0.8 + belief.confidence * 0.2

        belief.confidence = min(1.0, max(0.0, belief.confidence))
        belief.updated_at = time.time()
        return belief

    def check_contradictions(self, new_statement: str, new_belief_id: str) -> list[str]:
        """Check if a new belief contradicts existing beliefs."""
        contradictions = []
        # Simple negation check
        negations = [
            ("is", "is not"), ("has", "has no"), ("can", "cannot"),
            ("will", "will not"), ("does", "does not"), ("should", "should not"),
        ]
        for positive, negative in negations:
            if positive in new_statement.lower() and negative.replace(" ", "_") in new_statement.lower():
                pass  # Same statement shouldn't contradict itself

        for bid, belief in self._beliefs.items():
            if bid == new_belief_id:
                continue
            # Check for direct contradiction
            if belief.confidence > 0.7:
                for pos, neg in negations:
                    if (pos in belief.statement.lower() and neg in new_statement.lower()) or (neg in belief.statement.lower() and pos in new_statement.lower()):
                        contradictions.append(bid)

        return contradictions

    def resolve_contradiction(self, belief_id_1: str, belief_id_2: str, resolve_by: str = "evidence") -> str:
        """Resolve a contradiction between two beliefs."""
        b1 = self._beliefs.get(belief_id_1)
        b2 = self._beliefs.get(belief_id_2)

        if resolve_by == "evidence":
            winner = belief_id_1 if len(b1.evidence) > len(b2.evidence) else belief_id_2
        elif resolve_by == "confidence":
            winner = belief_id_1 if b1.confidence > b2.confidence else belief_id_2
        else:
            winner = belief_id_1

        loser = belief_id_2 if winner == belief_id_1 else belief_id_1
        self._beliefs[loser].status = BeliefStatus.CONTRADICTION
        self._contradictions.append((belief_id_1, belief_id_2, time.time()))

        return winner

    def get_beliefs_by_confidence(self, threshold: float = 0.8) -> list[Belief]:
        return [b for b in self._beliefs.values() if b.confidence >= threshold]

    def get_beliefs_by_status(self, status: BeliefStatus) -> list[Belief]:
        return [b for b in self._beliefs.values() if b.status == status]

    def get_summary(self) -> dict[str, Any]:
        by_status = {}
        for s in BeliefStatus:
            by_status[s.value] = len([b for b in self._beliefs.values() if b.status == s])

        avg_conf = sum(b.confidence for b in self._beliefs.values()) / len(self._beliefs) if self._beliefs else 0
        return {
            "total_beliefs": len(self._beliefs),
            "by_status": by_status,
            "avg_confidence": round(avg_conf, 3),
            "contradictions": len(self._contradictions),
        }


class BeliefEnginePlugin:
    def __init__(self):
        self.engine = BayesianBeliefEngine()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", "beliefs": len(self.engine._beliefs)}

    @property
    def beliefs(self) -> dict[str, Belief]:
        return self.engine._beliefs


async def create(kernel=None):
    plugin = BeliefEnginePlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
