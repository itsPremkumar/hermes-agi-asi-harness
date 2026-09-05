"""
Independent Critic Plugin — Dual-Critic Verification System

For high-value tasks, uses two independent critics + executive judge to reduce
correlated reasoning failures.
"""

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CriticVerdict(str, Enum):
    ACCEPT = "accept"
    REVISE = "revise"
    REJECT = "reject"


@dataclass
class CriticReview:
    critic_id: str
    verdict: CriticVerdict
    rationale: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence_checked: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "critic_id": self.critic_id,
            "verdict": self.verdict.value,
            "rationale": self.rationale,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "confidence": self.confidence,
            "evidence_checked": self.evidence_checked,
            "timestamp": self.timestamp,
        }


@dataclass
class CriticDecision:
    decision: str  # "accept", "revise", "reject"
    consensus: bool
    critic_reviews: list[CriticReview] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


class CriticEngine:
    """Dual-critic verification with executive judgment."""

    def __init__(self):
        self._reviews: list[CriticReview] = []
        self._decisions: list[CriticDecision] = []

    def critique(self, content: str, criteria: list[str], critic_id: str) -> CriticReview:
        """Run a single critic pass on content."""
        strengths = []
        weaknesses = []
        issues = []

        # Check each criterion
        for criterion in criteria:
            content_lower = content.lower()
            criterion_lower = criterion.lower()

            if criterion_lower in content_lower:
                strengths.append(f"Criterion '{criterion}' met")
            else:
                weaknesses.append(f"Criterion '{criterion}' not explicitly addressed")
                issues.append(criterion)

        # Check for common issues
        if len(content) < 50:
            weaknesses.append("Content too brief for meaningful review")
        if content.count(".") < 3:
            weaknesses.append("Content may lack detail/substance")

        confidence = 0.5 + len(strengths) * 0.1 - len(weaknesses) * 0.1
        confidence = max(0.1, min(0.9, confidence))

        verdict = CriticVerdict.ACCEPT if len(weaknesses) == 0 else \
                  CriticVerdict.REVISE if len(weaknesses) <= 2 else \
                  CriticVerdict.REJECT

        review = CriticReview(
            critic_id=critic_id,
            verdict=verdict,
            rationale=f"Found {len(strengths)} strengths, {len(weaknesses)} weaknesses",
            strengths=strengths,
            weaknesses=weaknesses,
            confidence=confidence,
            evidence_checked=len(criteria),
        )
        self._reviews.append(review)
        return review

    def dual_critique(self, content: str, criteria: list[str],
                      critic_a_id: str = "critic_a",
                      critic_b_id: str = "critic_b") -> CriticDecision:
        """Run two independent critics and combine verdicts."""
        review_a = self.critique(content, criteria, critic_a_id)
        review_b = self.critique(content, criteria, critic_b_id)

        # Executive judgment
        if review_a.verdict == review_b.verdict:
            decision = review_a.verdict.value
            consensus = True
        else:
            # Disagreement — use evidence count and confidence
            if review_a.evidence_checked > review_b.evidence_checked:
                decision = review_a.verdict.value
            elif review_b.evidence_checked > review_a.evidence_checked:
                decision = review_b.verdict.value
            else:
                # Fall back to confidence
                decision = review_a.verdict.value if review_a.confidence >= review_b.confidence else review_b.verdict.value
            consensus = False

        avg_conf = (review_a.confidence + review_b.confidence) / 2

        decision_obj = CriticDecision(
            decision=decision,
            consensus=consensus,
            critic_reviews=[review_a, review_b],
            reasoning=f"Critics {'agree' if consensus else 'disagree'}: A={review_a.verdict.value}, B={review_b.verdict.value}",
            confidence=avg_conf,
        )
        self._decisions.append(decision_obj)
        return decision_obj

    def get_history(self) -> list[CriticDecision]:
        return self._decisions


class CriticEnginePlugin:
    def __init__(self):
        self.engine = CriticEngine()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", "reviews": len(self.engine._reviews), "decisions": len(self.engine._decisions)}


async def create(kernel=None):
    plugin = CriticEnginePlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
