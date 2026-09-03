"""Planner — Decomposes high-level goals into executable sub-goals."""
from __future__ import annotations
from typing import List
from core.supervisor import Goal, Task, TaskType


class Planner:
    """Decomposes high-level goals into executable sub-goals."""

    def __init__(self):
        self._strategies = {
            "research": self._plan_research,
            "development": self._plan_development,
            "benchmark": self._plan_benchmark,
            "deployment": self._plan_deployment,
        }

    def decompose(self, goal: Goal) -> List[Task]:
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

    def _plan_research(self, goal: Goal) -> List[Task]:
        return [
            Task(title="Initial search", description=f"Search for: {goal.title}", type=TaskType.RESEARCH),
            Task(title="Deep extraction", description="Extract detailed info from top sources", type=TaskType.RESEARCH),
            Task(title="Synthesis", description="Combine findings into coherent report", type=TaskType.WRITING),
        ]

    def _plan_development(self, goal: Goal) -> List[Task]:
        return [
            Task(title="Requirements analysis", description="Analyze what needs to be built", type=TaskType.GENERAL),
            Task(title="Architecture design", description="Design the solution structure", type=TaskType.CODING),
            Task(title="Implementation", description="Write the code", type=TaskType.CODING),
            Task(title="Testing", description="Test and verify the implementation", type=TaskType.TESTING),
            Task(title="Documentation", description="Document the solution", type=TaskType.WRITING),
        ]

    def _plan_benchmark(self, goal: Goal) -> List[Task]:
        return [
            Task(title="Setup benchmark", description="Download and configure benchmark", type=TaskType.GENERAL),
            Task(title="Run evaluation", description="Execute benchmark tasks", type=TaskType.TESTING),
            Task(title="Collect results", description="Gather and analyze scores", type=TaskType.GENERAL),
            Task(title="Report", description="Generate benchmark report", type=TaskType.WRITING),
        ]

    def _plan_deployment(self, goal: Goal) -> List[Task]:
        return [
            Task(title="Pre-flight checks", description="Verify readiness for deployment", type=TaskType.GENERAL),
            Task(title="Build", description="Build the release artifacts", type=TaskType.CODING),
            Task(title="Deploy", description="Execute deployment", type=TaskType.DEPLOYMENT),
            Task(title="Verify", description="Verify deployment success", type=TaskType.TESTING),
        ]

    def _plan_generic(self, goal: Goal) -> List[Task]:
        return [
            Task(title="Understand", description="Understand the goal requirements", type=TaskType.GENERAL),
            Task(title="Execute", description="Execute the main work", type=TaskType.GENERAL),
            Task(title="Verify", description="Verify completion", type=TaskType.GENERAL),
        ]
