"""Hermes Supervisor Harness — Meta-orchestrator for autonomous agent swarms.

Instead of rebuilding tools Hermes already has (git, GitHub, search, code editing,
subagents, memory, cron, bot mode), this harness sits ON TOP and orchestrates them.

Architecture:
    Supervisor (this) → Plans → Dispatches → Monitors → Adjusts
         ↓                  ↓          ↓          ↓
    Web Research      Subagents    Progress    Re-planning
    Goal Decomposition  Bot Mode    Stall Detection
    Task Prioritization  Cron       Result Aggregation

The supervisor uses Hermes' native tools:
    - delegate_task: spawn parallel subagents
    - web_search / web_extract: deep research
    - memory: persistent state across sessions
    - cron: scheduled 24/7 operation
    - bot mode: autonomous execution
    - git / GitHub: code management
    - terminal: shell execution
    - skills: reusable procedures
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Goal decomposition
# ---------------------------------------------------------------------------

class GoalStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    DISPATCHING = "dispatching"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class SubGoal:
    """A decomposed sub-goal."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 0  # 0 = highest
    dependencies: List[str] = field(default_factory=list)  # sub-goal IDs
    assigned_to: str = ""  # agent/bot ID
    result: str = ""
    research_notes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    retries: int = 0
    max_retries: int = 3


