"""Goal Compiler — Transform human goals into mission contracts.

The first step in the hierarchy: take a human goal and compile it into
a structured mission contract with clear success criteria.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class GoalType(str, Enum):
    BUILD = "build"
    RESEARCH = "research"
    FIX = "fix"
    OPTIMIZE = "optimize"
    DEPLOY = "deploy"
    MIGRATE = "migrate"
    AUDIT = "audit"
    GENERAL = "general"


class Complexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class MissionContract:
    """A compiled mission contract from a human goal."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    goal_type: GoalType = GoalType.GENERAL
    complexity: Complexity = Complexity.MODERATE

    # Success criteria
    success_criteria: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)

    # Context
    constraints: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    # State
    status: str = "pending"
    priority: int = 0

    # Metadata
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "goal_type": self.goal_type.value,
            "complexity": self.complexity.value,
            "success_criteria": self.success_criteria,
            "deliverables": self.deliverables,
            "status": self.status,
        }


class GoalCompiler:
    """Compile human goals into structured mission contracts."""

    def __init__(self):
        self._history: List[MissionContract] = []

    def compile(self, human_goal: str, **context) -> MissionContract:
        """Compile a human goal into a mission contract."""
        # Classify the goal
        goal_type = self._classify_goal(human_goal)
        complexity = self._assess_complexity(human_goal)

        # Generate success criteria
        success_criteria = self._generate_success_criteria(human_goal, goal_type)

        # Generate deliverables
        deliverables = self._generate_deliverables(human_goal, goal_type)

        # Assess risks
        risks = self._assess_risks(human_goal, goal_type)

        contract = MissionContract(
            title=human_goal[:100],
            description=human_goal,
            goal_type=goal_type,
            complexity=complexity,
            success_criteria=success_criteria,
            deliverables=deliverables,
            risks=risks,
            metadata=context,
        )

        self._history.append(contract)
        return contract

    def _classify_goal(self, goal: str) -> GoalType:
        """Classify the goal type."""
        desc = goal.lower()
        if any(w in desc for w in ["build", "create", "develop", "implement", "make"]):
            return GoalType.BUILD
        elif any(w in desc for w in ["research", "study", "analyze", "investigate", "find"]):
            return GoalType.RESEARCH
        elif any(w in desc for w in ["fix", "bug", "error", "broken", "issue"]):
            return GoalType.FIX
        elif any(w in desc for w in ["optimize", "improve", "faster", "better", "enhance"]):
            return GoalType.OPTIMIZE
        elif any(w in desc for w in ["deploy", "release", "publish", "ship", "launch"]):
            return GoalType.DEPLOY
        elif any(w in desc for w in ["migrate", "move", "transfer", "convert"]):
            return GoalType.MIGRATE
        elif any(w in desc for w in ["audit", "review", "check", "inspect", "verify"]):
            return GoalType.AUDIT
        return GoalType.GENERAL

    def _assess_complexity(self, goal: str) -> Complexity:
        """Assess the complexity of the goal."""
        word_count = len(goal.split())
        if word_count < 8:
            return Complexity.SIMPLE
        elif word_count < 20:
            return Complexity.MODERATE
        elif word_count < 40:
            return Complexity.COMPLEX
        return Complexity.VERY_COMPLEX

    def _generate_success_criteria(self, goal: str, goal_type: GoalType) -> List[str]:
        """Generate success criteria based on goal type."""
        criteria = {
            GoalType.BUILD: ["Code compiles", "Tests pass", "Feature works as expected"],
            GoalType.RESEARCH: ["Sources gathered", "Findings documented", "Conclusions clear"],
            GoalType.FIX: ["Bug reproduced", "Fix implemented", "Tests pass", "No regressions"],
            GoalType.OPTIMIZE: ["Baseline measured", "Improvement demonstrated", "No regressions"],
            GoalType.DEPLOY: ["Deployment successful", "Service healthy", "Rollback plan exists"],
            GoalType.MIGRATE: ["Data migrated", "Integrity verified", "Old system decommissioned"],
            GoalType.AUDIT: ["Audit complete", "Issues documented", "Recommendations provided"],
            GoalType.GENERAL: ["Goal achieved", "Quality verified"],
        }
        return criteria.get(goal_type, ["Goal achieved"])

    def _generate_deliverables(self, goal: str, goal_type: GoalType) -> List[str]:
        """Generate expected deliverables."""
        deliverables = {
            GoalType.BUILD: ["Source code", "Tests", "Documentation"],
            GoalType.RESEARCH: ["Research report", "Sources", "Summary"],
            GoalType.FIX: ["Fix commit", "Test case", "Verification"],
            GoalType.OPTIMIZE: ["Optimized code", "Benchmark results", "Comparison report"],
            GoalType.DEPLOY: ["Deployment config", "Health check", "Rollback plan"],
            GoalType.MIGRATE: ["Migration script", "Verification report", "Cleanup"],
            GoalType.AUDIT: ["Audit report", "Findings", "Recommendations"],
            GoalType.GENERAL: ["Completed work"],
        }
        return deliverables.get(goal_type, ["Completed work"])

    def _assess_risks(self, goal: str, goal_type: GoalType) -> List[str]:
        """Assess risks for the goal."""
        risks = {
            GoalType.BUILD: ["Scope creep", "Technical debt", "Integration issues"],
            GoalType.RESEARCH: ["Outdated info", "Contradictory sources", "Scope creep"],
            GoalType.FIX: ["Side effects", "Root cause wrong", "Regressions"],
            GoalType.OPTIMIZE: ["Behavior changes", "Edge cases", "New bugs"],
            GoalType.DEPLOY: ["Downtime", "Data loss", "Rollback needed"],
            GoalType.MIGRATE: ["Data corruption", "Downtime", "Incomplete migration"],
            GoalType.AUDIT: ["Missing issues", "False positives", "Scope creep"],
            GoalType.GENERAL: ["Unknown complexity", "Blockers"],
        }
        return risks.get(goal_type, ["Unknown risks"])

    def get_history(self) -> List[MissionContract]:
        """Get compilation history."""
        return self._history.copy()
