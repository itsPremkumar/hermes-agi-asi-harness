"""
HERMES INTELLIGENCE OS — PLANE 10: COGNITIVE OS & META-REASONING
================================================================
Coordinates multiple specialized reasoning modes:
- Deductive • Causal • Counterfactual • Probabilistic • Programmatic
Includes explicit Meta-Reasoning pre-action evaluation:
- Assumptions • Falsification criteria • Epistemic confidence • Compute allocation
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.cognitive")


class ReasoningMode(str, Enum):
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    CAUSAL = "causal"
    COUNTERFACTUAL = "counterfactual"
    PROBABILISTIC = "probabilistic"
    PROGRAMMATIC = "programmatic"


@dataclass
class MetaReasoningAssessment:
    """Pre-action epistemological reflection on what is known, assumed, and risk-bearing."""
    assessment_id: str = field(default_factory=lambda: f"mr-{uuid.uuid4().hex[:8]}")
    what_is_known: list[str] = field(default_factory=list)
    key_assumptions: list[str] = field(default_factory=list)
    critical_unknowns: list[str] = field(default_factory=list)
    falsification_criteria: list[str] = field(default_factory=list)
    requires_external_search: bool = False
    requires_simulation: bool = False
    recommended_reasoning_mode: ReasoningMode = ReasoningMode.PROGRAMMATIC
    recommended_compute_tier: str = "standard"  # fast, standard, deep_deliberation
    confidence: float = 0.85
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "what_is_known": self.what_is_known,
            "key_assumptions": self.key_assumptions,
            "critical_unknowns": self.critical_unknowns,
            "falsification_criteria": self.falsification_criteria,
            "requires_external_search": self.requires_external_search,
            "requires_simulation": self.requires_simulation,
            "recommended_reasoning_mode": self.recommended_reasoning_mode.value,
            "recommended_compute_tier": self.recommended_compute_tier,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


class MetaCognitionEngine:
    """
    Executes the pre-action meta-reasoning turn before any planner or agent acts.
    Forces explicit examination of assumptions and prevents hallucinatory jumps.
    """

    def __init__(self):
        pass

    def evaluate_intent(
        self,
        task_description: str,
        context_summary: str = "",
        risk_level: str = "medium",
    ) -> MetaReasoningAssessment:
        """Analyze epistemic posture before plan decomposition."""
        desc_lower = task_description.lower()

        # 1. Unknowns & Search needs
        needs_search = any(k in desc_lower for k in ("unknown", "latest", "benchmark", "documentation", "api", "research"))
        # 2. Simulation needs
        needs_sim = any(k in desc_lower for k in ("concurrency", "distributed", "race condition", "race_condition", "deadlock", "stress", "performance", "leak"))
        # 3. Reasoning mode
        if any(k in desc_lower for k in ("why", "root cause", "diagnose", "fix", "regression")):
            mode = ReasoningMode.CAUSAL
        elif any(k in desc_lower for k in ("what if", "alternative", "counterfactual")):
            mode = ReasoningMode.COUNTERFACTUAL
        elif any(k in desc_lower for k in ("prove", "theorem", "formal", "verify")):
            mode = ReasoningMode.DEDUCTIVE
        elif any(k in desc_lower for k in ("code", "script", "algorithm", "implement")):
            mode = ReasoningMode.PROGRAMMATIC
        else:
            mode = ReasoningMode.DEDUCTIVE

        # Compute tier
        if risk_level == "critical" or needs_sim:
            compute_tier = "deep_deliberation"
        elif needs_search:
            compute_tier = "standard"
        else:
            compute_tier = "fast"

        knowns = [f"Objective is: {task_description[:50]}..."]
        if context_summary:
            knowns.append(f"Context: {context_summary[:60]}...")

        assumptions = [
            "Local environment matches requirements",
            "Tool execution semantics are deterministic",
        ]
        falsifications = [
            "Non-zero exit code during verification",
            "Broken invariant or unhandled exception",
        ]

        return MetaReasoningAssessment(
            what_is_known=knowns,
            key_assumptions=assumptions,
            critical_unknowns=["dynamic runtime dependencies"] if needs_search else [],
            falsification_criteria=falsifications,
            requires_external_search=needs_search,
            requires_simulation=needs_sim,
            recommended_reasoning_mode=mode,
            recommended_compute_tier=compute_tier,
            confidence=0.90 if not needs_search else 0.70,
        )
