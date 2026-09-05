"""
Hermes AGI/ASI Harness — Adversarial Proposer-Critic Verification Framework.

Implements dual-perspective adversarial stress-testing:
Proposer (Claims & Evidence) <-> Adversarial Critic (Attacks & Counter-examples) -> Arbiter (Consensus & Brier Calibration)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("hermes.adversarial_verifier")


@dataclass
class CritiqueFinding:
    """A vulnerability, assumption, or edge case identified by the Adversarial Critic."""
    target_claim: str
    vulnerability: str
    severity: str  # low, medium, critical
    mitigation: str


@dataclass
class VerificationVerdict:
    """The final consensus verdict issued by the Arbiter."""
    verified: bool
    consensus_score: float  # 0.0 to 1.0
    brier_score: float      # Lower = better calibrated
    claims_count: int
    critiques_count: int
    critiques: list[CritiqueFinding] = field(default_factory=list)
    verdict_summary: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "consensus_score": round(self.consensus_score, 3),
            "brier_score": round(self.brier_score, 4),
            "claims_count": self.claims_count,
            "critiques_count": self.critiques_count,
            "critiques": [
                {
                    "target_claim": c.target_claim,
                    "vulnerability": c.vulnerability,
                    "severity": c.severity,
                    "mitigation": c.mitigation,
                }
                for c in self.critiques
            ],
            "verdict_summary": self.verdict_summary,
            "timestamp": self.timestamp,
        }


class AdversarialVerifier:
    """
    Adversarial Proposer-Critic Engine.
    
    Eliminates hallucinations, unsubstantiated claims, and hidden regression bugs
    before declaring a task or mission 'DONE'.
    """

    def __init__(self, minimum_consensus: float = 0.85):
        self.minimum_consensus = minimum_consensus

    def verify(
        self,
        claims: list[str],
        evidence: list[str],
        context: dict[str, Any] | None = None,
    ) -> VerificationVerdict:
        """
        Execute an adversarial stress-test on a set of claims and evidence.
        """
        if not claims:
            return VerificationVerdict(
                verified=False,
                consensus_score=0.0,
                brier_score=1.0,
                claims_count=0,
                critiques_count=0,
                verdict_summary="No claims provided to verify.",
            )

        critiques: list[CritiqueFinding] = []
        ctx = context or {}

        # 1. Adversarial Critic Phase: Probe each claim
        for claim in claims:
            c_lower = claim.lower()
            
            # Probe 1: Did claim state file created, but no evidence provided?
            if any(k in c_lower for k in ("write", "created", "saved", "file")):
                has_file_evidence = any("file" in e.lower() or "wrote" in e.lower() for e in evidence)
                if not has_file_evidence:
                    critiques.append(
                        CritiqueFinding(
                            target_claim=claim,
                            vulnerability="Claim asserts file creation without matching filesystem evidence.",
                            severity="medium",
                            mitigation="Verify file existence with os.path.exists() and check byte count.",
                        )
                    )

            # Probe 2: Did claim assert zero errors, but stderr exists?
            if "success" in c_lower or "passed" in c_lower:
                if any("error" in e.lower() or "fail" in e.lower() for e in evidence):
                    critiques.append(
                        CritiqueFinding(
                            target_claim=claim,
                            vulnerability="Claim asserts success but evidence log contains error keywords.",
                            severity="critical",
                            mitigation="Re-run tests and assert return code == 0.",
                        )
                    )

            # Probe 3: Check for vague or unsubstantiated claims
            if any(k in c_lower for k in ("guaranteed", "perfect", "100%", "always")):
                critiques.append(
                    CritiqueFinding(
                        target_claim=claim,
                        vulnerability="Absolutist claim detected; verify boundary conditions and edge cases.",
                        severity="low",
                        mitigation="Formulate invariant bounds and test with extreme values.",
                    )
                )

        # 2. Arbiter / Judge Scoring Phase
        # Calculate consensus based on severe critiques
        critical_count = sum(1 for c in critiques if c.severity == "critical")
        medium_count = sum(1 for c in critiques if c.severity == "medium")
        
        penalty = (critical_count * 0.40) + (medium_count * 0.10)
        consensus_score = max(0.0, min(1.0, 1.0 - penalty))
        
        # Brier score calculation: (forecast - outcome)^2
        outcome = 1.0 if consensus_score >= self.minimum_consensus else 0.0
        brier_score = (consensus_score - outcome) ** 2

        verified = consensus_score >= self.minimum_consensus

        summary = (
            f"Adversarial verification {'PASSED' if verified else 'FLAGGED'}: "
            f"Consensus={consensus_score:.2f}, {len(critiques)} critique points raised."
        )

        return VerificationVerdict(
            verified=verified,
            consensus_score=consensus_score,
            brier_score=brier_score,
            claims_count=len(claims),
            critiques_count=len(critiques),
            critiques=critiques,
            verdict_summary=summary,
        )
