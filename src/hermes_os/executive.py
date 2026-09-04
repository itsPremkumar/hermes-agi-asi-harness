"""
HERMES INTELLIGENCE OS — EXECUTIVE KERNEL
=========================================
The central operating-system kernel coordinating:
Goal • Mission • Policy • State • Decisions • Resources • Safety
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


class ExecutiveKernel:
    """The central executive coordinating control over the intelligence operating system."""

    def __init__(self):
        self.goals = GoalController()
        self.state = StateController()
        self.resources = ResourceController()
        self.safety = SafetyController()
