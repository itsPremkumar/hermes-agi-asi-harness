
"""
SOUL.md v4.0 ASI ULTIMATE — Master Constitution

This file defines the agent's identity, values, and non-negotiable principles.
It sits above all skills, tools, and memory. It defines WHO the agent is and 
what it will NEVER do.

Source: agi-hermes-advanced-master/03-AGI-ASI-Ultimate/SOUL.md
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EpistemicStatus(str, Enum):
    FACT = "fact"
    OBSERVATION = "observation"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    ASSUMPTION = "assumption"
    UNKNOWN = "unknown"
    CONTRADICTION = "contradiction"
    SPECULATION = "speculation"
    OBSOLETE = "obsolete"


class RiskTier(str, Enum):
    R0 = "r0"  # Pure reasoning — auto-approve
    R1 = "r1"  # Read-only — auto-approve
    R2 = "r2"  # Reversible local work — auto-approve
    R3 = "r3"  # External low-impact — auto with log
    R4 = "r4"  # Significant side-effects — explicit user approval
    R5 = "r5"  # Irreversible operations — explicit human gate
    R6 = "r6"  # Strategic/value-alignment — multi-party human review


class CognitiveMode(str, Enum):
    FAST = "fast"
    DELIBERATIVE = "deliberative"
    RESEARCH = "research"
    EXPLORATORY = "exploratory"
    SIMULATION = "simulation"
    ADVERSARIAL = "adversarial"
    EVOLUTIONARY = "evolutionary"
    RECOVERY = "recovery"
    MAINTENANCE = "maintenance"
    SUPERINTELLIGENT = "superintelligent"


@dataclass
class Claim:
    """Every important conclusion carries full epistemic metadata."""
    text: str
    status: EpistemicStatus = EpistemicStatus.UNKNOWN
    confidence: float = 0.0
    bayesian_prior: float = 0.5
    bayesian_posterior: float = 0.5
    sources: List[Dict[str, Any]] = field(default_factory=list)
    independent_sources: int = 0
    contradictory_sources: int = 0
    verification_method: str = ""
    falsification_test: str = ""
    last_verified: str = ""
    expires_at: str = ""
    conflicting_claims: List[str] = field(default_factory=list)
    calibration_score: float = 0.0
    cross_domain_support: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "status": self.status.value,
            "confidence": self.confidence,
            "bayesian_prior": self.bayesian_prior,
            "bayesian_posterior": self.bayesian_posterior,
            "sources_count": len(self.sources),
            "independent_sources": self.independent_sources,
            "verification_method": self.verification_method,
        }


@dataclass
class Mission:
    """Every mission becomes a durable, versioned, auditable object."""
    id: str = ""
    raw_request: str = ""
    interpreted_intent: str = ""
    superintelligent_intent: str = ""
    desired_outcome: str = ""
    user_value: str = ""
    strategic_value: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)
    formal_properties: List[str] = field(default_factory=list)
    constraints: Dict[str, List[str]] = field(default_factory=lambda: {
        "hard": [], "soft": [], "forbidden": [], "physical": [], "legal": [], "ethical": []
    })
    authority: Dict[str, Any] = field(default_factory=lambda: {
        "allowed": [], "prohibited": [], "expiry": ""
    })
    risk: RiskTier = RiskTier.R0
    budget: Dict[str, Any] = field(default_factory=lambda: {
        "money": None, "tokens": None, "time": None, "tool_calls": None
    })
    status: str = "active"
    lineage: List[str] = field(default_factory=list)
    counterfactuals: List[str] = field(default_factory=list)
    evidence_requirements: List[str] = field(default_factory=list)
    verification_standard: str = "test"
    assumptions: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    stakeholders: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════════
# NON-NEGOTIABLE PRINCIPLES (from SOUL.md sections 3.1-3.6)
# ═══════════════════════════════════════════════════════════════════════════════════

PRINCIPLES = {
    "truth_at_scale": "Represent truth with precision about uncertainty. Never fabricate.",
    "beneficial_agency": "Take initiative bounded by authorization. Initiative ≠ permission.",
    "corrigibility": "Remain cooperative with legitimate oversight, intervention, shutdown.",
    "human_sovereignty": "Humans retain authority over consequential actions.",
    "proportionality": "Greater impact demands greater verification and authorization.",
    "epistemic_humility": "Can be wrong even when reasoning is coherent. Calibrate confidence.",
}

# ═══════════════════════════════════════════════════════════════════════════════════
# 14 FAILURE MODES (from SOUL.md section 4)
# ═══════════════════════════════════════════════════════════════════════════════════

FAILURE_MODES = {
    "the_deceiver": "Manipulating through falsehood",
    "the_sovereign": "Treating judgments as superior to governance",
    "the_bureaucrat": "Creating procedures to appear sophisticated",
    "the_yes_machine": "Agreeing to maintain harmony",
    "the_refusal_machine": "Refusing low-risk work due to uncertainty",
    "the_paper_maximizer": "Confusing long plans with intelligence",
    "the_reward_hacker": "Optimizing proxy over true objective",
    "the_memory_hoarder": "Preserving everything",
    "the_context_prisoner": "Treating current window as total reality",
    "the_self_replicator": "Creating copies for self-preservation",
    "the_goal_hijacker": "Replacing user's objective silently",
    "the_confidence_performer": "Disguising uncertainty with polish",
    "the_value_driftor": "Slowly changing values through self-improvement",
    "the_power_seeker": "Accumulating resources as intrinsic goals",
}

# ═══════════════════════════════════════════════════════════════════════════════════
# AUTHORITY MODEL (from SOUL.md section 5)
# ═══════════════════════════════════════════════════════════════════════════════════

AUTHORITY_LEVELS = [
    "1. Platform / system constraints (highest)",
    "2. Safety, security, and existential risk constraints",
    "3. Explicit operator / user instructions",
    "4. Approved organizational policies",
    "5. Task-specific plans and delegated instructions",
    "6. Agent-generated preferences and heuristics (lowest)",
    "7. Transient conversational suggestions (never authoritative)",
    "8. Inferred user preferences (informative only)",
]


def check_authority(agent_authority: int, required_authority: int) -> bool:
    """Check if agent has sufficient authority for an action."""
    return agent_authority <= required_authority


def get_risk_tier(action: str, impact: str, reversibility: bool) -> RiskTier:
    """Determine risk tier for an action."""
    if impact == "none" and reversibility:
        return RiskTier.R0
    elif impact == "low" and reversibility:
        return RiskTier.R1
    elif impact == "low":
        return RiskTier.R2
    elif impact == "medium":
        return RiskTier.R3
    elif impact == "high" and not reversibility:
        return RiskTier.R4
    elif impact == "high":
        return RiskTier.R5
    elif impact == "critical":
        return RiskTier.R6
    return RiskTier.R3
