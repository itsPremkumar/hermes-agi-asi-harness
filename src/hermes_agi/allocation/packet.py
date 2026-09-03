"""
Hermes AGI/ASI Harness — Hermes Mission Allocation Packet.

The formal contract and execution packet dispatched from the Harness to the Hermes Agent.
Contains goal criteria, research facts, deliberate invariants, and sandboxed tool permissions.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HermesMissionPacket:
    """A formal mission execution packet dispatched to the Hermes AI Agent."""
    mission_id: str = field(default_factory=lambda: f"mission-{uuid.uuid4().hex[:8]}")
    goal: str = ""
    assigned_role: str = "hermes-coder"
    assigned_model: str = "hermes-3-70b"
    goal_contract: dict[str, Any] = field(default_factory=dict)
    research_dossier: dict[str, Any] = field(default_factory=dict)
    thinking_summary: dict[str, Any] = field(default_factory=dict)
    plan_steps: list[dict[str, Any]] = field(default_factory=list)
    tool_whitelist: list[str] = field(default_factory=list)
    completion_criteria: list[str] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=lambda: {"max_steps": 25, "timeout_seconds": 300})
    status: str = "dispatched"  # dispatched, executing, monitored, verified, completed, failed
    dispatched_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "goal": self.goal,
            "assigned_role": self.assigned_role,
            "assigned_model": self.assigned_model,
            "status": self.status,
            "plan_steps_count": len(self.plan_steps),
            "tool_whitelist": self.tool_whitelist,
            "completion_criteria": self.completion_criteria,
            "goal_contract": self.goal_contract,
            "research_dossier": self.research_dossier,
            "thinking_summary": self.thinking_summary,
            "budget": self.budget,
            "dispatched_at": self.dispatched_at,
        }
