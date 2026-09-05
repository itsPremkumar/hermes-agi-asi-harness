"""
HERMES INTELLIGENCE OS — MISSION INTERMEDIATE REPRESENTATION & DYNAMIC GOAL GRAPH
================================================================================
The foundational data structures of the Cognitive Planning OS (v9):
- MissionIR: Durable, self-contained mission specification compiled before execution.
- GoalLifecycle: Rigorous state transitions (CREATED -> UNDERSTOOD -> VALIDATED -> PLANNED -> ACTIVE -> BLOCKED -> REPLANNING -> VERIFYING -> COMPLETED/FAILED/ABANDONED).
- GoalNode & GoalGraph: Dynamic DAG with dependency declaration, cycle detection, critical path extraction, and execution wave computation.
- GoalMemory: Persistent goal registry distinguishing active goals from archived history.
- GoalInvariant: Kernel-level non-compactable rules preserved across all turns.
"""

from __future__ import annotations

import collections
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("hermes.os.mission_ir")


class GoalLifecycle(str, enum.Enum):
    """Rigorous state lifecycle for goals and subgoals."""
    CREATED = "created"
    UNDERSTOOD = "understood"
    VALIDATED = "validated"
    PLANNED = "planned"
    ACTIVE = "active"
    BLOCKED = "blocked"
    REPLANNING = "replanning"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


@dataclass
class GoalInvariant:
    """Kernel-level rule that must never be violated or lost during context compaction."""
    name: str
    description: str
    severity: str = "CRITICAL"            # "CRITICAL", "HIGH", "MEDIUM"
    rule_expression: str = ""
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "rule_expression": self.rule_expression,
            "is_active": self.is_active,
        }


@dataclass
class GoalNode:
    """A node in the dynamic goal dependency DAG."""
    goal_id: str
    title: str
    description: str
    parent_id: Optional[str] = None
    subgoal_ids: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)      # Must complete before this goal starts
    blocks: List[str] = field(default_factory=list)          # Goals waiting on this goal
    enables: List[str] = field(default_factory=list)         # Capabilities or goals unlocked by this
    conflicts_with: List[str] = field(default_factory=list)  # Cannot run concurrently with these
    derived_from: Optional[str] = None
    owner_agent: Optional[str] = None
    status: GoalLifecycle = GoalLifecycle.CREATED
    evidence_refs: List[str] = field(default_factory=list)
    progress: float = 0.0                                    # 0.0 to 1.0
    budget_tokens: int = 5000
    deadline_seconds: float = 300.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def transition_to(self, new_status: GoalLifecycle, reason: str = "") -> None:
        logger.info(f"Goal {self.goal_id} ({self.title}) transition: {self.status.value} -> {new_status.value}. Reason: {reason}")
        self.status = new_status
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "parent_id": self.parent_id,
            "subgoal_ids": list(self.subgoal_ids),
            "depends_on": list(self.depends_on),
            "blocks": list(self.blocks),
            "enables": list(self.enables),
            "conflicts_with": list(self.conflicts_with),
            "owner_agent": self.owner_agent,
            "status": self.status.value,
            "progress": round(self.progress, 3),
            "evidence_refs": list(self.evidence_refs),
            "budget_tokens": self.budget_tokens,
            "deadline_seconds": self.deadline_seconds,
        }


