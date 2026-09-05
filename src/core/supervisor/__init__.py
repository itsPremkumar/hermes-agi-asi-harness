"""Supervisor Core — State machine for autonomous agent orchestration.

Implements the AVO evolution cycle:
    OBSERVE → REASON → PLAN → ACT → EVALUATE → UPDATE → REPEAT

Uses Hermes native tools: delegate_task, web_search, web_extract, memory, cron, bot_mode.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class SupervisorState(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    RESEARCHING = "researching"
    DISPATCHING = "dispatching"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    EVOLVING = "evolving"
    CONSOLIDATING = "consolidating"
    STALLED = "stalled"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    RESEARCH = "research"
    CODING = "coding"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    WRITING = "writing"
    GENERAL = "general"


@dataclass
class Task:
    """A unit of work for the supervisor to execute."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: TaskType = TaskType.GENERAL
    title: str = ""
    description: str = ""
    goal_id: str = ""
    priority: int = 0
    status: str = "pending"
    result: str = ""
    feedback: str = ""
    score: float = 0.0
    attempts: int = 0
    max_attempts: int = 3
    subagent_id: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Goal:
    """A high-level goal decomposed into tasks."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    status: str = "pending"
    tasks: List[Task] = field(default_factory=list)
    score: float = 0.0
    iteration: int = 0
    max_iterations: int = 10
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Supervisor Core
# ---------------------------------------------------------------------------

class Supervisor:
    """Main supervisor implementing the AVO evolution cycle."""

    def __init__(
        self,
        data_dir: Path | None = None,
        max_iterations: int = 10,
        stall_threshold: int = 5,
    ):
        self._data_dir = data_dir or Path.home() / ".hermes" / "supervisor"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._state = SupervisorState.IDLE
        self._goals: Dict[str, Goal] = {}
        self._active_task: Task | None = None
        self._iteration = 0
        self._max_iterations = max_iterations
        self._stall_threshold = stall_threshold
        self._stall_count = 0
        self._last_score = 0.0

        # Callbacks for integration with Hermes tools
        self._dispatch_callback: Callable | None = None
        self._research_callback: Callable | None = None
        self._evaluate_callback: Callable | None = None

    # --- Properties ---

    @property
    def state(self) -> SupervisorState:
        return self._state

    @property
    def is_active(self) -> bool:
        return self._state not in (SupervisorState.IDLE, SupervisorState.COMPLETED, SupervisorState.FAILED)

    @property
    def active_goals(self) -> List[Goal]:
        return [g for g in self._goals.values() if g.status not in ("completed", "failed")]

    # --- Callback registration ---

    def on_dispatch(self, callback: Callable) -> None:
        """Register callback for task dispatch. Called as callback(task) -> result."""
        self._dispatch_callback = callback

    def on_research(self, callback: Callable) -> None:
        """Register callback for research. Called as callback(query) -> research_result."""
        self._research_callback = callback

    def on_evaluate(self, callback: Callable) -> None:
        """Register callback for evaluation. Called as callback(task, result) -> score."""
        self._evaluate_callback = callback

    # --- Goal management ---

    def add_goal(self, title: str, description: str, **metadata) -> Goal:
        """Add a new high-level goal."""
        goal = Goal(title=title, description=description, metadata=metadata)
        goal.tasks = self._plan(goal)
        self._goals[goal.id] = goal
        return goal

    def get_goal(self, goal_id: str) -> Goal | None:
        """Get a goal by ID."""
        return self._goals.get(goal_id)

    def list_goals(self) -> List[Goal]:
        """List all goals."""
        return list(self._goals.values())

    # --- Main evolution loop ---

    def run(self, goal_id: str) -> None:
        """Run the full evolution cycle for a goal."""
        goal = self._goals.get(goal_id)
        if not goal:
            return

        goal.status = "running"
        self._iteration = 0

        while self._iteration < self._max_iterations:
            self._iteration += 1
            goal.iteration = self._iteration

            # 1. PLAN: Decompose goal into tasks
            self._state = SupervisorState.PLANNING
            tasks = self._plan(goal)
            goal.tasks = tasks

            # 2. RESEARCH: Gather context
            self._state = SupervisorState.RESEARCHING
            research = self._research(goal)

            # 3. DISPATCH + EXECUTE: Run tasks
            self._state = SupervisorState.EXECUTING
            for task in tasks:
                self._active_task = task
                self._execute_task(task, goal, research)

            # 4. EVALUATE: Score the result
            self._state = SupervisorState.EVALUATING
            score = self._evaluate(goal)
            goal.score = score

            # 5. Check for completion
            if score >= 1.0:
                goal.status = "completed"
                goal.completed_at = time.time()
                self._state = SupervisorState.COMPLETED
                return

            # 6. If no real evaluator, mark completed after first iteration
            if not self._evaluate_callback and not self._dispatch_callback:
                goal.status = "completed"
                goal.completed_at = time.time()
                self._state = SupervisorState.COMPLETED
                return

            # 7. Check for stall
            if self._is_stalled(score):
                self._state = SupervisorState.STALLED
                self._handle_stall(goal)
                if self._stall_count >= self._stall_threshold:
                    goal.status = "failed"
                    self._state = SupervisorState.FAILED
                    return
            else:
                self._stall_count = 0

            # 7. EVOLVE: Generate variations
            self._state = SupervisorState.EVOLVING
            self._evolve(goal)

        # Max iterations reached
        goal.status = "completed" if goal.score > 0.5 else "failed"
        self._state = SupervisorState.COMPLETED if goal.status == "completed" else SupervisorState.FAILED

    # --- Planning ---

    def _plan(self, goal: Goal) -> List[Task]:
        """Decompose goal into executable tasks."""
        task = Task(
            type=self._classify_task(goal.description),
            title=goal.title,
            description=goal.description,
            goal_id=goal.id,
        )
        return [task]

    def _classify_task(self, description: str) -> TaskType:
        """Classify task type from description."""
        desc = description.lower()
        if any(w in desc for w in ["research", "search", "find", "analyze"]):
            return TaskType.RESEARCH
        elif any(w in desc for w in ["test", "verify", "benchmark", "evaluate"]):
            return TaskType.TESTING
        elif any(w in desc for w in ["code", "implement", "build", "fix", "develop"]):
            return TaskType.CODING
        elif any(w in desc for w in ["deploy", "release", "publish"]):
            return TaskType.DEPLOYMENT
        elif any(w in desc for w in ["document", "write", "report"]):
            return TaskType.WRITING
        return TaskType.GENERAL

    # --- Research ---

    def _research(self, goal: Goal) -> Dict[str, Any]:
        """Gather research context for the goal."""
        if self._research_callback:
            return self._research_callback(goal.title + " " + goal.description)
        return {"query": goal.title, "sources": [], "findings": []}

    # --- Task execution ---

    def _execute_task(self, task: Task, goal: Goal, research: Dict[str, Any]) -> None:
        """Execute a single task."""
        task.status = "running"
        task.attempts += 1

        if self._dispatch_callback:
            result = self._dispatch_callback(task, research)
            task.result = str(result)
            task.status = "completed"
            task.completed_at = time.time()
        else:
            task.status = "failed"
            task.feedback = "No dispatch callback registered"

    # --- Evaluation ---

    def _evaluate(self, goal: Goal) -> float:
        """Evaluate the goal's current state."""
        if self._evaluate_callback:
            return self._evaluate_callback(goal)

        if not goal.tasks:
            return 0.0
        return sum(t.score for t in goal.tasks) / len(goal.tasks)

    # --- Stall detection ---

    def _is_stalled(self, score: float) -> bool:
        """Detect if progress has stalled."""
        if abs(score - self._last_score) < 0.01:
            self._stall_count += 1
        else:
            self._stall_count = 0
        self._last_score = score
        return self._stall_count >= self._stall_threshold

    def _handle_stall(self, goal: Goal) -> None:
        """Handle a stall by changing strategy."""
        pass

    def _evolve(self, goal: Goal) -> None:
        """Evolve the approach based on feedback."""
        pass

    # --- State persistence ---

    def save_state(self) -> None:
        """Persist supervisor state to disk."""
        state = {
            "state": self._state.value,
            "iteration": self._iteration,
            "goals": {
                gid: {
                    "id": g.id,
                    "title": g.title,
                    "description": g.description,
                    "status": g.status,
                    "score": g.score,
                    "iteration": g.iteration,
                    "tasks": [
                        {
                            "id": t.id,
                            "type": t.type.value,
                            "title": t.title,
                            "status": t.status,
                            "result": t.result,
                            "score": t.score,
                        }
                        for t in g.tasks
                    ],
                }
                for gid, g in self._goals.items()
            },
        }
        path = self._data_dir / "supervisor_state.json"
        path.write_text(json.dumps(state, indent=2))

    def load_state(self) -> None:
        """Load supervisor state from disk."""
        path = self._data_dir / "supervisor_state.json"
        if not path.exists():
            return
        state = json.loads(path.read_text())
        self._state = SupervisorState(state.get("state", "idle"))
        self._iteration = state.get("iteration", 0)
        for gid, gdata in state.get("goals", {}).items():
            goal = Goal(
                id=gdata["id"],
                title=gdata["title"],
                description=gdata["description"],
                status=gdata["status"],
                score=gdata.get("score", 0),
                iteration=gdata.get("iteration", 0),
            )
            for tdata in gdata.get("tasks", []):
                task = Task(
                    id=tdata["id"],
                    type=TaskType(tdata.get("type", "general")),
                    title=tdata.get("title", ""),
                    status=tdata.get("status", "pending"),
                    result=tdata.get("result", ""),
                    score=tdata.get("score", 0),
                )
                goal.tasks.append(task)
            self._goals[gid] = goal

    # --- Status ---

    def get_status(self) -> Dict[str, Any]:
        """Get full supervisor status."""
        return {
            "state": self._state.value,
            "iteration": self._iteration,
            "total_goals": len(self._goals),
            "active_goals": len(self.active_goals),
            "completed_goals": sum(1 for g in self._goals.values() if g.status == "completed"),
            "failed_goals": sum(1 for g in self._goals.values() if g.status == "failed"),
            "goals": {
                gid: {
                    "title": g.title,
                    "status": g.status,
                    "score": g.score,
                    "iteration": g.iteration,
                }
                for gid, g in self._goals.items()
            },
        }
