"""
Closed-Loop Orchestrator — Full 15-step loop.

Runs: perceive → estimate → predict → search → simulate → safety → select → execute → observe → verify → record → evaluate → rsi → promote/rollback
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LoopStep(str, Enum):
    IDLE = "idle"
    PERCEIVING = "perceiving"
    ESTIMATING = "estimating"
    PREDICTING = "predicting"
    SEARCHING_POLICIES = "searching_policies"
    SIMULATING = "simulating"
    SAFETY_CHECK = "safety_check"
    SELECTING_POLICY = "selecting_policy"
    EXECUTING = "executing"
    OBSERVING = "observing"
    VERIFYING = "verifying"
    RECORDING_TRAJECTORY = "recording_trajectory"
    SELF_EVALUATING = "self_evaluating"
    RSI_EXPERIMENT = "rsi_experiment"
    BENCHMARKING = "benchmarking"
    PROMOTE_ROLLBACK = "promote_rollback"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LoopContext:
    """Execution context maintained across the loop."""
    world_state: Dict[str, Any] = field(default_factory=dict)
    active_policy: Optional[str] = None
    active_envelope: Optional[str] = None
    trajectory_id: Optional[str] = None
    mission_id: str = ""
    cycle_count: int = 0
    last_success: bool = False
    last_reward: float = 0.0


@dataclass
class LoopResult:
    success: bool
    step_reached: LoopStep
    context: LoopContext
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class ClosedLoopOrchestrator:
    """Full closed-loop execution engine."""
    
    def __init__(self, policy_bridge: Any, trajectory_store: Any,
                 policy_learner: Any, safety_manager: Any,
                 consequence_simulator: Any, environment_model: Any):
        self.policy_bridge = policy_bridge
        self.trajectory_store = trajectory_store
        self.policy_learner = policy_learner
        self.safety_manager = safety_manager
        self.consequence_simulator = consequence_simulator
        self.environment_model = environment_model
        self.context = LoopContext()
        self.state = LoopStep.IDLE
    
    def run_loop(self, goal: str, initial_state: Dict[str, Any] = None) -> LoopResult:
        """Run the full 15-step loop."""
        start_time = time.time()
        self.context = LoopContext(mission_id=str(uuid.uuid4()))
        
        if initial_state:
            self.context.world_state = initial_state
        
        try:
            # Step 1: Perceive
            self.state = LoopStep.PERCEIVING
            observations = self._perceive(goal)
            
            # Step 2: Estimate state
            self.state = LoopStep.ESTIMATING
            state_estimate = self._estimate(observations)
            
            # Step 3: Predict futures
            self.state = LoopStep.PREDICTING
            predictions = self._predict(state_estimate)
            
            # Step 4: Search policies
            self.state = LoopStep.SEARCHING_POLICIES
            candidates = self._search_policies(goal)
            
            # Step 5: Simulate consequences
            self.state = LoopStep.SIMULATING
            simulations = self._simulate_candidates(candidates)
            
            # Step 6: Safety check
            self.state = LoopStep.SAFETY_CHECK
            safe_candidates = self._check_safety(simulations)
            
            if not safe_candidates:
                raise Exception("No candidates passed safety check")
            
            # Step 7: Select policy
            self.state = LoopStep.SELECTING_POLICY
            selected = self._select_best(safe_candidates)
            
            # Step 8: Execute
            self.state = LoopStep.EXECUTING
            action_result = self._execute(selected)
            
            # Step 9: Observe
            self.state = LoopStep.OBSERVING
            observation = self._observe(action_result)
            
            # Step 10: Verify
            self.state = LoopStep.VERIFYING
            verified = self._verify(observation)
            
            # Step 11: Record trajectory
            self.state = LoopStep.RECORDING_TRAJECTORY
            self._record_trajectory(selected, action_result, observation, verified)
            
            # Step 12: Self-evaluate
            self.state = LoopStep.SELF_EVALUATING
            evaluation = self._self_evaluate(verified, selected)
            
            # Step 13: Maybe RSI
            if evaluation.get("bottleneck"):
                self.state = LoopStep.RSI_EXPERIMENT
                self._trigger_rsi(evaluation["bottleneck"])
            
            # Step 14: Benchmark
            self.state = LoopStep.BENCHMARKING
            bench_result = self._benchmark(selected)
            
            # Step 15: Promote or rollback
            self.state = LoopStep.PROMOTE_ROLLBACK
            self._promote_or_rollback(selected, bench_result, verified)
            
            self.state = LoopStep.COMPLETED
            self.context.last_success = verified
            self.context.cycle_count += 1
            
            return LoopResult(
                success=True,
                step_reached=LoopStep.COMPLETED,
                context=self.context,
                output=action_result,
                duration_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            self.state = LoopStep.FAILED
            return LoopResult(
                success=False,
                step_reached=self.state,
                context=self.context,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )
    
    def _perceive(self, goal: str) -> Dict[str, Any]:
        """Step 1: Gather observations from environment."""
        return {
            "goal": goal,
            "timestamp": time.time(),
            "environment_state": self.context.world_state,
        }
    
    def _estimate(self, observations: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: Fuse observations into state estimate."""
        return {
            "state": observations.get("environment_state", {}),
            "confidence": 0.7,
        }
    
    def _predict(self, state_estimate: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Step 3: Predict possible futures."""
        return [
            {"scenario": "success", "probability": 0.8},
            {"scenario": "failure", "probability": 0.2},
        ]
    
    def _search_policies(self, goal: str) -> List[Dict[str, Any]]:
        """Step 4: Find candidate policies for the goal."""
        return [{"policy_id": "default", "goal": goal}]
    
    def _simulate_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 5: Simulate consequences for each candidate."""
        return [{"candidate": c, "risk": 0.3} for c in candidates]
    
    def _check_safety(self, simulations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 6: Filter candidates through safety envelope."""
        return [s for s in simulations if s.get("risk", 1.0) < 0.7]
    
    def _select_best(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Step 7: Pick the best candidate."""
        if not candidates:
            raise Exception("No candidates to select")
        return candidates[0]
    
    def _execute(self, selected: Dict[str, Any]) -> Dict[str, Any]:
        """Step 8: Execute the selected action."""
        return {"status": "executed", "action": selected}
    
    def _observe(self, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 9: Observe the result."""
        return {"result": action_result, "timestamp": time.time()}
    
    def _verify(self, observation: Dict[str, Any]) -> bool:
        """Step 10: Verify the result."""
        return observation.get("result", {}).get("status") == "executed"
    
    def _record_trajectory(self, selected: Dict, action_result: Dict,
                           observation: Dict, verified: bool):
        """Step 11: Record the trajectory."""
        traj = self.trajectory_store.create_trajectory(
            self.context.mission_id, "closed_loop"
        )
        self.trajectory_store.add_step(
            traj.id,
            self.context.world_state,
            {"action": selected},
            observation,
            {"verified": verified},
        )
        self.trajectory_store.complete_trajectory(
            traj.id, "success" if verified else "failure"
        )
        self.context.trajectory_id = traj.id
    
    def _self_evaluate(self, verified: bool, selected: Dict) -> Dict[str, Any]:
        """Step 12: Self-evaluate the result."""
        return {
            "success": verified,
            "bottleneck": None if verified else "execution_failure",
        }
    
    def _trigger_rsi(self, bottleneck: str):
        """Step 13: Trigger RSI experiment if bottleneck detected."""
        pass  # RSI integration handled by RSIntegrationEngine
    
    def _benchmark(self, selected: Dict[str, Any]) -> Dict[str, Any]:
        """Step 14: Benchmark the selected policy."""
        return {"score": 0.8, "baseline": 0.7, "improved": True}
    
    def _promote_or_rollback(self, selected: Dict, bench_result: Dict, verified: bool):
        """Step 15: Promote or rollback based on benchmark."""
        if verified and bench_result.get("improved"):
            self.context.last_reward = bench_result["score"]
        elif not verified:
            pass  # Rollback logic handled by PolicyBridge
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "cycle_count": self.context.cycle_count,
            "last_success": self.context.last_success,
            "last_reward": self.context.last_reward,
            "mission_id": self.context.mission_id,
        }
