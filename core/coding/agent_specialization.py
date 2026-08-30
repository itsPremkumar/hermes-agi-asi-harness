"""Agent Specialization — 15+ specialist roles."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

class AgentRole(str, Enum):
    REQUIREMENTS = "requirements"
    REPOSITORY_ANALYST = "repository_analyst"
    RESEARCH = "research"
    ARCHITECT = "architect"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    TEST = "test"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DEVOPS = "devops"
    REVIEWER = "reviewer"
    DEBUGGER = "debugger"
    RELEASE = "release"
    EXECUTOR = "executor"

@dataclass
class AgentSpec:
    id: str
    role: AgentRole
    capabilities: List[str]
    allowed_tools: List[str]
    risk_level: str = "medium"

class AgentSpecialist:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.agents: Dict[str, AgentSpec] = {}
    
    def create_agent(self, role: AgentRole, capabilities: List[str],
                     allowed_tools: List[str], risk_level: str = "medium") -> AgentSpec:
        agent = AgentSpec(id=str(uuid.uuid4()), role=role,
                         capabilities=capabilities, allowed_tools=allowed_tools,
                         risk_level=risk_level)
        self.agents[agent.id] = agent
        return agent
    
    def get_by_role(self, role: AgentRole) -> List[AgentSpec]:
        return [a for a in self.agents.values() if a.role == role]
    
    def get_state(self) -> Dict[str, Any]:
        return {"agents": len(self.agents), "roles": list(set(a.role.value for a in self.agents.values()))}
