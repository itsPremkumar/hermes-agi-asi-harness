"""
HERMES INTELLIGENCE OS — CALIBRATED BELIEF ENGINE
=================================================
Maintains explicit epistemological beliefs:
Distinguishes between KNOWN, LIKELY, UNCERTAIN, CONTRADICTED, and UNKNOWN.
Evaluates supporting vs contradictory evidence with Bayesian updates and temporal decay.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("hermes.world_model.beliefs")


class BeliefState(str, Enum):
    KNOWN = "known"              # High probability (>= 0.95), direct verified evidence
    LIKELY = "likely"            # Moderate-to-high probability (0.70 to 0.94)
    UNCERTAIN = "uncertain"      # Low-to-moderate probability (0.35 to 0.69)
    CONTRADICTED = "contradicted"# Active opposing evidence detected
    UNKNOWN = "unknown"          # No verified evidence, probability ~ 0.5 default


@dataclass
class Belief:
    """A proposition about reality with evidence and calibration."""
    belief_id: str
    proposition: str
    probability: float  # 0.0 to 1.0
    state: BeliefState
    supporting_evidence: list[str] = field(default_factory=list)
    contradictory_evidence: list[str] = field(default_factory=list)
    last_verified: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time or time.time()
        return self.expires_at is not None and now >= self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "belief_id": self.belief_id,
            "proposition": self.proposition,
            "probability": round(self.probability, 4),
            "state": self.state.value if isinstance(self.state, BeliefState) else str(self.state),
            "supporting_evidence": self.supporting_evidence,
            "contradictory_evidence": self.contradictory_evidence,
            "last_verified": self.last_verified,
            "expires_at": self.expires_at,
            "is_expired": self.is_expired(),
            "metadata": self.metadata,
        }


class BeliefSystem:
    """The central belief manager maintaining the system's epistemic grounding."""

    def __init__(self, default_ttl_seconds: float = 3600.0):
        self.default_ttl = default_ttl_seconds
        self._beliefs: dict[str, Belief] = {}

    def _classify_state(self, prob: float, has_contradiction: bool) -> BeliefState:
        if has_contradiction:
            return BeliefState.CONTRADICTED
        if prob >= 0.95:
            return BeliefState.KNOWN
        elif prob >= 0.70:
            return BeliefState.LIKELY
        elif prob >= 0.35:
            return BeliefState.UNCERTAIN
        else:
            return BeliefState.UNKNOWN

    def assert_belief(
        self,
        proposition: str,
        probability: float = 0.95,
        supporting_evidence: Optional[list[str]] = None,
        contradictory_evidence: Optional[list[str]] = None,
        ttl_seconds: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Belief:
        """Register or update an explicit belief proposition."""
        bid = f"blf-{uuid.uuid4().hex[:8]}"
        sup = list(supporting_evidence or [])
        contra = list(contradictory_evidence or [])
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        now = time.time()
        expires = now + ttl if ttl is not None else None

        prob = max(0.0, min(1.0, probability))
        state = self._classify_state(prob, bool(contra))

        belief = Belief(
            belief_id=bid,
            proposition=proposition,
            probability=prob,
            state=state,
            supporting_evidence=sup,
            contradictory_evidence=contra,
            last_verified=now,
            expires_at=expires,
            metadata=metadata or {},
        )
        self._beliefs[proposition] = belief
        return belief

    def add_evidence(self, proposition: str, evidence_ref: str, is_contradiction: bool = False) -> Optional[Belief]:
        """Incorporate new evidence and perform a Bayesian adjustment."""
        b = self._beliefs.get(proposition)
        if not b:
            # Create new belief on first observation
            initial_prob = 0.30 if is_contradiction else 0.85
            return self.assert_belief(
                proposition=proposition,
                probability=initial_prob,
                supporting_evidence=[] if is_contradiction else [evidence_ref],
                contradictory_evidence=[evidence_ref] if is_contradiction else [],
            )

        if is_contradiction:
            if evidence_ref not in b.contradictory_evidence:
                b.contradictory_evidence.append(evidence_ref)
            # Downgrade probability
            b.probability = max(0.05, b.probability * 0.5)
        else:
            if evidence_ref not in b.supporting_evidence:
                b.supporting_evidence.append(evidence_ref)
            # Upgrade probability towards 1.0
            b.probability = min(0.99, b.probability + (1.0 - b.probability) * 0.4)

        b.last_verified = time.time()
        b.state = self._classify_state(b.probability, bool(b.contradictory_evidence))
        return b

    def get_belief(self, proposition: str) -> Optional[Belief]:
        return self._beliefs.get(proposition)

    def detect_contradictions(self) -> list[Belief]:
        """Return all beliefs with active opposing evidence."""
        return [b for b in self._beliefs.values() if b.state == BeliefState.CONTRADICTED]

    def decay_beliefs(self, decay_rate: float = 0.05) -> None:
        """Apply temporal entropy decay to beliefs that have not been recently verified."""
        now = time.time()
        for b in self._beliefs.values():
            if b.is_expired(now):
                # Regression to uncertainty
                b.probability = b.probability + (0.5 - b.probability) * decay_rate
                b.state = self._classify_state(b.probability, bool(b.contradictory_evidence))

    def all_beliefs(self) -> list[Belief]:
        return list(self._beliefs.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_beliefs": len(self._beliefs),
            "contradictions": len(self.detect_contradictions()),
            "beliefs": [b.to_dict() for b in self._beliefs.values()],
        }
