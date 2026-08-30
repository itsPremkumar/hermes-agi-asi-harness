"""Dispatcher — Routes sub-goals to appropriate agents."""
from __future__ import annotations
import uuid
from typing import Any, Callable, Dict, List, Optional
from core.supervisor import Task, TaskType


class Dispatcher:
    """Routes sub-goals to agents by type."""

    def __init__(self):
        self._active_dispatches: Dict[str, Dict[str, Any]] = {}

    def dispatch(self, sub_goal: Task, context: Dict[str, Any]) -> str:
        """Dispatch a sub-goal to an agent."""
        dispatch_id = str(uuid.uuid4())[:8]
        method = self._choose_method(sub_goal)

        self._active_dispatches[dispatch_id] = {
            "sub_goal_id": sub_goal.id,
            "method": method,
            "status": "dispatched",
            "dispatched_at": 0.0,
            "result": "",
        }

        return dispatch_id

    def _choose_method(self, sub_goal: Task) -> str:
        """Choose the best dispatch method."""
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

    def get_dispatch_status(self, dispatch_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a dispatch."""
        return self._active_dispatches.get(dispatch_id)

    def update_dispatch(self, dispatch_id: str, status: str, result: str = "") -> None:
        """Update dispatch status."""
        if dispatch_id in self._active_dispatches:
            self._active_dispatches[dispatch_id]["status"] = status
            self._active_dispatches[dispatch_id]["result"] = result
