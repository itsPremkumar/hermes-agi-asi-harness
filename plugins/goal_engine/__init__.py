"""
goal_engine.py — Long-Horizon Goal Decomposition & DAG Orchestration Engine

Builds on the reference's GoalEngine to provide:
- Automatic goal decomposition into dependency DAGs
- Topological execution with parallel task support
- Retry with exponential backoff
- Progress tracking and completion detection
- Integration with the supervisor for 24/7 operation
"""

import time
import uuid
import asyncio
import logging
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


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
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


@dataclass
class Goal:
    goal_id: str
    title: str
    description: str
    subtasks: Dict[str, SubTask] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GoalEngine:
    """
    Long-horizon goal decomposition and DAG orchestration.
    Supports automatic decomposition, parallel execution, and retry logic.
    """

    def __init__(self):
        self.active_goals: Dict[str, Goal] = {}
        self.completed_goals: Dict[str, Goal] = {}
        self._execution_traces: Dict[str, List[Dict[str, Any]]] = {}

    def create_goal(self, title: str, description: str, goal_id: Optional[str] = None) -> Goal:
        """Creates a new goal with optional custom ID."""
        gid = goal_id or f"goal_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        goal = Goal(goal_id=gid, title=title, description=description)
        self.active_goals[gid] = goal
        self._execution_traces[gid] = []
        logger.info("Created goal: %s — %s", gid, title)
        return goal

    def add_subtask(
        self,
        goal: Goal,
        task_id: str,
        title: str,
        description: str,
        role: str = "general_specialist",
        dependencies: Optional[List[str]] = None,
    ) -> SubTask:
        """Adds a subtask to a goal with dependency tracking."""
        deps = dependencies or []
        initial_status = TaskStatus.READY if len(deps) == 0 else TaskStatus.BLOCKED
        subtask = SubTask(
            id=task_id,
            title=title,
            description=description,
            role=role,
            dependencies=deps,
            status=initial_status,
        )
        goal.subtasks[task_id] = subtask
        return subtask

    def auto_decompose(self, goal: Goal, strategy: str = "standard") -> List[SubTask]:
        """
        Automatically decomposes a goal into subtasks.
        
        Strategies:
        - "standard": 4-stage pipeline (research → plan → implement → verify)
        - "research": Research-focused (discover → analyze → synthesize → report)
        - "engineering": Engineering-focused (design → code → test → deploy)
        - "minimal": 2-stage (execute → verify)
        """
        if strategy == "research":
            return self._decompose_research(goal)
        elif strategy == "engineering":
            return self._decompose_engineering(goal)
        elif strategy == "minimal":
            return self._decompose_minimal(goal)
        else:
            return self._decompose_standard(goal)

    def _decompose_standard(self, goal: Goal) -> List[SubTask]:
        """Standard 4-stage pipeline."""
        t1 = self.add_subtask(
            goal=goal,
            task_id="task_1_research",
            title="Requirements & Research",
            description=f"Analyze requirements and constraints for: {goal.description}",
            role="researcher",
        )
        t2 = self.add_subtask(
            goal=goal,
            task_id="task_2_architecture",
            title="System Architecture & Plan",
            description="Formulate technical design and invariant contracts",
            role="planner",
            dependencies=["task_1_research"],
        )
        t3 = self.add_subtask(
            goal=goal,
            task_id="task_3_implementation",
            title="Core Implementation",
            description="Implement code and algorithms meeting the specification",
            role="coder",
            dependencies=["task_2_architecture"],
        )
        t4 = self.add_subtask(
            goal=goal,
            task_id="task_4_verification",
            title="Verification & Evaluation",
            description="Execute automated tests, AST check, and proof verification",
            role="evaluator",
            dependencies=["task_3_implementation"],
        )
        return [t1, t2, t3, t4]

    def _decompose_research(self, goal: Goal) -> List[SubTask]:
        """Research-focused decomposition."""
        t1 = self.add_subtask(
            goal=goal,
            task_id="task_1_discover",
            title="Discovery & Search",
            description=f"Search for relevant information about: {goal.description}",
            role="researcher",
        )
        t2 = self.add_subtask(
            goal=goal,
            task_id="task_2_analyze",
            title="Analysis & Synthesis",
            description="Analyze findings and identify patterns",
            role="analyst",
            dependencies=["task_1_discover"],
        )
        t3 = self.add_subtask(
            goal=goal,
            task_id="task_3_synthesize",
            title="Synthesis & Report",
            description="Synthesize findings into a coherent report",
            role="writer",
            dependencies=["task_2_analyze"],
        )
        return [t1, t2, t3]

    def _decompose_engineering(self, goal: Goal) -> List[SubTask]:
        """Engineering-focused decomposition."""
        t1 = self.add_subtask(
            goal=goal,
            task_id="task_1_design",
            title="System Design",
            description=f"Design system architecture for: {goal.description}",
            role="architect",
        )
        t2 = self.add_subtask(
            goal=goal,
            task_id="task_2_implement",
            title="Implementation",
            description="Implement the designed system",
            role="coder",
            dependencies=["task_1_design"],
        )
        t3 = self.add_subtask(
            goal=goal,
            task_id="task_3_test",
            title="Testing & QA",
            description="Write and run tests to verify correctness",
            role="tester",
            dependencies=["task_2_implement"],
        )
        t4 = self.add_subtask(
            goal=goal,
            task_id="task_4_deploy",
            title="Deployment",
            description="Package and deploy the solution",
            role="deployer",
            dependencies=["task_3_test"],
        )
        return [t1, t2, t3, t4]

    def _decompose_minimal(self, goal: Goal) -> List[SubTask]:
        """Minimal 2-stage decomposition."""
        t1 = self.add_subtask(
            goal=goal,
            task_id="task_1_execute",
            title="Execute",
            description=goal.description,
            role="executor",
        )
        t2 = self.add_subtask(
            goal=goal,
            task_id="task_2_verify",
            title="Verify",
            description="Verify the execution result",
            role="verifier",
            dependencies=["task_1_execute"],
        )
        return [t1, t2]

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
            task.completed_at = time.time()

            # Update goal completion
            if self.is_goal_complete(goal):
                goal.completed_at = time.time()
                self.completed_goals[goal.goal_id] = goal
                if goal.goal_id in self.active_goals:
                    del self.active_goals[goal.goal_id]
                logger.info("Goal %s completed!", goal.goal_id)

    def fail_task(self, goal: Goal, task_id: str, error: str) -> bool:
        """
        Handles task failure. Returns True if task will be retried.
        """
        if task_id in goal.subtasks:
            task = goal.subtasks[task_id]
            task.error = error
            task.retries += 1
            if task.retries < task.max_retries:
                task.status = TaskStatus.READY
                logger.warning("Task %s failed (retry %d/%d): %s", task_id, task.retries, task.max_retries, error)
                return True
            else:
                task.status = TaskStatus.FAILED
                logger.error("Task %s permanently failed: %s", task_id, error)
                return False
        return False

    def is_goal_complete(self, goal: Goal) -> bool:
        """Checks if all subtasks are completed."""
        if not goal.subtasks:
            return False
        return all(t.status == TaskStatus.COMPLETED for t in goal.subtasks.values())

    def get_progress(self, goal: Goal) -> Dict[str, Any]:
        """Returns progress statistics for a goal."""
        total = len(goal.subtasks)
        completed = sum(1 for t in goal.subtasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in goal.subtasks.values() if t.status == TaskStatus.FAILED)
        in_progress = sum(1 for t in goal.subtasks.values() if t.status == TaskStatus.IN_PROGRESS)
        return {
            "goal_id": goal.goal_id,
            "title": goal.title,
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "percent": (completed / total * 100) if total > 0 else 0,
            "is_complete": self.is_goal_complete(goal),
        }

    def get_execution_trace(self, goal_id: str) -> List[Dict[str, Any]]:
        """Returns the execution trace for a goal."""
        return self._execution_traces.get(goal_id, [])


async def create(kernel=None) -> GoalEngine:
    """Factory function for kernel integration."""
    engine = GoalEngine()
    return engine
