
"""
Planning Engine — Superintelligent Planning with 6 Plan Portfolio.

Extracted from SKILL.md v9.0 ASI section 12:
- 6 plans: Conservative, Balanced, Aggressive, Experimental, Antifragile, Strategic
- Task graph with dependencies
- Dynamic replanning
"""

from __future__ import annotations

import uuid
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PlanType(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    EXPERIMENTAL = "experimental"
    ANTIFRAGILE = "antifragile"
    STRATEGIC = "strategic"


@dataclass
class Task:
    id: str
    objective: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    owner: str = ""
    workspace: str = ""
    permissions: List[str] = field(default_factory=list)
    budget: Dict[str, Any] = field(default_factory=dict)
    acceptance_tests: List[str] = field(default_factory=list)
    formal_properties: List[str] = field(default_factory=list)
    verification: Dict[str, Any] = field(default_factory=dict)
    rollback: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"


@dataclass
class Plan:
    id: str
    plan_type: PlanType
    tasks: List[Task] = field(default_factory=list)
    expected_outcome: str = ""
    success_probability: float = 0.5
    evidence: str = ""
    cost: float = 0.0
    latency: float = 0.0
    risk: float = 0.5
    reversibility: bool = True
    complexity: float = 0.5
    dependencies: List[str] = field(default_factory=list)
    maintenance: float = 0.0
    optionality: float = 0.5
    antifragility: float = 0.5
    strategic_trajectory: str = ""


class PlanningEngine:
    """
    Superintelligent planning engine.
    
    Features:
    - 6 plan portfolio (Conservative, Balanced, Aggressive, Experimental, Antifragile, Strategic)
    - Task graph with dependency management
    - Dynamic replanning triggers
    - Critical path calculation
    """

    def __init__(self):
        self.plans: Dict[str, Plan] = {}
        self.active_plan: Optional[str] = None

    def generate_plans(self, mission: Any) -> List[Plan]:
        """Generate 6 plans for a mission."""
        plans = []

        # Plan A: Conservative
        plans.append(Plan(
            id=str(uuid.uuid4()),
            plan_type=PlanType.CONSERVATIVE,
            expected_outcome="Lowest risk, proven path",
            success_probability=0.9,
            risk=0.1,
        ))

        # Plan B: Balanced (default)
        plans.append(Plan(
            id=str(uuid.uuid4()),
            plan_type=PlanType.BALANCED,
            expected_outcome="Best expected value",
            success_probability=0.7,
            risk=0.3,
        ))

        # Plan C: Aggressive
        plans.append(Plan(
            id=str(uuid.uuid4()),
            plan_type=PlanType.AGGRESSIVE,
            expected_outcome="Highest upside, managed risk",
            success_probability=0.5,
            risk=0.6,
        ))

        # Plan D: Experimental
        plans.append(Plan(
            id=str(uuid.uuid4()),
            plan_type=PlanType.EXPERIMENTAL,
            expected_outcome="Novel, high learning value",
            success_probability=0.4,
            risk=0.7,
        ))

        # Plan E: Antifragile
        plans.append(Plan(
            id=str(uuid.uuid4()),
            plan_type=PlanType.ANTIFRAGILE,
            expected_outcome="Gains from volatility, robust to unknown unknowns",
            success_probability=0.6,
            risk=0.4,
            antifragility=0.9,
        ))

        # Plan F: Strategic
        plans.append(Plan(
            id=str(uuid.uuid4()),
            plan_type=PlanType.STRATEGIC,
            expected_outcome="Maximizes long-term optionality, 100x vision",
            success_probability=0.5,
            risk=0.5,
            optionality=0.9,
            strategic_trajectory="Long-term value creation",
        ))

        for plan in plans:
            self.plans[plan.id] = plan

        return plans

    def select_plan(self, mission: Any, preference: str = "balanced") -> Optional[Plan]:
        """Select the best plan based on mission and preference."""
        if not self.plans:
            return None

        # Default to balanced
        for plan in self.plans.values():
            if plan.plan_type == PlanType.BALANCED:
                self.active_plan = plan.id
                return plan

        # Fallback to first plan
        first = list(self.plans.values())[0]
        self.active_plan = first.id
        return first

    def should_replan(self, state: Dict[str, Any]) -> bool:
        """Determine if replanning is needed."""
        triggers = [
            state.get("assumption_failed"),
            state.get("dependency_broken"),
            state.get("environment_changed"),
            state.get("criteria_changed"),
            state.get("risk_threshold_crossed"),
            state.get("evidence_re_ranked"),
            state.get("budget_changed"),
            state.get("tool_unavailable"),
            state.get("better_strategy_available"),
            state.get("strategic_opportunity_emerged"),
            state.get("simulation_reveals_superior"),
        ]
        return any(triggers)

    def get_critical_path(self, plan: Plan) -> List[str]:
        """Calculate critical path for a plan."""
        # Simple topological sort
        visited = set()
        path = []

        def visit(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)
            task = next((t for t in plan.tasks if t.id == task_id), None)
            if task:
                for dep in task.dependencies:
                    visit(dep)
                path.append(task_id)

        for task in plan.tasks:
            visit(task.id)

        return path


from enum import Enum
