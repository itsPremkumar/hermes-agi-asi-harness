"""Replanning Engine + Dynamic Re-decomposition.

Handles dynamic re-decomposition when new complexity is discovered
and replanning when the current plan is no longer optimal.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ReplanTrigger(str, Enum):
    """What triggered the replan."""
    STAGNATION = "stagnation"
    NEW_DISCOVERY = "new_discovery"
    DEPENDENCY_CHANGE = "dependency_change"
    RESOURCE_CHANGE = "resource_change"
    FAILURE = "failure"
    RISK_ESCALATION = "risk_escalation"
    MANUAL = "manual"


class ReplanAction(str, Enum):
    """What action the replan takes."""
    RE_DECOMPOSE = "re_decompose"
    REASSIGN = "reassign"
    REDUCE_SCOPE = "reduce_scope"
    CHANGE_STRATEGY = "change_strategy"
    ADD_TASKS = "add_tasks"
    REMOVE_TASKS = "remove_tasks"
    REORDER = "reorder"
    SPLIT_TASK = "split_task"
    MERGE_TASKS = "merge_tasks"


@dataclass
class ReplanEvent:
    """A replanning event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trigger: ReplanTrigger = ReplanTrigger.STAGNATION
    action: ReplanAction = ReplanAction.RE_DECOMPOSE
    reason: str = ""
    task_id: str = ""
    worker_id: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReplanningEngine:
    """Dynamic re-decomposition and replanning."""

    def __init__(self):
        self._history: List[ReplanEvent] = []

    def needs_replanning(
        self,
        stagnation_signals: List[Any],
        mission_progress: Dict[str, Any],
    ) -> bool:
        """Determine if replanning is needed."""
        # Replan if too many stagnation signals
        if len(stagnation_signals) >= 3:
            return True

        # Replan if progress is too slow
        if mission_progress.get("percent", 0) < 20 and mission_progress.get("iterations", 0) > 10:
            return True

        # Replan if too many blocked tasks
        if mission_progress.get("blocked", 0) > mission_progress.get("total", 1) * 0.3:
            return True

        return False

    def replan(
        self,
        trigger: ReplanTrigger,
        mission_graph: Any,
        execution_graph: Any,
        evidence_graph: Any,
        context: Dict[str, Any],
    ) -> ReplanEvent:
        """Execute a replanning cycle."""
        # Determine the best action
        action = self._select_action(trigger, context)

        event = ReplanEvent(
            trigger=trigger,
            action=action,
            reason=f"Replan due to {trigger.value}",
            metadata=context,
        )

        # Execute the action
        if action == ReplanAction.RE_DECOMPOSE:
            self._re_decompose(mission_graph, context)
        elif action == ReplanAction.REASSIGN:
            self._reassign(execution_graph, context)
        elif action == ReplanAction.REDUCE_SCOPE:
            self._reduce_scope(mission_graph, context)
        elif action == ReplanAction.CHANGE_STRATEGY:
            self._change_strategy(context)
        elif action == ReplanAction.ADD_TASKS:
            self._add_tasks(mission_graph, context)
        elif action == ReplanAction.REMOVE_TASKS:
            self._remove_tasks(mission_graph, context)
        elif action == ReplanAction.REORDER:
            self._reorder(mission_graph, context)
        elif action == ReplanAction.SPLIT_TASK:
            self._split_task(mission_graph, context)
        elif action == ReplanAction.MERGE_TASKS:
            self._merge_tasks(mission_graph, context)

        self._history.append(event)
        return event

    def _select_action(self, trigger: ReplanTrigger, context: Dict[str, Any]) -> ReplanAction:
        """Select the best replan action."""
        actions = {
            ReplanTrigger.STAGNATION: ReplanAction.RE_DECOMPOSE,
            ReplanTrigger.NEW_DISCOVERY: ReplanAction.ADD_TASKS,
            ReplanTrigger.DEPENDENCY_CHANGE: ReplanAction.REORDER,
            ReplanTrigger.RESOURCE_CHANGE: ReplanAction.REASSIGN,
            ReplanTrigger.FAILURE: ReplanAction.CHANGE_STRATEGY,
            ReplanTrigger.RISK_ESCALATION: ReplanAction.REDUCE_SCOPE,
            ReplanTrigger.MANUAL: ReplanAction.RE_DECOMPOSE,
        }
        return actions.get(trigger, ReplanAction.RE_DECOMPOSE)

    def _re_decompose(self, mission_graph: Any, context: Dict[str, Any]) -> None:
        """Re-decompose a task into smaller subtasks."""
        task_id = context.get("task_id", "")
        if task_id and hasattr(mission_graph, 'get_node'):
            node = mission_graph.get_node(task_id)
            if node:
                # Mark as needing re-decomposition
                node.metadata["needs_re_decomposition"] = True

    def _reassign(self, execution_graph: Any, context: Dict[str, Any]) -> None:
        """Reassign a task to a different worker."""
        task_id = context.get("task_id", "")
        new_worker_id = context.get("new_worker_id", "")
        if task_id and new_worker_id:
            pass  # Reassignment logic

    def _reduce_scope(self, mission_graph: Any, context: Dict[str, Any]) -> None:
        """Reduce the scope of a task."""
        task_id = context.get("task_id", "")
        if task_id and hasattr(mission_graph, 'get_node'):
            node = mission_graph.get_node(task_id)
            if node:
                node.metadata["scope_reduced"] = True

    def _change_strategy(self, context: Dict[str, Any]) -> None:
        """Change the strategy for a task."""
        pass

    def _add_tasks(self, mission_graph: Any, context: Dict[str, Any]) -> None:
        """Add new tasks to the mission."""
        pass

    def _remove_tasks(self, mission_graph: Any, context: Dict[str, Any]) -> None:
        """Remove tasks from the mission."""
        pass

    def _reorder(self, mission_graph: Any, context: Dict[str, Any]) -> None:
        """Reorder tasks based on new dependencies."""
        pass

    def _split_task(self, mission_graph: Any, context: Dict[str, Any]) -> None:
        """Split a task into smaller tasks."""
        pass

    def _merge_tasks(self, mission_graph: Any, context: Dict[str, Any]) -> None:
        """Merge multiple tasks into one."""
        pass

    def get_history(self) -> List[ReplanEvent]:
        """Get replanning history."""
        return self._history.copy()


class DynamicDecomposer:
    """Dynamic re-decomposition when new complexity is discovered."""

    def __init__(self):
        self._decomposition_history: List[Dict[str, Any]] = []

    def decompose_on_discovery(
        self,
        task_id: str,
        discovery: str,
        mission_graph: Any,
    ) -> List[Dict[str, str]]:
        """Re-decompose a task when new complexity is discovered."""
        # Create new subtasks based on the discovery
        new_subtasks = [
            {"title": f"Handle: {discovery[:50]}", "description": discovery},
            {"title": "Verify integration", "description": "Verify integration with existing work"},
            {"title": "Update tests", "description": "Update tests for new complexity"},
        ]

        self._decomposition_history.append({
            "task_id": task_id,
            "discovery": discovery,
            "new_subtasks": len(new_subtasks),
            "timestamp": time.time(),
        })

        return new_subtasks

    def get_history(self) -> List[Dict[str, Any]]:
        """Get decomposition history."""
        return self._decomposition_history.copy()