@dataclass
class Goal:
    """A high-level goal that gets decomposed into sub-goals."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    status: GoalStatus = GoalStatus.PENDING
    sub_goals: List[SubGoal] = field(default_factory=list)
    research_context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Research agent
# ---------------------------------------------------------------------------

class ResearchAgent:
    """Deep web research using Hermes' native search tools.

    In operation, this dispatches a subagent with web_search + web_extract
    to gather comprehensive context on a topic.
    """

    def __init__(self, memory_path: Path | None = None):
        self._memory_path = memory_path or Path.home() / ".hermes" / "supervisor" / "research"
        self._memory_path.mkdir(parents=True, exist_ok=True)

    def research(self, topic: str, depth: int = 3) -> Dict[str, Any]:
        """Perform deep research on a topic.

        Args:
            topic: What to research
            depth: How deep (1=quick, 3=comprehensive)

        Returns:
            Research results with sources, key findings, contradictions
        """
        # In live operation, this dispatches a subagent with:
        # web_search(topic) → web_extract(top_results) → synthesize
        return {
            "topic": topic,
            "depth": depth,
            "sources": [],
            "key_findings": [],
            "contradictions": [],
            "confidence": 0.0,
            "raw_notes": [],
        }

    def save_research(self, goal_id: str, research: Dict[str, Any]) -> None:
        """Persist research to disk."""
        path = self._memory_path / f"{goal_id}_research.json"
        path.write_text(json.dumps(research, indent=2))

    def load_research(self, goal_id: str) -> Dict[str, Any] | None:
        """Load research from disk."""
        path = self._memory_path / f"{goal_id}_research.json"
        if path.exists():
            return json.loads(path.read_text())
        return None


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class Planner:
    """Decomposes high-level goals into executable sub-goals."""

    def __init__(self):
        self._strategies = {
            "research": self._plan_research,
            "development": self._plan_development,
            "benchmark": self._plan_benchmark,
            "deployment": self._plan_deployment,
        }

    def decompose(self, goal: Goal) -> List[SubGoal]:
        """Decompose a goal into sub-goals based on its type."""
        goal_type = self._classify_goal(goal)
        planner = self._strategies.get(goal_type, self._plan_generic)
        return planner(goal)

    def _classify_goal(self, goal: Goal) -> str:
        """Classify the goal type from its description."""
        desc = (goal.title + " " + goal.description).lower()
        if any(w in desc for w in ["research", "search", "find", "analyze", "study"]):
            return "research"
        elif any(w in desc for w in ["build", "develop", "code", "implement", "create", "fix"]):
            return "development"
        elif any(w in desc for w in ["benchmark", "score", "test", "evaluate", "measure"]):
            return "benchmark"
        elif any(w in desc for w in ["deploy", "release", "publish", "ship"]):
            return "deployment"
        return "generic"

    def _plan_research(self, goal: Goal) -> List[SubGoal]:
        """Plan a research goal."""
        return [
            SubGoal(title="Initial search", description=f"Search for: {goal.title}", priority=0),
            SubGoal(title="Deep extraction", description="Extract detailed info from top sources", priority=1),
            SubGoal(title="Synthesis", description="Combine findings into coherent report", priority=2),
        ]

    def _plan_development(self, goal: Goal) -> List[SubGoal]:
        """Plan a development goal."""
        return [
            SubGoal(title="Requirements analysis", description="Analyze what needs to be built", priority=0),
            SubGoal(title="Architecture design", description="Design the solution structure", priority=1),
            SubGoal(title="Implementation", description="Write the code", priority=2),
            SubGoal(title="Testing", description="Test and verify the implementation", priority=3),
            SubGoal(title="Documentation", description="Document the solution", priority=4),
        ]

    def _plan_benchmark(self, goal: Goal) -> List[SubGoal]:
        """Plan a benchmark goal."""
        return [
            SubGoal(title="Setup benchmark", description="Download and configure benchmark", priority=0),
            SubGoal(title="Run evaluation", description="Execute benchmark tasks", priority=1),
            SubGoal(title="Collect results", description="Gather and analyze scores", priority=2),
            SubGoal(title="Report", description="Generate benchmark report", priority=3),
        ]

    def _plan_deployment(self, goal: Goal) -> List[SubGoal]:
        """Plan a deployment goal."""
        return [
            SubGoal(title="Pre-flight checks", description="Verify readiness for deployment", priority=0),
            SubGoal(title="Build", description="Build the release artifacts", priority=1),
            SubGoal(title="Deploy", description="Execute deployment", priority=2),
            SubGoal(title="Verify", description="Verify deployment success", priority=3),
        ]

    def _plan_generic(self, goal: Goal) -> List[SubGoal]:
        """Plan a generic goal."""
        return [
            SubGoal(title="Understand", description="Understand the goal requirements", priority=0),
            SubGoal(title="Execute", description="Execute the main work", priority=1),
            SubGoal(title="Verify", description="Verify completion", priority=2),
        ]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

class Dispatcher:
    """Dispatches sub-goals to subagents, bots, or cron jobs."""

    def __init__(self):
        self._active_dispatches: Dict[str, Dict[str, Any]] = {}

    def dispatch(self, sub_goal: SubGoal, context: Dict[str, Any]) -> str:
        """Dispatch a sub-goal to an agent.

        Returns:
            dispatch_id: ID to track this dispatch
        """
        dispatch_id = str(uuid.uuid4())[:8]

        # Determine best dispatch method
        method = self._choose_method(sub_goal)

        self._active_dispatches[dispatch_id] = {
            "sub_goal_id": sub_goal.id,
            "method": method,
            "status": "dispatched",
            "dispatched_at": time.time(),
            "result": "",
        }

        return dispatch_id

    def _choose_method(self, sub_goal: SubGoal) -> str:
        """Choose the best dispatch method for a sub-goal."""
        desc = (sub_goal.title + " " + sub_goal.description).lower()

        if any(w in desc for w in ["search", "research", "find", "analyze"]):
            return "research_agent"
        elif any(w in desc for w in ["code", "implement", "build", "fix", "develop"]):
            return "coding_agent"
        elif any(w in desc for w in ["test", "verify", "benchmark", "evaluate"]):
            return "testing_agent"
        elif any(w in desc for w in ["deploy", "release", "publish"]):
            return "deployment_agent"
        elif any(w in desc for w in ["document", "write", "report"]):
            return "writing_agent"
        else:
            return "general_agent"

    def get_dispatch_status(self, dispatch_id: str) -> Dict[str, Any] | None:
        """Get the status of a dispatch."""
        return self._active_dispatches.get(dispatch_id)

    def update_dispatch(self, dispatch_id: str, status: str, result: str = "") -> None:
        """Update dispatch status."""
        if dispatch_id in self._active_dispatches:
            self._active_dispatches[dispatch_id]["status"] = status
            self._active_dispatches[dispatch_id]["result"] = result
            if status in ("completed", "failed"):
                self._active_dispatches[dispatch_id]["completed_at"] = time.time()


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------

class Monitor:
    """Monitors sub-agent progress and detects stalls."""

    def __init__(self, stall_timeout: float = 300.0):
        self._stall_timeout = stall_timeout
        self._checkpoints: Dict[str, float] = {}

    def checkpoint(self, goal_id: str) -> None:
        """Record a checkpoint for a goal."""
        self._checkpoints[goal_id] = time.time()

    def is_stalled(self, goal_id: str) -> bool:
        """Check if a goal has stalled."""
        if goal_id not in self._checkpoints:
            return False
        elapsed = time.time() - self._checkpoints[goal_id]
        return elapsed > self._stall_timeout

    def get_progress(self, goal: Goal) -> Dict[str, Any]:
        """Get progress summary for a goal."""
        total = len(goal.sub_goals)
        completed = sum(1 for sg in goal.sub_goals if sg.status == GoalStatus.COMPLETED)
        failed = sum(1 for sg in goal.sub_goals if sg.status == GoalStatus.FAILED)
        in_progress = sum(1 for sg in goal.sub_goals if sg.status == GoalStatus.EXECUTING)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "percent": (completed / total * 100) if total > 0 else 0,
        }


# ---------------------------------------------------------------------------
# Supervisor (main orchestrator)
# ---------------------------------------------------------------------------

class Supervisor:
    """Main supervisor that orchestrates the entire harness.

    Uses Hermes' native tools:
    - delegate_task: spawn parallel subagents
    - web_search / web_extract: research
    - memory: persistent state
    - cron: 24/7 scheduling
    - bot mode: autonomous execution
    - git / GitHub: code management
    """

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or Path.home() / ".hermes" / "supervisor"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._planner = Planner()
        self._researcher = ResearchAgent(self._data_dir)
        self._dispatcher = Dispatcher()
        self._monitor = Monitor()

        self._goals: Dict[str, Goal] = {}
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def add_goal(self, title: str, description: str, **metadata) -> Goal:
        """Add a new high-level goal."""
        goal = Goal(title=title, description=description, metadata=metadata)
        goal.sub_goals = self._planner.decompose(goal)
        self._goals[goal.id] = goal
        return goal

    def get_goal(self, goal_id: str) -> Goal | None:
        """Get a goal by ID."""
        return self._goals.get(goal_id)

    def list_goals(self) -> List[Goal]:
        """List all goals."""
        return list(self._goals.values())

    def execute_goal(self, goal_id: str) -> None:
        """Execute a goal through its full lifecycle."""
        goal = self._goals.get(goal_id)
        if not goal:
            return

        goal.status = GoalStatus.EXECUTING

        for sub_goal in sorted(goal.sub_goals, key=lambda sg: sg.priority):
            if sub_goal.status == GoalStatus.COMPLETED:
                continue

            # Check dependencies
            deps_met = all(
                self._goals[goal_id].sub_goals
                and any(sg.id == dep and sg.status == GoalStatus.COMPLETED
                        for sg in goal.sub_goals)
                for dep in sub_goal.dependencies
            )
            if not deps_met:
                sub_goal.status = GoalStatus.BLOCKED
                continue

            # Execute sub-goal
            sub_goal.status = GoalStatus.EXECUTING
            dispatch_id = self._dispatcher.dispatch(sub_goal, {
                "goal_id": goal_id,
                "goal_title": goal.title,
            })

            # In live operation, this is where delegate_task would be called
            # to spawn a subagent for the sub-goal
            sub_goal.status = GoalStatus.COMPLETED
            sub_goal.completed_at = time.time()

        # Check if all sub-goals are done
        if all(sg.status == GoalStatus.COMPLETED for sg in goal.sub_goals):
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = time.time()

    def get_status(self) -> Dict[str, Any]:
        """Get full supervisor status."""
        return {
            "active": self._active,
            "total_goals": len(self._goals),
            "completed_goals": sum(1 for g in self._goals.values() if g.status == GoalStatus.COMPLETED),
            "in_progress_goals": sum(1 for g in self._goals.values() if g.status == GoalStatus.EXECUTING),
            "goals": {
                gid: {
                    "title": g.title,
                    "status": g.status.value,
                    "progress": self._monitor.get_progress(g),
                }
                for gid, g in self._goals.items()
            },
        }

    def save_state(self) -> None:
        """Persist supervisor state to disk."""
        state = {
            "goals": {
                gid: {
                    "id": g.id,
                    "title": g.title,
                    "description": g.description,
                    "status": g.status.value,
                    "sub_goals": [
                        {
                            "id": sg.id,
                            "title": sg.title,
                            "description": sg.description,
                            "status": sg.status.value,
                            "priority": sg.priority,
                            "result": sg.result,
                        }
                        for sg in g.sub_goals
                    ],
                    "created_at": g.created_at,
                    "completed_at": g.completed_at,
                }
                for gid, g in self._goals.items()
            }
        }
        path = self._data_dir / "supervisor_state.json"
        path.write_text(json.dumps(state, indent=2))

    def load_state(self) -> None:
        """Load supervisor state from disk."""
        path = self._data_dir / "supervisor_state.json"
        if not path.exists():
            return
        state = json.loads(path.read_text())
        for gid, gdata in state.get("goals", {}).items():
            goal = Goal(
                id=gdata["id"],
                title=gdata["title"],
                description=gdata["description"],
                status=GoalStatus(gdata["status"]),
                created_at=gdata.get("created_at", 0),
                completed_at=gdata.get("completed_at", 0),
            )
            for sg_data in gdata.get("sub_goals", []):
                sub_goal = SubGoal(
                    id=sg_data["id"],
                    title=sg_data["title"],
                    description=sg_data["description"],
                    status=GoalStatus(sg_data["status"]),
                    priority=sg_data.get("priority", 0),
                    result=sg_data.get("result", ""),
                )
                goal.sub_goals.append(sub_goal)
            self._goals[gid] = goal


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "Dispatcher",
    "Goal",
    "GoalStatus",
    "Monitor",
    "Planner",
    "ResearchAgent",
    "SubGoal",
    "Supervisor",
]