class GoalGraph:
    """
    Dynamic Directed Acyclic Graph (DAG) of goals, subgoals, and atomic tasks.
    Supports topological sorting, cycle detection, critical path extraction,
    and parallel execution wave segmentation.
    """

    def __init__(self):
        self._nodes: Dict[str, GoalNode] = {}

    def add_goal(self, goal: GoalNode) -> None:
        self._nodes[goal.goal_id] = goal
        # If this goal depends on others, update their 'blocks' list
        for dep in goal.depends_on:
            if dep in self._nodes and goal.goal_id not in self._nodes[dep].blocks:
                self._nodes[dep].blocks.append(goal.goal_id)

    def get_goal(self, goal_id: str) -> Optional[GoalNode]:
        return self._nodes.get(goal_id)

    def list_goals(self) -> List[GoalNode]:
        return list(self._nodes.values())

    def detect_cycles(self) -> bool:
        """Detect circular dependencies using Tarjan / DFS."""
        visited: Dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=visited

        def dfs(node_id: str) -> bool:
            visited[node_id] = 1
            node = self._nodes.get(node_id)
            if node:
                for dep in node.depends_on:
                    if dep not in self._nodes:
                        continue
                    state = visited.get(dep, 0)
                    if state == 1:
                        return True  # Back edge -> Cycle detected
                    if state == 0 and dfs(dep):
                        return True
            visited[node_id] = 2
            return False

        for n_id in self._nodes:
            if visited.get(n_id, 0) == 0:
                if dfs(n_id):
                    return True
        return False

    def topological_sort(self) -> List[str]:
        """Return valid linear execution order respecting dependencies."""
        if self.detect_cycles():
            raise ValueError("Cycle detected in GoalGraph; cannot topologically sort")

        in_degree: Dict[str, int] = {gid: 0 for gid in self._nodes}
        for node in self._nodes.values():
            for dep in node.depends_on:
                if dep in in_degree:
                    in_degree[node.goal_id] += 1

        queue = collections.deque([gid for gid, deg in in_degree.items() if deg == 0])
        order: List[str] = []

        while queue:
            curr_id = queue.popleft()
            order.append(curr_id)
            curr_node = self._nodes.get(curr_id)
            if curr_node:
                for blocked_id in curr_node.blocks:
                    if blocked_id in in_degree:
                        in_degree[blocked_id] -= 1
                        if in_degree[blocked_id] == 0:
                            queue.append(blocked_id)

        return order

    def compute_execution_waves(self) -> List[List[str]]:
        """
        Group tasks into sequential execution waves where all tasks within
        a single wave can be safely executed in parallel.
        """
        if self.detect_cycles():
            raise ValueError("Cycle detected in GoalGraph; cannot compute waves")

        waves: List[List[str]] = []
        completed: Set[str] = set()
        remaining = set(self._nodes.keys())

        while remaining:
            # Find all nodes whose dependencies are already fully completed
            current_wave = [
                gid for gid in remaining
                if all(dep in completed for dep in self._nodes[gid].depends_on)
            ]
            if not current_wave:
                # Deadlock or circular reference
                break

            waves.append(current_wave)
            for gid in current_wave:
                completed.add(gid)
                remaining.remove(gid)

        return waves

    # ------------------------------------------------------------------
    # Dynamic mutation API (workers can rewrite the graph at runtime)
    # ------------------------------------------------------------------
    def insert_subgoal(self, parent_id: str, title: str, description: str = "",
                       depends_on: Optional[List[str]] = None,
                       evidence: str = "", owner_agent: Optional[str] = None) -> GoalNode:
        """Discover-new-requirement → create subgoal → insert → execute."""
        import time as _t
        import uuid as _uuid
        gid = f"g-{_uuid.uuid4().hex[:8]}"
        node = GoalNode(goal_id=gid, title=title, description=description or title,
                        parent_id=parent_id, depends_on=list(depends_on or []),
                        owner_agent=owner_agent, status=GoalLifecycle.PLANNED)
        if evidence:
            node.evidence_refs.append(evidence)
        node.updated_at = _t.time()
        parent = self._nodes.get(parent_id)
        if parent is not None and gid not in parent.subgoal_ids:
            parent.subgoal_ids.append(gid)
        self.add_goal(node)
        if self.detect_cycles():
            # rollback on cycle
            self._nodes.pop(gid, None)
            if parent is not None and gid in parent.subgoal_ids:
                parent.subgoal_ids.remove(gid)
            raise ValueError(f"insert_subgoal would create cycle (parent={parent_id})")
        return node

    def move_dependency(self, goal_id: str, new_depends_on: List[str]) -> None:
        node = self._nodes.get(goal_id)
        if not node:
            raise KeyError(f"Unknown goal {goal_id}")
        old_deps = list(node.depends_on)
        old_blocks: Dict[str, List[str]] = {gid: list(n.blocks) for gid, n in self._nodes.items()}
        node.depends_on = list(new_depends_on)
        # rebuild blocks
        for n in self._nodes.values():
            n.blocks = [b for b in n.blocks if b != goal_id]
        for dep in node.depends_on:
            if dep in self._nodes and goal_id not in self._nodes[dep].blocks:
                self._nodes[dep].blocks.append(goal_id)
        if self.detect_cycles():
            node.depends_on = old_deps
            for gid, bl in old_blocks.items():
                if gid in self._nodes:
                    self._nodes[gid].blocks = bl
            raise ValueError("move_dependency would create cycle")

    def mark_progress(self, goal_id: str, progress: float, evidence: str = "",
                      status: Optional[GoalLifecycle] = None) -> None:
        import time as _t
        node = self._nodes.get(goal_id)
        if not node:
            raise KeyError(f"Unknown goal {goal_id}")
        node.progress = max(0.0, min(1.0, float(progress)))
        if evidence and evidence not in node.evidence_refs:
            node.evidence_refs.append(evidence)
        if status is not None:
            node.transition_to(status, "mark_progress")
        elif node.progress >= 1.0 and node.status not in (GoalLifecycle.COMPLETED, GoalLifecycle.FAILED):
            node.transition_to(GoalLifecycle.VERIFYING, "progress=1.0 awaiting verification")
        node.updated_at = _t.time()

    def replan_waves(self) -> List[List[str]]:
        """Recompute parallel waves after mutation. Raises on cycle/deadlock."""
        return self.compute_execution_waves()

    def blocked_by(self, goal_id: str) -> List[str]:
        node = self._nodes.get(goal_id)
        return list(node.depends_on) if node else []

    def extract_critical_path(self) -> List[str]:
        """Identify the longest dependency path (critical path) determining total project duration."""
        topo = self.topological_sort()
        dist: Dict[str, float] = {gid: 0.0 for gid in self._nodes}
        pred: Dict[str, Optional[str]] = {gid: None for gid in self._nodes}

        for gid in topo:
            node = self._nodes[gid]
            for blk in node.blocks:
                if blk in dist and dist[gid] + node.deadline_seconds > dist[blk]:
                    dist[blk] = dist[gid] + node.deadline_seconds
                    pred[blk] = gid

        # Find node with maximum distance
        if not dist:
            return []
        end_node = max(dist, key=lambda k: dist[k])
        path = []
        curr: Optional[str] = end_node
        while curr:
            path.append(curr)
            curr = pred.get(curr)
        path.reverse()
        return path


