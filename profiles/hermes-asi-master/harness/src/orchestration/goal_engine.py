#!/usr/bin/env python3
"""
goal_engine.py — Long-Horizon Goal Decomposition & DAG Orchestration Engine
Decomposes complex objectives into dependency DAGs and tracks topological execution.
"""

import time
from enum import Enum
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field

class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class SubTask:
    id: str
    title: str
    description: str
    role: str = "general_specialist"
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3

@dataclass
class Goal:
    goal_id: str
    title: str
    description: str
    subtasks: Dict[str, SubTask] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

class GoalEngine:
    def __init__(self):
        self.active_goals: Dict[str, Goal] = {}

    def create_goal(self, title: str, description: str) -> Goal:
        goal_id = f"goal_{int(time.time() * 1000)}"
        goal = Goal(goal_id=goal_id, title=title, description=description)
        self.active_goals[goal_id] = goal
        return goal

    def add_subtask(
        self,
        goal: Goal,
        task_id: str,
        title: str,
        description: str,
        role: str = "general_specialist",
        dependencies: Optional[List[str]] = None
    ) -> SubTask:
        deps = dependencies or []
        initial_status = TaskStatus.READY if len(deps) == 0 else TaskStatus.BLOCKED
        subtask = SubTask(
            id=task_id,
            title=title,
            description=description,
            role=role,
            dependencies=deps,
            status=initial_status
        )
        goal.subtasks[task_id] = subtask
        return subtask

    def auto_decompose(self, goal: Goal) -> List[SubTask]:
        """Automatically creates standard 4-stage pipeline for general engineering goals."""
        t1 = self.add_subtask(
            goal=goal,
            task_id="task_1_research",
            title="Requirements & Research",
            description=f"Analyze requirements and constraints for: {goal.description}",
            role="researcher"
        )
        t2 = self.add_subtask(
            goal=goal,
            task_id="task_2_architecture",
            title="System Architecture & Plan",
            description="Formulate technical design and invariant contracts",
            role="planner",
            dependencies=["task_1_research"]
        )
        t3 = self.add_subtask(
            goal=goal,
            task_id="task_3_implementation",
            title="Core Implementation",
            description="Implement code and algorithms meeting the specification",
            role="coder",
            dependencies=["task_2_architecture"]
        )
        t4 = self.add_subtask(
            goal=goal,
            task_id="task_4_verification",
            title="Verification & Evaluation",
            description="Execute automated tests, AST check, and proof verification",
            role="evaluator",
            dependencies=["task_3_implementation"]
        )
        return [t1, t2, t3, t4]

    def get_ready_tasks(self, goal: Goal) -> List[SubTask]:
        """Returns all subtasks whose dependencies have successfully completed."""
        ready = []
        for task in goal.subtasks.values():
            if task.status in (TaskStatus.PENDING, TaskStatus.BLOCKED):
                deps_met = all(
                    goal.subtasks.get(dep_id) and goal.subtasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                if deps_met:
                    task.status = TaskStatus.READY
                    ready.append(task)
            elif task.status == TaskStatus.READY:
                ready.append(task)
        return ready

    def complete_task(self, goal: Goal, task_id: str, result: Any = None):
        """Marks a task completed and unlocks downstream dependencies."""
        if task_id in goal.subtasks:
            task = goal.subtasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.result = result

            # Update goal completion
            if self.is_goal_complete(goal):
                goal.completed_at = time.time()

    def fail_task(self, goal: Goal, task_id: str, error: str) -> bool:
        """Handles task failure, retries if within budget, otherwise marks FAILED."""
        if task_id in goal.subtasks:
            task = goal.subtasks[task_id]
            task.error = error
            task.retries += 1
            if task.retries < task.max_retries:
                task.status = TaskStatus.READY
                return True  # Will retry
            else:
                task.status = TaskStatus.FAILED
                return False
        return False

    def is_goal_complete(self, goal: Goal) -> bool:
        if not goal.subtasks:
            return False
        return all(t.status == TaskStatus.COMPLETED for t in goal.subtasks.values())
