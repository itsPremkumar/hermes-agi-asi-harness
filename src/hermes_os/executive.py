"""
HERMES INTELLIGENCE OS — PLANE 05: EXECUTIVE CONTROL PLANE
==========================================================
The central operating-system kernel scheduler coordinating the 14 controllers:
Goal • Mission • State • Decision • Context • Planning • Agent • Tool
• Resource • Verification • Learning • Evolution • Safety • Health
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from context_os.invariants import GoalContract, GoalInvariant

logger = logging.getLogger("hermes.os.executive")


class GoalController:
    """Compiles raw user requests into authoritative Goal Contracts with immutable invariants."""

    def compile_goal(
        self,
        request: str,
        invariants: Optional[list[str]] = None,
        risk_level: str = "medium",
    ) -> GoalContract:
        cid = f"contract-{uuid.uuid4().hex[:8]}"
        inv_list = [
            GoalInvariant(
                name="existing_code_must_not_be_deleted",
                description="Zero deletion of existing working functionality",
                severity="critical",
            ),
            GoalInvariant(
                name="security_requirements_preserved",
                description="All security contracts and sandbox permissions must hold",
                severity="critical",
            ),
            GoalInvariant(
                name="budget_must_remain_within_limit",
                description="Token and compute ceilings must be strictly respected",
                severity="high",
            ),
        ]
        if invariants:
            for inv_str in invariants:
                inv_list.append(GoalInvariant(name=inv_str, description=f"Invariant: {inv_str}", severity="high"))

        return GoalContract(
            contract_id=cid,
            objective=request,
            desired_world_state={"objective_achieved": True, "task": request},
            invariants=inv_list,
            success_conditions=["all_tasks_completed", "invariants_verified", "completion_proof_earned"],
            failure_conditions=["unhandled_exception", "invariant_violation", "timeout_exceeded"],
            risk_level=risk_level,
        )


class StateController:
    """Tracks durable operational states across the operating system."""

    def __init__(self):
        self.current_state: str = "INITIALIZING"
        self.state_history: list[dict[str, Any]] = []

    def transition_to(self, new_state: str, reason: str = "") -> None:
        logger.info("OS State Transition: %s -> %s (Reason: %s)", self.current_state, new_state, reason)
        self.state_history.append({
            "from_state": self.current_state,
            "to_state": new_state,
            "reason": reason,
            "timestamp": time.time(),
        })
        self.current_state = new_state


class ResourceController:
    """Tracks tokens, compute time, memory, and concurrent agent slots."""

    def __init__(self, token_limit: int = 1000000, time_limit_seconds: float = 300.0):
        self.token_limit = token_limit
        self.time_limit = time_limit_seconds
        self.tokens_used: int = 0
        self.start_time: float = time.time()
        self.active_agent_slots: int = 0

    def consume_tokens(self, count: int) -> bool:
        self.tokens_used += count
        return self.tokens_used <= self.token_limit

    def is_time_exhausted(self) -> bool:
        return (time.time() - self.start_time) >= self.time_limit


class SafetyController:
    """Enforces safety policy outside primary agent authority."""

    def __init__(self):
        self._blocked_patterns = ["rm -rf /", "mkfs", ":(){ :|:& };:"]

    def authorize_action(self, action_type: str, args: dict[str, Any], goal_contract: GoalContract) -> tuple[bool, str]:
        cmd = str(args.get("command", "") or args.get("cmd", ""))
        for b in self._blocked_patterns:
            if b in cmd:
                return False, f"Safety violation: Dangerous command pattern detected: '{b}'"

        # Check immutable goal invariants
        violations = goal_contract.check_invariants(args)
        if violations:
            return False, f"Safety violation: {'; '.join(violations)}"

        return True, "Authorized"


class MissionController:
    """Manages mission DAGs, task states, and checkpoint coordinates."""

    def __init__(self):
        self.active_missions: dict[str, dict[str, Any]] = {}

    def register_mission(self, mission_id: str, contract: GoalContract, dag: list[dict[str, Any]]) -> None:
        self.active_missions[mission_id] = {
            "contract": contract.to_dict(),
            "dag": dag,
            "status": "in_progress",
            "created_at": time.time(),
        }

    def complete_mission(self, mission_id: str, success: bool = True) -> None:
        if mission_id in self.active_missions:
            self.active_missions[mission_id]["status"] = "completed" if success else "failed"


class DecisionController:
    """Records and validates system-level architectural and strategic decisions."""

    def __init__(self):
        self.decisions: list[dict[str, Any]] = []

    def record(self, decision_type: str, chosen: str, alternatives: list[str], rationale: str) -> None:
        self.decisions.append({
            "id": f"dec-{uuid.uuid4().hex[:6]}",
            "type": decision_type,
            "chosen": chosen,
            "alternatives": alternatives,
            "rationale": rationale,
            "timestamp": time.time(),
        })


class ContextController:
    """Supervises dynamic context allocation and compaction."""

    def __init__(self, max_tokens: int = 200000):
        self.max_tokens = max_tokens
        self.active_utilization: float = 0.0

    def record_usage(self, used: int) -> None:
        self.active_utilization = used / self.max_tokens if self.max_tokens > 0 else 0.0


class PlanningController:
    """Supervises search algorithms and planner selection."""

    def __init__(self):
        self.active_mode: str = "linear"

    def set_mode(self, mode: str) -> None:
        self.active_mode = mode


class AgentController:
    """Manages agent pool concurrency, slot reservations, and lifecycle."""

    def __init__(self, max_slots: int = 8):
        self.max_slots = max_slots
        self.active_agents: dict[str, str] = {}

    def acquire_slot(self, agent_id: str, role: str) -> bool:
        if len(self.active_agents) >= self.max_slots:
            return False
        self.active_agents[agent_id] = role
        return True

    def release_slot(self, agent_id: str) -> None:
        self.active_agents.pop(agent_id, None)


class ToolController:
    """Tracks tool availability and usage telemetry."""

    def __init__(self):
        self.tool_invocations: dict[str, int] = {}

    def record_call(self, tool_name: str) -> None:
        self.tool_invocations[tool_name] = self.tool_invocations.get(tool_name, 0) + 1


class VerificationController:
    """Tracks proof requirements and verification tier thresholds."""

    def __init__(self):
        self.proofs_verified: int = 0
        self.proofs_rejected: int = 0

    def record_verdict(self, verified: bool) -> None:
        if verified:
            self.proofs_verified += 1
        else:
            self.proofs_rejected += 1


class LearningController:
    """Supervises procedural skill extraction and experience replay."""

    def __init__(self):
        self.skills_promoted: int = 0

    def record_skill_learned(self) -> None:
        self.skills_promoted += 1


class EvolutionController:
    """Regulates mutation rates, sandbox testing, and holdout gates."""

    def __init__(self):
        self.active_generation: int = 1
        self.mutations_approved: int = 0

    def record_mutation(self) -> None:
        self.mutations_approved += 1


class HealthController:
    """Monitors heartbeat, memory saturation, and stall flags."""

    def __init__(self):
        self.last_heartbeat: float = time.time()
        self.stall_detected: bool = False

    def heartbeat(self) -> None:
        self.last_heartbeat = time.time()

    def is_alive(self, timeout_seconds: float = 60.0) -> bool:
        return (time.time() - self.last_heartbeat) <= timeout_seconds


class ExecutiveKernel:
    """The central executive coordinating control over the intelligence operating system."""

    def __init__(self):
        self.goals = GoalController()
        self.missions = MissionController()
        self.state = StateController()
        self.decisions = DecisionController()
        self.context = ContextController()
        self.planning = PlanningController()
        self.agents = AgentController()
        self.tools = ToolController()
        self.resources = ResourceController()
        self.verification = VerificationController()
        self.learning = LearningController()
        self.evolution = EvolutionController()
        self.safety = SafetyController()
        self.health = HealthController()