# =====================================================================
# Goal Memory
# =====================================================================

class GoalMemory:
    """
    Dedicated memory subsystem for goals.
    Maintains past, active, paused, failed, completed, and recurring goals.
    Strictly distinguishes 'goal exists' from 'goal is currently active'
    to prevent accidental resurrecting of stale objectives.
    """

    def __init__(self):
        self._active_goals: Dict[str, GoalNode] = {}
        self._archived_goals: Dict[str, GoalNode] = {}
        self._recurring_templates: Dict[str, GoalNode] = {}

    def register_goal(self, goal: GoalNode, is_active: bool = True) -> None:
        if is_active:
            self._active_goals[goal.goal_id] = goal
        else:
            self._archived_goals[goal.goal_id] = goal

    def get_active_goals(self) -> List[GoalNode]:
        return list(self._active_goals.values())

    def archive_goal(self, goal_id: str, final_status: GoalLifecycle) -> bool:
        if goal_id in self._active_goals:
            goal = self._active_goals.pop(goal_id)
            goal.status = final_status
            self._archived_goals[goal_id] = goal
            logger.info(f"Archived goal {goal_id} with status {final_status.value}")
            return True
        return False

    def search_similar_goals(self, query: str) -> List[GoalNode]:
        """Search previous goals for transferrable knowledge."""
        q_tokens = set(query.lower().split())
        scored = []
        for g in list(self._archived_goals.values()) + list(self._active_goals.values()):
            g_tokens = set(f"{g.title} {g.description}".lower().split())
            overlap = len(q_tokens.intersection(g_tokens))
            if overlap > 0:
                scored.append((overlap, g))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [g for _, g in scored[:5]]


# =====================================================================
# Mission Intermediate Representation (MissionIR)
# =====================================================================

@dataclass
class MissionIR:
    """
    The formal, durable Mission Intermediate Representation (Mission IR).
    Compiled before any execution occurs.
    """
    mission_id: str
    original_request: str
    normalized_intent: str
    objective: str
    desired_state: str
    constraints: List[str] = field(default_factory=list)
    invariants: List[GoalInvariant] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    risks: List[Dict[str, Any]] = field(default_factory=list)
    authority_scope: List[str] = field(default_factory=lambda: ["read", "write:workspace"])
    resource_limits: Dict[str, Any] = field(default_factory=lambda: {
        "max_tokens": 100000,
        "max_time_seconds": 600,
        "max_subagents": 8,
    })
    required_capabilities: List[str] = field(default_factory=list)
    candidate_strategies: List[Dict[str, Any]] = field(default_factory=list)
    selected_strategy_id: Optional[str] = None
    agent_topology: str = "planner_executor"
    tool_requirements: List[str] = field(default_factory=list)
    skill_requirements: List[str] = field(default_factory=list)
    plugin_requirements: List[str] = field(default_factory=list)
    command_requirements: List[str] = field(default_factory=list)
    verification_requirements: List[Dict[str, Any]] = field(default_factory=list)
    termination_conditions: List[str] = field(default_factory=list)
    goal_graph: GoalGraph = field(default_factory=GoalGraph)
    status: str = "compiled"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "original_request": self.original_request,
            "normalized_intent": self.normalized_intent,
            "objective": self.objective,
            "desired_state": self.desired_state,
            "constraints": self.constraints,
            "invariants": [inv.to_dict() for inv in self.invariants],
            "unknowns": self.unknowns,
            "assumptions": self.assumptions,
            "risks": self.risks,
            "required_capabilities": self.required_capabilities,
            "selected_strategy": self.selected_strategy_id,
            "agent_topology": self.agent_topology,
            "tools": self.tool_requirements,
            "skills": self.skill_requirements,
            "plugins": self.plugin_requirements,
            "commands": self.command_requirements,
            "termination_conditions": self.termination_conditions,
            "goals_count": len(self.goal_graph.list_goals()),
            "status": self.status,
        }
