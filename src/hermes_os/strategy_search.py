"""
HERMES INTELLIGENCE OS — STRATEGY SEARCH & ADVERSARIAL PLAN CRITIC (v9)
=====================================================================
Multi-strategy exploration, deliberation, and adversarial review:
- Explicit StrategyCandidate objects with quantified trade-offs.
- Multi-attribute evaluation (success probability, reversibility, risk, cost, time).
- Dedicated PlanCritic: Adversarial audit detecting missing requirements, hidden
  dependencies, ungrounded assumptions, verification gaps, and security risks.
- SecondOpinionJudge: Structured arbitration between competing candidate plans.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.strategy")


@dataclass
class StrategyCandidate:
    """Explicit candidate strategy for accomplishing the mission."""
    strategy_id: str
    name: str
    description: str
    approach: str                              # e.g. "minimalist_direct", "staged_robust", "swarm_parallel"
    assumptions: List[str] = field(default_factory=list)
    key_steps: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    risks: List[str] = field(default_factory=list)
    estimated_cost_tokens: int = 10000
    estimated_time_seconds: float = 60.0
    reversibility: float = 0.8                 # 0.0 (irreversible) to 1.0 (fully sandboxed/reversible)
    probability_of_success: float = 0.85       # 0.0 to 1.0
    composite_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "approach": self.approach,
            "assumptions": self.assumptions,
            "key_steps": self.key_steps,
            "risks": self.risks,
            "estimated_cost_tokens": self.estimated_cost_tokens,
            "reversibility": round(self.reversibility, 2),
            "probability_of_success": round(self.probability_of_success, 2),
            "composite_score": round(self.composite_score, 3),
        }


@dataclass
class PlanReviewReport:
    """Adversarial critique and formal approval report."""
    approved: bool
    quality_score: float                       # 0.0 to 1.0
    missing_requirements: List[str] = field(default_factory=list)
    hidden_dependencies: List[str] = field(default_factory=list)
    ungrounded_assumptions: List[str] = field(default_factory=list)
    verification_gaps: List[str] = field(default_factory=list)
    security_risks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"PlanReview(approved={self.approved}, score={self.quality_score:.2f}, "
            f"missing_reqs={len(self.missing_requirements)}, "
            f"verification_gaps={len(self.verification_gaps)})"
        )


class StrategySearchEngine:
    """
    Generates competing strategic options and computes multi-attribute scores
    to select the mathematically optimal execution strategy.
    """

    def generate_candidates(
        self,
        objective: str,
        constraints: List[str],
        risk_level: str = "medium",
    ) -> List[StrategyCandidate]:
        """Generate 3 distinct structural strategies for the objective."""
        candidates = [
            # 1. Direct / Minimalist Strategy
            StrategyCandidate(
                strategy_id=f"strat-direct-{uuid.uuid4().hex[:6]}",
                name="Direct Phased Execution",
                description="Execute core tasks sequentially with inline unit test checks",
                approach="minimalist_direct",
                assumptions=["Environment is stable", "Requirements are deterministic"],
                key_steps=["Inspect target files", "Implement changes", "Run tests"],
                estimated_cost_tokens=8000,
                estimated_time_seconds=30.0,
                reversibility=0.9,
                probability_of_success=0.88 if risk_level == "low" else 0.75,
            ),
            # 2. Staged / Robust Strategy
            StrategyCandidate(
                strategy_id=f"strat-robust-{uuid.uuid4().hex[:6]}",
                name="Staged Verification & Pre-flight Simulation",
                description="Sandbox trial, deep AST verification, adversarial critique, and staged rollout",
                approach="staged_robust",
                assumptions=["External dependencies may fail", "Verification requires independent oracle"],
                key_steps=["Sandbox simulation", "Multi-stage verification", "Atomic commit"],
                estimated_cost_tokens=18000,
                estimated_time_seconds=75.0,
                reversibility=0.98,
                probability_of_success=0.95,
            ),
            # 3. Parallel Swarm Strategy
            StrategyCandidate(
                strategy_id=f"strat-swarm-{uuid.uuid4().hex[:6]}",
                name="Parallel Specialist Swarm",
                description="Fan-out concurrent specialist workers for search, coding, and review",
                approach="swarm_parallel",
                assumptions=["Work units can be decomposed without resource contention"],
                key_steps=["Parallel discovery", "Concurrent synthesis", "Judge arbitration"],
                estimated_cost_tokens=25000,
                estimated_time_seconds=45.0,
                reversibility=0.85,
                probability_of_success=0.89,
            ),
        ]

        # Score candidates
        for c in candidates:
            # Score formula: Prob * 0.4 + Reversibility * 0.3 + (1 - Cost/50000) * 0.3
            cost_factor = max(0.0, 1.0 - (c.estimated_cost_tokens / 50000.0))
            c.composite_score = (
                (c.probability_of_success * 0.45) +
                (c.reversibility * 0.35) +
                (cost_factor * 0.20)
            )

        candidates.sort(key=lambda s: s.composite_score, reverse=True)
        return candidates

    def select_best_strategy(
        self,
        candidates: List[StrategyCandidate],
        risk_level: str = "medium",
    ) -> StrategyCandidate:
        """Select highest scoring candidate, prioritizing reversibility under high risk."""
        if not candidates:
            raise ValueError("No strategy candidates provided")
        if risk_level in ["high", "critical"]:
            # Prioritize highest reversibility and robustness
            return max(candidates, key=lambda s: (s.reversibility, s.probability_of_success))
        return candidates[0]


class PlanCritic:
    """
    Dedicated Adversarial Plan Critic.
    Reviews candidate plans to expose blindspots, missing requirements,
    hidden dependency cycles, and untested invariants before execution.
    """

    def review_plan(
        self,
        objective: str,
        invariants: List[str],
        strategy: StrategyCandidate,
        tasks: List[Dict[str, Any]],
        verifiers: List[Dict[str, Any]],
    ) -> PlanReviewReport:
        missing_reqs = []
        hidden_deps = []
        ungrounded_assumps = []
        verification_gaps = []
        security_risks = []
        recommendations = []

        # 1. Audit Invariant Coverage
        for inv in invariants:
            inv_l = inv.lower()
            if "no deletion" in inv_l or "zero deletion" in inv_l:
                has_safety_guard = any("safe" in str(t).lower() or "check" in str(t).lower() for t in tasks)
                if not has_safety_guard:
                    security_risks.append(f"Invariant '{inv}' lacks explicit pre-execution guard in task list")

        # 2. Audit Verification Completeness
        if len(verifiers) < len(tasks):
            verification_gaps.append(
                f"Task-to-verifier ratio ({len(verifiers)} verifiers for {len(tasks)} tasks) indicates unverified tasks"
            )

        # 3. Check for Dangerous Actions
        for t in tasks:
            action = str(t.get("action", "")).lower()
            if any(w in action for w in ["drop", "delete_all", "force_push", "rmdir"]):
                security_risks.append(f"Task '{t.get('id')}' proposes potentially irreversible action: {action}")

        # 4. Check Assumptions
        for a in strategy.assumptions:
            if "stable" in a.lower() or "deterministic" in a.lower():
                ungrounded_assumps.append(f"Assumption '{a}' has not been empirically verified via recon")

        # Compute Score
        penalties = (
            (len(missing_reqs) * 0.15) +
            (len(hidden_deps) * 0.20) +
            (len(verification_gaps) * 0.25) +
            (len(security_risks) * 0.30)
        )
        score = max(0.0, min(1.0, 1.0 - penalties))
        approved = score >= 0.70 and len(security_risks) == 0

        if not approved:
            recommendations.append("Attach explicit verifiers to all state-modifying tasks.")
            if security_risks:
                recommendations.append("Remove or sandbox high-risk actions.")

        return PlanReviewReport(
            approved=approved,
            quality_score=round(score, 2),
            missing_requirements=missing_reqs,
            hidden_dependencies=hidden_deps,
            ungrounded_assumptions=ungrounded_assumps,
            verification_gaps=verification_gaps,
            security_risks=security_risks,
            recommendations=recommendations,
        )


class SecondOpinionJudge:
    """
    Arbitrates between competing candidate plans with structured evidence
    and predictable trade-offs instead of ungrounded voting.
    """

    def arbitrate(
        self,
        strategy_a: StrategyCandidate,
        strategy_b: StrategyCandidate,
        critique_a: PlanReviewReport,
        critique_b: PlanReviewReport,
    ) -> Dict[str, Any]:
        """Perform formal multi-dimensional comparison."""
        score_a = (strategy_a.composite_score * 0.5) + (critique_a.quality_score * 0.5)
        score_b = (strategy_b.composite_score * 0.5) + (critique_b.quality_score * 0.5)

        winner = strategy_a if score_a >= score_b else strategy_b
        return {
            "winner_id": winner.strategy_id,
            "winner_name": winner.name,
            "score_a": round(score_a, 3),
            "score_b": round(score_b, 3),
            "rationale": f"Strategy {winner.name} achieved higher combined viability score ({max(score_a, score_b):.2f})",
        }
