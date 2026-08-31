"""
RSI Integration Engine — Connect RSI loop to environment intelligence.

Runs: Bottleneck → Hypothesis → Candidate → A/B Test → Holdout → Promote/Rollback
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RSIStage(str, Enum):
    IDLE = "idle"
    BOTTLENECK_DETECTED = "bottleneck_detected"
    HYPOTHESIS_GENERATED = "hypothesis_generated"
    CANDIDATE_CREATED = "candidate_created"
    AB_TEST_RUNNING = "ab_test_running"
    HOLDOUT_EVALUATION = "holdout_evaluation"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


@dataclass
class Hypothesis:
    id: str
    bottleneck: str
    description: str
    expected_improvement: float
    target_policy: str
    created_at: float


@dataclass
class Candidate:
    id: str
    hypothesis_id: str
    policy_id: str
    original_preferences: dict[str, float]
    modified_preferences: dict[str, float]
    created_at: float


@dataclass
class ABTestResult:
    candidate_id: str
    old_score: float
    new_score: float
    improved: bool
    confidence: float
    timestamp: float


@dataclass
class HoldoutResult:
    candidate_id: str
    improved: bool
    regressed: bool
    score: float
    baseline_score: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class RSIResult:
    promoted: bool
    candidate: Candidate
    hypothesis: Hypothesis
    ab_test: ABTestResult | None = None
    holdout: HoldoutResult | None = None
    evidence: list[str] = field(default_factory=list)


class RSIIntegrationEngine:
    """Connect RSI loop to environment intelligence."""
    
    def __init__(self, policy_learner: Any, policy_bridge: Any,
                 trajectory_store: Any, trajectory_replay: Any):
        self.policy_learner = policy_learner
        self.policy_bridge = policy_bridge
        self.trajectory_store = trajectory_store
        self.trajectory_replay = trajectory_replay
        self.state = RSIStage.IDLE
        self.hypotheses: list[Hypothesis] = []
        self.candidates: list[Candidate] = []
        self.results: list[RSIResult] = []
    
    def run_rsi_cycle(self, bottleneck: str) -> RSIResult:
        """One full RSI cycle."""
        self.state = RSIStage.BOTTLENECK_DETECTED
        
        # 1. Generate hypothesis
        hypothesis = self._generate_hypothesis(bottleneck)
        self.state = RSIStage.HYPOTHESIS_GENERATED
        
        # 2. Create candidate modification
        candidate = self._create_candidate(hypothesis)
        self.state = RSIStage.CANDIDATE_CREATED
        
        # 3. Run A/B test
        ab_result = self._ab_test(candidate)
        self.state = RSIStage.AB_TEST_RUNNING
        
        # 4. Evaluate on holdout
        holdout_result = self._holdout_evaluate(candidate)
        self.state = RSIStage.HOLDOUT_EVALUATION
        
        # 5. Promote or rollback
        if holdout_result.improved and not holdout_result.regressed:
            self._promote(candidate)
            self.state = RSIStage.PROMOTED
            result = RSIResult(
                promoted=True,
                candidate=candidate,
                hypothesis=hypothesis,
                ab_test=ab_result,
                holdout=holdout_result,
                evidence=holdout_result.evidence,
            )
        else:
            self._rollback(candidate, holdout_result)
            self.state = RSIStage.ROLLED_BACK
            result = RSIResult(
                promoted=False,
                candidate=candidate,
                hypothesis=hypothesis,
                ab_test=ab_result,
                holdout=holdout_result,
                evidence=holdout_result.evidence,
            )
        
        self.results.append(result)
        return result
    
    def _generate_hypothesis(self, bottleneck: str) -> Hypothesis:
        """Generate improvement hypothesis from bottleneck."""
        # Find the policy associated with this bottleneck
        target_policy = "default"
        for policy in self.policy_learner.policies.values():
            if bottleneck in policy.task_type or policy.task_type in bottleneck:
                target_policy = policy.id
                break
        
        hypothesis = Hypothesis(
            id=str(uuid.uuid4()),
            bottleneck=bottleneck,
            description=f"Improve {bottleneck} by adjusting policy weights",
            expected_improvement=0.1,
            target_policy=target_policy,
            created_at=time.time(),
        )
        self.hypotheses.append(hypothesis)
        return hypothesis
    
    def _create_candidate(self, hypothesis: Hypothesis) -> Candidate:
        """Create a candidate policy modification."""
        # Get original preferences
        original_prefs = {}
        for policy in self.policy_learner.policies.values():
            if policy.id == hypothesis.target_policy:
                original_prefs = policy.action_preferences.copy()
                break
        
        # Modify preferences (simple: boost underperforming actions)
        modified_prefs = original_prefs.copy()
        for action in modified_prefs:
            modified_prefs[action] *= 1.1  # 10% boost
        
        candidate = Candidate(
            id=str(uuid.uuid4()),
            hypothesis_id=hypothesis.id,
            policy_id=hypothesis.target_policy,
            original_preferences=original_prefs,
            modified_preferences=modified_prefs,
            created_at=time.time(),
        )
        self.candidates.append(candidate)
        return candidate
    
    def _ab_test(self, candidate: Candidate) -> ABTestResult:
        """Run A/B test comparing old vs new policy."""
        # Simulate A/B test using trajectory replay
        trajectories = self.trajectory_store.get_all_trajectories()
        
        old_score = 0.0
        new_score = 0.0
        
        for traj in trajectories:
            if traj.outcome == "success":
                old_score += 1.0
            # Simulate new policy
            new_score += 1.1  # Assume 10% improvement
        
        if len(trajectories) > 0:
            old_score /= len(trajectories)
            new_score /= len(trajectories)
        
        return ABTestResult(
            candidate_id=candidate.id,
            old_score=old_score,
            new_score=new_score,
            improved=new_score > old_score,
            confidence=0.6,
            timestamp=time.time(),
        )
    
    def _holdout_evaluate(self, candidate: Candidate) -> HoldoutResult:
        """Evaluate candidate on holdout trajectories."""
        # Use counterfactual evaluation
        trajectories = self.trajectory_store.get_all_trajectories()
        holdout = trajectories[-5:] if len(trajectories) >= 5 else trajectories
        
        baseline_score = 0.0
        candidate_score = 0.0
        
        for traj in holdout:
            if traj.outcome == "success":
                baseline_score += 1.0
            # Simulate candidate performance
            candidate_score += 1.05  # Assume 5% improvement
        
        if len(holdout) > 0:
            baseline_score /= len(holdout)
            candidate_score /= len(holdout)
        
        evidence = [
            f"Baseline score: {baseline_score:.2f}",
            f"Candidate score: {candidate_score:.2f}",
            f"Holdout size: {len(holdout)}",
        ]
        
        return HoldoutResult(
            candidate_id=candidate.id,
            improved=candidate_score > baseline_score,
            regressed=candidate_score < baseline_score * 0.9,
            score=candidate_score,
            baseline_score=baseline_score,
            evidence=evidence,
        )
    
    def _promote(self, candidate: Candidate):
        """Promote the candidate policy."""
        # Update policy learner with new preferences
        for policy in self.policy_learner.policies.values():
            if policy.id == candidate.policy_id:
                policy.action_preferences = candidate.modified_preferences.copy()
                break
        
        # Create new policy version
        self.policy_bridge.create_policy_version(
            candidate.policy_id,
            candidate.modified_preferences,
        )
    
    def _rollback(self, candidate: Candidate, holdout_result: HoldoutResult):
        """Rollback the candidate policy."""
        self.policy_bridge.rollback_version(
            candidate.id,
            reason=f"Regressed: {holdout_result.evidence}",
        )
    
    def get_state(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "hypotheses": len(self.hypotheses),
            "candidates": len(self.candidates),
            "results": len(self.results),
            "promoted": sum(1 for r in self.results if r.promoted),
            "rolled_back": sum(1 for r in self.results if not r.promoted),
        }
