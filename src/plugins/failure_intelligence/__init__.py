"""
Failure Intelligence + Counterfactual Recovery — Sections 41, 43 of v7 spec

Structured failure data, root cause classification, recurrence tracking.
After failure: generate alternative trajectories, simulate, compare, identify decision boundary.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FailureRecord:
    """A structured failure record."""
    id: str
    mission_id: str
    task_id: str
    expected: str
    actual: str
    failure_class: str  # knowledge_gap, reasoning_error, planning_error, tool_selection, etc.
    root_cause: str
    recovery_action: str = ""
    counterfactuals: list[str] = field(default_factory=list)
    recurrence_count: int = 0
    impact_score: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class Counterfactual:
    """A counterfactual analysis."""
    id: str
    failure_id: str
    description: str
    alternative_action: str
    predicted_outcome: str
    would_have_succeeded: bool
    decision_boundary: str  # "The decision point where things went wrong"
    lesson: str = ""


class FailureIntelligenceEngine:
    """Failure analysis and counterfactual recovery."""

    FAILURE_CLASSES = [
        "knowledge_gap", "reasoning_error", "planning_error",
        "tool_selection", "tool_execution", "memory_retrieval",
        "coordination", "verification", "environment",
        "resource", "security", "policy",
    ]

    def __init__(self):
        self._failures: dict[str, FailureRecord] = {}
        self._counterfactuals: dict[str, Counterfactual] = {}
        self._recurrence: dict[str, list[str]] = {}  # root_cause → [failure_ids]

    def record_failure(
        self,
        mission_id: str,
        task_id: str,
        expected: str,
        actual: str,
        failure_class: str,
        root_cause: str,
        impact_score: float = 0.5,
    ) -> FailureRecord:
        """Record a structured failure."""
        failure = FailureRecord(
            id=str(uuid.uuid4()),
            mission_id=mission_id,
            task_id=task_id,
            expected=expected,
            actual=actual,
            failure_class=failure_class,
            root_cause=root_cause,
            impact_score=impact_score,
        )
        self._failures[failure.id] = failure
        
        # Track recurrence
        if root_cause not in self._recurrence:
            self._recurrence[root_cause] = []
        self._recurrence[root_cause].append(failure.id)
        failure.recurrence_count = len(self._recurrence[root_cause])
        
        return failure

    def record_recovery(self, failure_id: str, action: str):
        """Record a recovery action."""
        if failure_id in self._failures:
            self._failures[failure_id].recovery_action = action

    def generate_counterfactuals(self, failure_id: str) -> list[Counterfactual]:
        """Generate counterfactual analyses for a failure."""
        failure = self._failures.get(failure_id)
        if not failure:
            return []

        counterfactuals = []
        
        # Generate alternatives based on failure class
        alternatives = self._suggest_alternatives(failure)
        
        for alt_action, description in alternatives:
            cf = Counterfactual(
                id=str(uuid.uuid4()),
                failure_id=failure_id,
                description=description,
                alternative_action=alt_action,
                predicted_outcome=f"Alternative: {alt_action}",
                would_have_succeeded=True,  # Optimistic prediction
                decision_boundary=f"At point of {failure.failure_class}: {failure.root_cause}",
                lesson=f"Consider {alt_action} when encountering {failure.root_cause}",
            )
            self._counterfactuals[cf.id] = cf
            counterfactuals.append(cf)
            failure.counterfactuals.append(cf.id)
        
        return counterfactuals

    def _suggest_alternatives(self, failure: FailureRecord) -> list[tuple]:
        """Suggest alternative actions based on failure class."""
        suggestions = {
            "knowledge_gap": [
                ("research_first", "Research the unknown before acting"),
                ("ask_clarification", "Ask for clarification"),
                ("use_assumption", "Proceed with bounded assumption and disclose"),
            ],
            "reasoning_error": [
                ("use_different_model", "Try a different reasoning model"),
                ("decompose_further", "Break into smaller sub-problems"),
                ("add_critic", "Add an independent critic/reviewer"),
            ],
            "planning_error": [
                ("replan_from_current", "Replan from current state"),
                ("use_different_strategy", "Try alternative planning strategy"),
                ("add_checkpoint", "Add more frequent checkpoints"),
            ],
            "tool_selection": [
                ("try_alternative_tool", "Try a different tool"),
                ("combine_tools", "Use multiple tools together"),
                ("manual_fallback", "Fall back to manual execution"),
            ],
            "tool_execution": [
                ("retry_with_backoff", "Retry with exponential backoff"),
                ("use_different_params", "Try different parameters"),
                ("add_timeout", "Add explicit timeout and fallback"),
            ],
        }
        return suggestions.get(failure.failure_class, [
            ("retry", "Retry the operation"),
            ("escalate", "Escalate to human oversight"),
            ("skip_and_continue", "Skip this step and continue"),
        ])

    def get_recurring_failures(self, min_count: int = 2) -> list[dict[str, Any]]:
        """Get failures that recur frequently."""
        recurring = []
        for root_cause, failure_ids in self._recurrence.items():
            if len(failure_ids) >= min_count:
                recurring.append({
                    "root_cause": root_cause,
                    "count": len(failure_ids),
                    "failures": failure_ids,
                })
        recurring.sort(key=lambda x: x["count"], reverse=True)
        return recurring

    def get_failure_summary(self) -> dict[str, Any]:
        """Get failure statistics."""
        if not self._failures:
            return {"total": 0}
        
        classes = {}
        for f in self._failures.values():
            classes[f.failure_class] = classes.get(f.failure_class, 0) + 1
        
        return {
            "total": len(self._failures),
            "by_class": classes,
            "counterfactuals": len(self._counterfactuals),
            "recurring_causes": len(self.get_recurring_failures()),
            "avg_impact": round(sum(f.impact_score for f in self._failures.values()) / len(self._failures), 4),
        }


class FailureIntelligencePlugin:
    def __init__(self):
        self.engine = FailureIntelligenceEngine()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.engine.get_failure_summary()}

    async def record_failure(self, **kwargs):
        return self.engine.record_failure(**kwargs)

    async def generate_counterfactuals(self, failure_id: str):
        return self.engine.generate_counterfactuals(failure_id)

    async def get_recurring(self):
        return self.engine.get_recurring_failures()


async def create(kernel=None):
    plugin = FailureIntelligencePlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
