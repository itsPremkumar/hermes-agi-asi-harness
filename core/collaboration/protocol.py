"""
Multi-Agent Collaboration Protocol — Enable agents to collaborate on shared goals.

Agents can:
- Share world model updates
- Coordinate actions (avoid conflicts)
- Delegate tasks based on capability
- Debate when uncertain
- Reach consensus on high-impact decisions
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentRole(str, Enum):
    MANAGER = "manager"
    RESEARCHER = "researcher"
    CODER = "coder"
    CRITIC = "critic"
    EXECUTOR = "executor"
    MONITOR = "monitor"


@dataclass
class Agent:
    id: str
    name: str
    role: AgentRole
    capabilities: List[str]
    status: str = "idle"
    current_task: Optional[str] = None


@dataclass
class SubGoal:
    id: str
    description: str
    assigned_agent: Optional[str] = None
    status: str = "pending"
    dependencies: List[str] = field(default_factory=list)
    result: Any = None


@dataclass
class Conflict:
    id: str
    agent_a: str
    agent_b: str
    description: str
    resolution: Optional[str] = None


@dataclass
class CollaborationResult:
    success: bool
    sub_goals: List[SubGoal]
    conflicts: List[Conflict]
    results: Dict[str, Any]
    duration_ms: float


class AgentCollaborationProtocol:
    """Enable agents to collaborate on shared goals."""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.sub_goals: Dict[str, SubGoal] = {}
        self.conflicts: List[Conflict] = []
    
    def register_agent(self, name: str, role: AgentRole,
                       capabilities: List[str]) -> Agent:
        agent = Agent(
            id=str(uuid.uuid4()),
            name=name,
            role=role,
            capabilities=capabilities,
        )
        self.agents[agent.id] = agent
        return agent
    
    def coordinate(self, agents: List[Agent], goal: str,
                   world_state: Dict[str, Any]) -> CollaborationResult:
        """Coordinate multiple agents on a shared goal."""
        start_time = time.time()
        
        # 1. Decompose goal into sub-goals
        sub_goals = self._decompose_goal(goal)
        
        # 2. Match agents to sub-goals by capability
        assignments = self._assign_agents(agents, sub_goals, world_state)
        
        # 3. Check for conflicts
        conflicts = self._detect_conflicts(assignments)
        if conflicts:
            assignments = self._resolve_conflicts(assignments, conflicts)
        
        # 4. Execute (parallel where possible, sequential where needed)
        results = self._execute_coordinated(assignments, sub_goals)
        
        # 5. Synthesize results
        success = all(r.get("success", False) for r in results.values())
        
        return CollaborationResult(
            success=success,
            sub_goals=list(sub_goals.values()),
            conflicts=conflicts,
            results=results,
            duration_ms=(time.time() - start_time) * 1000,
        )
    
    def _decompose_goal(self, goal: str) -> Dict[str, SubGoal]:
        """Decompose a goal into sub-goals."""
        # Simple decomposition based on goal keywords
        sub_goals = {}
        
        if "deploy" in goal.lower():
            sub_goals["test"] = SubGoal(
                id=str(uuid.uuid4()),
                description="Run tests",
                dependencies=[],
            )
            sub_goals["build"] = SubGoal(
                id=str(uuid.uuid4()),
                description="Build artifact",
                dependencies=["test"],
            )
            sub_goals["deploy"] = SubGoal(
                id=str(uuid.uuid4()),
                description="Deploy to production",
                dependencies=["build"],
            )
        elif "research" in goal.lower():
            sub_goals["search"] = SubGoal(
                id=str(uuid.uuid4()),
                description="Search for information",
                dependencies=[],
            )
            sub_goals["analyze"] = SubGoal(
                id=str(uuid.uuid4()),
                description="Analyze findings",
                dependencies=["search"],
            )
            sub_goals["report"] = SubGoal(
                id=str(uuid.uuid4()),
                description="Generate report",
                dependencies=["analyze"],
            )
        else:
            sub_goals["execute"] = SubGoal(
                id=str(uuid.uuid4()),
                description=goal,
                dependencies=[],
            )
        
        self.sub_goals = sub_goals
        return sub_goals
    
    def _assign_agents(self, agents: List[Agent], sub_goals: Dict[str, SubGoal],
                       world_state: Dict[str, Any]) -> Dict[str, str]:
        """Match agents to sub-goals by capability."""
        assignments = {}
        available_agents = {a.id: a for a in agents}
        
        # Simple matching: assign based on role/capability
        capability_map = {
            "test": ["testing", "qa", "verification"],
            "build": ["coding", "build", "compilation"],
            "deploy": ["deployment", "devops", "operations"],
            "search": ["research", "search", "web_search"],
            "analyze": ["analysis", "research", "data_analysis"],
            "report": ["writing", "documentation", "reporting"],
            "execute": ["execution", "general"],
        }
        
        for sg_id, sg in sub_goals.items():
            required_caps = capability_map.get(sg_id, ["general"])
            
            # Find best matching agent
            best_agent = None
            best_score = -1
            
            for agent in available_agents.values():
                if agent.status != "idle":
                    continue
                
                score = len(set(agent.capabilities) & set(required_caps))
                if score > best_score:
                    best_score = score
                    best_agent = agent
            
            if best_agent:
                assignments[sg_id] = best_agent.id
                sg.assigned_agent = best_agent.id
                best_agent.status = "assigned"
                best_agent.current_task = sg_id
        
        return assignments
    
    def _detect_conflicts(self, assignments: Dict[str, str]) -> List[Conflict]:
        """Detect conflicts between agent assignments."""
        conflicts = []
        
        # Check for resource conflicts (same agent assigned to conflicting tasks)
        agent_tasks: Dict[str, List[str]] = {}
        for sg_id, agent_id in assignments.items():
            if agent_id not in agent_tasks:
                agent_tasks[agent_id] = []
            agent_tasks[agent_id].append(sg_id)
        
        # Check for dependency conflicts
        for sg_id, sg in self.sub_goals.items():
            for dep_id in sg.dependencies:
                if dep_id in assignments and sg_id in assignments:
                    if assignments[dep_id] == assignments[sg_id]:
                        # Same agent assigned to dependent tasks - potential conflict
                        conflicts.append(Conflict(
                            id=str(uuid.uuid4()),
                            agent_a=assignments[sg_id],
                            agent_b=assignments[dep_id],
                            description=f"Agent {assignments[sg_id]} assigned to both {sg_id} and its dependency {dep_id}",
                        ))
        
        self.conflicts = conflicts
        return conflicts
    
    def _resolve_conflicts(self, assignments: Dict[str, str],
                           conflicts: List[Conflict]) -> Dict[str, str]:
        """Resolve conflicts by reassigning tasks."""
        for conflict in conflicts:
            # Simple resolution: reassign the later task to a different agent
            sg_id = conflict.agent_a
            if sg_id in self.sub_goals:
                self.sub_goals[sg_id].assigned_agent = None
                del assignments[sg_id]
            
            conflict.description += " (resolved by unassigning)"
        
        return assignments
    
    def _execute_coordinated(self, assignments: Dict[str, str],
                             sub_goals: Dict[str, SubGoal]) -> Dict[str, Any]:
        """Execute assigned sub-goals."""
        results = {}
        
        for sg_id, agent_id in assignments.items():
            sg = sub_goals.get(sg_id)
            if not sg:
                continue
            
            # Simulate execution
            result = {
                "sub_goal_id": sg_id,
                "agent_id": agent_id,
                "success": True,
                "output": f"Completed: {sg.description}",
                "timestamp": time.time(),
            }
            
            sg.status = "completed"
            sg.result = result
            results[sg_id] = result
            
            # Update agent status
            if agent_id in self.agents:
                self.agents[agent_id].status = "idle"
                self.agents[agent_id].current_task = None
        
        return results
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "agents": len(self.agents),
            "sub_goals": len(self.sub_goals),
            "conflicts": len(self.conflicts),
        }
