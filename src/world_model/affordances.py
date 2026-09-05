"""
HERMES INTELLIGENCE OS — ACTION AFFORDANCE MODEL
================================================
Evaluates which actions, tools, and actuators are physically, legally, and safely
available given the current world model state and active permissions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("hermes.world_model.affordances")


@dataclass
class ActionAffordance:
    action_type: str  # file_write, shell_exec, http_get, rlm_eval, git_commit
    tool_name: str
    required_entities: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    expected_effects: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high, critical
    side_effects: bool = False


class ActionAffordanceModel:
    """Computes the set of valid, safe, and effective actions at any instant."""

    def __init__(self):
        self._registered_affordances: dict[str, ActionAffordance] = {}
        self._init_standard_affordances()

    def _init_standard_affordances(self):
        self.register(ActionAffordance(
            action_type="write_file",
            tool_name="filesystem_tool",
            preconditions=["target_directory_exists", "workspace_permission_granted"],
            expected_effects=["file_persisted_to_disk"],
            risk_level="medium",
            side_effects=True,
        ))
        self.register(ActionAffordance(
            action_type="execute_python",
            tool_name="python_tool",
            preconditions=["isolated_sandbox_ready"],
            expected_effects=["code_executed_in_memory"],
            risk_level="low",
            side_effects=False,
        ))
        self.register(ActionAffordance(
            action_type="execute_rlm_repl",
            tool_name="rlm_repl",
            preconditions=["persistent_loop_active"],
            expected_effects=["state_persisted_in_heap"],
            risk_level="low",
            side_effects=False,
        ))
        self.register(ActionAffordance(
            action_type="git_commit",
            tool_name="git_tool",
            preconditions=["working_tree_valid", "invariants_tested"],
            expected_effects=["atomic_commit_recorded"],
            risk_level="medium",
            side_effects=True,
        ))
        self.register(ActionAffordance(
            action_type="web_search",
            tool_name="agent_eye_search",
            preconditions=["network_reachable"],
            expected_effects=["factual_citations_gathered"],
            risk_level="low",
            side_effects=False,
        ))

    def register(self, affordance: ActionAffordance) -> None:
        self._registered_affordances[affordance.action_type] = affordance

    def get_affordance(self, action_type: str) -> Optional[ActionAffordance]:
        return self._registered_affordances.get(action_type)

    def evaluate_available_actions(self, world_context: dict[str, Any]) -> list[ActionAffordance]:
        """Filter affordances against current world state and constraints."""
        available = []
        is_isolated = world_context.get("sandbox_isolated", True)

        for aff in self._registered_affordances.values():
            if aff.risk_level == "critical" and not is_isolated:
                continue
            available.append(aff)
        return available

    def all_affordances(self) -> list[ActionAffordance]:
        return list(self._registered_affordances.values())
