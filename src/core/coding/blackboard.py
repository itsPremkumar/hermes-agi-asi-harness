"""Engineering Blackboard - Shared workspace for agents."""
from __future__ import annotations

import uuid
from typing import Any


class Blackboard:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.objective: str = ""
        self.requirements: list[str] = []
        self.architecture: str = ""
        self.hypotheses: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []
        self.evidence: list[dict[str, Any]] = []
        self.blocked_tasks: list[str] = []
        self.active_agents: list[str] = []
    
    def publish(self, key: str, value: Any):
        if hasattr(self, key):
            setattr(self, key, value)
    
    def get_state(self) -> dict[str, Any]:
        return {"objective": self.objective, "agents": len(self.active_agents)}
