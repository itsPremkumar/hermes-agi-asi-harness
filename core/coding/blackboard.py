"""Engineering Blackboard - Shared workspace for agents."""
from __future__ import annotations
import uuid
from typing import Any, Dict, List

class Blackboard:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.objective: str = ""
        self.requirements: List[str] = []
        self.architecture: str = ""
        self.hypotheses: List[Dict[str, Any]] = []
        self.decisions: List[Dict[str, Any]] = []
        self.evidence: List[Dict[str, Any]] = []
        self.blocked_tasks: List[str] = []
        self.active_agents: List[str] = []
    
    def publish(self, key: str, value: Any):
        if hasattr(self, key):
            setattr(self, key, value)
    
    def get_state(self) -> Dict[str, Any]:
        return {"objective": self.objective, "agents": len(self.active_agents)}
