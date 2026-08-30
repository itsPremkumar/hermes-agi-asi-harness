"""
Completion Proof Plugin — Evidence-Backed Goal Completion

"Done" becomes an evidence-backed state, not just a model-generated message.
Every completed goal has: expected outcome, actual result, evidence, confidence.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CompletionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class CompletionProof:
    goal_id: str
    status: CompletionStatus = CompletionStatus.NOT_STARTED
    expected: list[str] = field(default_factory=list)
    observed: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    verification_results: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "status": self.status.value,
            "expected": self.expected,
            "observed": self.observed,
            "evidence": self.evidence,
            "verification_results": self.verification_results,
            "confidence": self.confidence,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }

    @property
    def is_proven(self) -> bool:
        return self.status == CompletionStatus.VERIFIED and self.confidence > 0.8

    @property
    def is_incomplete(self) -> bool:
        return self.status in [CompletionStatus.NOT_STARTED, CompletionStatus.IN_PROGRESS]


class CompletionProofPlugin:
    def __init__(self):
        self._proofs: dict[str, CompletionProof] = {}
        self._start_times: dict[str, float] = {}

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", "proofs_generated": len(self._proofs)}

    def start_goal(self, goal_id: str, expected: list[str] | None = None) -> CompletionProof:
        proof = CompletionProof(
            goal_id=goal_id,
            status=CompletionStatus.IN_PROGRESS,
            expected=expected or [],
        )
        self._proofs[goal_id] = proof
        self._start_times[goal_id] = time.time()
        return proof

    def add_evidence(self, goal_id: str, evidence_item: str):
        if goal_id in self._proofs:
            self._proofs[goal_id].evidence.append(evidence_item)

    def add_observed(self, goal_id: str, observation: str):
        if goal_id in self._proofs:
            self._proofs[goal_id].observed.append(observation)

    def verify(self, goal_id: str, results: dict[str, Any]) -> CompletionProof:
        if goal_id not in self._proofs:
            return None
        proof = self._proofs[goal_id]
        proof.verification_results = results
        proof.status = CompletionStatus.VERIFYING

        # Calculate confidence from evidence
        confidence = self._calculate_confidence(proof, results)
        proof.confidence = confidence

        if results.get("passed", False) and confidence > 0.7:
            proof.status = CompletionStatus.VERIFIED
        else:
            proof.status = CompletionStatus.FAILED

        if goal_id in self._start_times:
            proof.duration_seconds = time.time() - self._start_times[goal_id]

        return proof

    def _calculate_confidence(self, proof: CompletionProof, results: dict[str, Any]) -> float:
        """Calculate confidence from evidence quality."""
        score = 0.0

        # Verification result quality
        if results.get("passed"):
            score += 0.4

        # Evidence count (more evidence = higher confidence, capped)
        evidence_count = len(proof.evidence)
        score += min(0.3, evidence_count * 0.1)

        # Expected outcomes matched
        if proof.expected:
            matched = len([e for e in proof.expected if any(
                e.lower() in obs.lower() for obs in proof.observed
            )])
            score += (matched / len(proof.expected)) * 0.2

        # Source quality
        if results.get("source_quality"):
            score += min(0.1, results["source_quality"] * 0.1)

        return min(1.0, score)

    def get_proof(self, goal_id: str) -> CompletionProof | None:
        return self._proofs.get(goal_id)

    def get_all_proofs(self) -> list[CompletionProof]:
        return list(self._proofs.values())

    def get_completion_rate(self) -> float:
        if not self._proofs:
            return 0.0
        verified = sum(1 for p in self._proofs.values() if p.status == CompletionStatus.VERIFIED)
        return verified / len(self._proofs)

    def generate_proof_report(self, goal_id: str) -> dict[str, Any]:
        proof = self._proofs.get(goal_id)
        if not proof:
            return {"error": "Goal not found"}
        return {
            "proof": proof.to_dict(),
            "is_proven": proof.is_proven,
            "evidence_count": len(proof.evidence),
            "observed_count": len(proof.observed),
            "expected_count": len(proof.expected),
        }


async def create(kernel=None):
    return CompletionProofPlugin()
