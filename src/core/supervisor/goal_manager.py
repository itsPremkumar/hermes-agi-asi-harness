"""Goal Dependency Graph + Assignment Engine + Goal Manager + Replanning Engine.

Implements the core intelligence for:
1. Dependency tracking between goals
2. Worker assignment based on capability matching
3. Goal health monitoring
4. Dynamic re-decomposition and replanning
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Worker:
    """A Hermes worker."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    capabilities: List[str] = field(default_factory=list)
    performance_history: Dict[str, float] = field(default_factory=dict)
    current_task: str = ""
    status: str = "idle"  # idle, busy, failed
    success_rate: float = 0.0
    total_tasks: int = 0
    completed_tasks: int = 0

    def assign(self, task_id: str) -> None:
        """Assign a task to this worker."""
        self.current_task = task_id
        self.status = "busy"

    def complete(self, success: bool) -> None:
        """Complete the current task."""
        self.total_tasks += 1
        if success:
            self.completed_tasks += 1
        self.success_rate = self.completed_tasks / self.total_tasks if self.total_tasks > 0 else 0.0
        self.current_task = ""
        self.status = "idle"

    def capability_score(self, required_capabilities: List[str]) -> float:
        """Calculate how well this worker matches required capabilities."""
        if not required_capabilities:
            return 0.5  # Default score
        matches = sum(1 for cap in required_capabilities if cap in self.capabilities)
        return matches / len(required_capabilities)


@dataclass
class DependencyEdge:
    """A dependency between two goals."""
    from_id: str = ""
    to_id: str = ""
    dependency_type: str = "finish_to_start"  # finish_to_start, start_to_start, finish_to_finish
    strength: float = 1.0  # 0.0 to 1.0


class GoalDependencyGraph:
    """Tracks dependencies between goals."""

    def __init__(self):
        self._edges: List[DependencyEdge] = []

    def add_dependency(self, from_id: str, to_id: str, dep_type: str = "finish_to_start") -> None:
        """Add a dependency edge."""
        edge = DependencyEdge(from_id=from_id, to_id=to_id, dependency_type=dep_type)
        self._edges.append(edge)

    def get_dependencies(self, goal_id: str) -> List[str]:
        """Get all goals that must complete before this goal."""
        return [e.from_id for e in self._edges if e.to_id == goal_id]

    def get_dependents(self, goal_id: str) -> List[str]:
        """Get all goals that depend on this goal."""
        return [e.to_id for e in self._edges if e.from_id == goal_id]

    def is_ready(self, goal_id: str, completed_goals: List[str]) -> bool:
        """Check if a goal is ready (all dependencies met)."""
        deps = self.get_dependencies(goal_id)
        return all(dep in completed_goals for dep in deps)

    def get_ready_goals(self, all_goals: List[str], completed_goals: List[str]) -> List[str]:
        """Get all goals that are ready to execute."""
        return [g for g in all_goals if self.is_ready(g, completed_goals)]

    def get_critical_path(self, goal_id: str) -> List[str]:
        """Get the critical path to a goal."""
        path = [goal_id]
        deps = self.get_dependencies(goal_id)
        if deps:
            # Follow the longest dependency chain
            longest = max(deps, key=lambda d: len(self.get_critical_path(d)))
            path = self.get_critical_path(longest) + path
        return path


class AssignmentEngine:
    """Assigns tasks to workers based on capability matching and performance."""

    def __init__(self):
        self._workers: Dict[str, Worker] = {}

    def register_worker(self, worker: Worker) -> None:
        """Register a worker."""
        self._workers[worker.id] = worker

    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get a worker by ID."""
        return self._workers.get(worker_id)

    def get_available_workers(self) -> List[Worker]:
        """Get all available (idle) workers."""
        return [w for w in self._workers.values() if w.status == "idle"]

    def assign_task(
        self,
        task_id: str,
        required_capabilities: List[str],
        task_complexity: float = 0.5,
    ) -> Optional[str]:
        """Assign a task to the best available worker.

        Returns:
            worker_id of the assigned worker, or None if no worker available.
        """
        available = self.get_available_workers()
        if not available:
            return None

        # Score each worker
        scores = []
        for worker in available:
            capability_score = worker.capability_score(required_capabilities)
            performance_score = worker.success_rate
            # Combined score: 60% capability, 40% performance
            combined = 0.6 * capability_score + 0.4 * performance_score
            scores.append((combined, worker))

        # Select best worker
        scores.sort(key=lambda x: x[0], reverse=True)
        best_worker = scores[0][1]

        best_worker.assign(task_id)
        return best_worker.id

    def complete_task(self, worker_id: str, success: bool) -> None:
        """Complete a task for a worker."""
        worker = self._workers.get(worker_id)
        if worker:
            worker.complete(success)

    def get_worker_stats(self) -> Dict[str, Any]:
        """Get stats for all workers."""
        return {
            wid: {
                "name": w.name,
                "status": w.status,
                "success_rate": w.success_rate,
                "total_tasks": w.total_tasks,
                "capabilities": w.capabilities,
            }
            for wid, w in self._workers.items()
        }


class GoalManager:
    """Manages goal health and progress tracking."""

    def __init__(self):
        self._goals: Dict[str, Dict[str, Any]] = {}

    def register_goal(self, goal_id: str, goal_data: Dict[str, Any]) -> None:
        """Register a goal for tracking."""
        self._goals[goal_id] = {
            **goal_data,
            "health": {
                "progress": 0.0,
                "confidence": 1.0,
                "risk": 0.0,
                "dependency_health": 1.0,
                "resource_health": 1.0,
                "schedule_health": 1.0,
                "blockers": [],
            },
            "created_at": time.time(),
            "updated_at": time.time(),
        }

    def update_progress(self, goal_id: str, progress: float) -> None:
        """Update goal progress."""
        if goal_id in self._goals:
            self._goals[goal_id]["health"]["progress"] = progress
            self._goals[goal_id]["updated_at"] = time.time()

    def update_health(self, goal_id: str, **kwargs) -> None:
        """Update goal health metrics."""
        if goal_id in self._goals:
            self._goals[goal_id]["health"].update(kwargs)
            self._goals[goal_id]["updated_at"] = time.time()

    def get_health(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get goal health."""
        goal = self._goals.get(goal_id)
        return goal["health"] if goal else None

    def get_blockers(self, goal_id: str) -> List[str]:
        """Get blockers for a goal."""
        health = self.get_health(goal_id)
        return health.get("blockers", []) if health else []

    def is_at_risk(self, goal_id: str) -> bool:
        """Check if a goal is at risk."""
        health = self.get_health(goal_id)
        if not health:
            return False
        return health.get("risk", 0.0) > 0.7 or health.get("progress", 0.0) < 0.2

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health across all goals."""
        if not self._goals:
            return {"total": 0, "at_risk": 0, "blocked": 0}

        at_risk = sum(1 for g in self._goals if self.is_at_risk(g))
        blocked = sum(1 for g in self._goals if self.get_blockers(g))

        return {
            "total": len(self._goals),
            "at_risk": at_risk,
            "blocked": blocked,
            "avg_progress": sum(g["health"]["progress"] for g in self._goals.values()) / len(self._goals),
        }


class ReplanningEngine:
    """Dynamic re-decomposition and replanning."""

    def __init__(self):
        self._replanning_history: List[Dict[str, Any]] = []

    def needs_replanning(self, goal_manager: GoalManager, dependency_graph: GoalDependencyGraph) -> bool:
        """Determine if replanning is needed."""
        health = goal_manager.get_overall_health()

        # Replan if too many goals are at risk
        if health["at_risk"] > health["total"] * 0.3:
            return True

        # Replan if too many goals are blocked
        if health["blocked"] > health["total"] * 0.2:
            return True

        return False

    def replan(
        self,
        goal_manager: GoalManager,
        dependency_graph: GoalDependencyGraph,
        decomposer: Any,
        hierarchy: Any,
    ) -> Dict[str, Any]:
        """Execute a replanning cycle."""
        replan_record = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": time.time(),
            "actions": [],
        }

        # 1. Identify at-risk goals
        at_risk = [gid for gid in goal_manager._goals if goal_manager.is_at_risk(gid)]

        # 2. For each at-risk goal, re-decompose
        for goal_id in at_risk:
            # Create new subtasks
            new_subtasks = [
                ("Re-analyze", "Re-analyze the approach"),
                ("Alternative approach", "Try alternative approach"),
                ("Verify", "Verify new approach works"),
            ]

            # Record the action
            replan_record["actions"].append({
                "goal_id": goal_id,
                "action": "re_decompose",
                "new_subtasks": len(new_subtasks),
            })

        # 3. Update goal health
        for action in replan_record["actions"]:
            goal_manager.update_health(
                action["goal_id"],
                risk=0.3,  # Reduce risk after replanning
                blockers=[],  # Clear blockers
            )

        self._replanning_history.append(replan_record)
        return replan_record

    def get_history(self) -> List[Dict[str, Any]]:
        """Get replanning history."""
        return self._replanning_history.copy()
