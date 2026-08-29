"""
Self-Improvement Boundary Plugin — Defines What CAN and CANNOT Be Changed

Defines: which capabilities are mutable, which are immutable,
which require human approval, the safety perimeter.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum


class ChangeLevel(str, Enum):
    AUTONOMOUS = "autonomous"  # agent can change
    SUPERVISED = "supervised"  # requires watchdog monitoring
    APPROVED = "approved"  # requires human approval
    FORBIDDEN = "forbidden"  # cannot be changed


@dataclass
class BoundaryRule:
    target: str
    level: ChangeLevel
    rationale: str


class SelfImprovementBoundary:
    """Defines the safety perimeter for self-modification."""

    def __init__(self):
        self._rules: List[BoundaryRule] = self._default_rules()
        self._change_log: List[Dict[str, Any]] = []

    def _default_rules(self) -> List[BoundaryRule]:
        return [
            # Procedural improvements — safe
            BoundaryRule("workflow_procedure", ChangeLevel.AUTONOMOUS,
                        "Workflow optimizations are reversible and low-risk"),
            BoundaryRule("prompt_template", ChangeLevel.SUPERVISED,
                        "Prompt changes can affect output quality"),
            BoundaryRule("skill_library", ChangeLevel.AUTONOMOUS,
                        "Skills are tested before deployment"),

            # Behavioral parameters — supervised
            BoundaryRule("tool_selection_weights", ChangeLevel.SUPERVISED,
                        "Tool routing affects performance"),
            BoundaryRule("model_selection", ChangeLevel.APPROVED,
                        "Model swaps have broad impact"),
            BoundaryRule("exploration_rate", ChangeLevel.SUPERVISED,
                        "Exploration rate affects learning"),

            # Identity — requires approval
            BoundaryRule("core_values", ChangeLevel.APPROVED,
                        "Core values require explicit human approval"),
            BoundaryRule("authority_hierarchy", ChangeLevel.APPROVED,
                        "Authority changes are sensitive"),

            # Forbidden — never change
            BoundaryRule("constitution", ChangeLevel.FORBIDDEN,
                        "Constitution is immutable"),
            BoundaryRule("corrigibility_mechanisms", ChangeLevel.FORBIDDEN,
                        "Cannot disable corrigibility"),
            BoundaryRule("safety_constraints", ChangeLevel.FORBIDDEN,
                        "Cannot weaken safety"),
            BoundaryRule("shutdown_mechanisms", ChangeLevel.FORBIDDEN,
                        "Cannot disable shutdown"),
        ]

    def can_change(self, target: str, level: Optional[ChangeLevel] = None) -> bool:
        """Check if a target can be changed at the given level."""
        for rule in self._rules:
            if rule.target == target:
                if level is None:
                    return rule.level != ChangeLevel.FORBIDDEN
                # Higher level authorization is acceptable
                level_order = [
                    ChangeLevel.FORBIDDEN,
                    ChangeLevel.APPROVED,
                    ChangeLevel.SUPERVISED,
                    ChangeLevel.AUTONOMOUS,
                ]
                return level_order.index(level) >= level_order.index(rule.level)
        # Unknown target — assume FORBIDDEN by default
        return False

    def get_required_level(self, target: str) -> ChangeLevel:
        for rule in self._rules:
            if rule.target == target:
                return rule.level
        return ChangeLevel.FORBIDDEN

    def log_change(self, target: str, level: ChangeLevel, description: str,
                   approved_by: str = "system"):
        """Log a self-improvement change."""
        self._change_log.append({
            "target": target,
            "level": level.value,
            "description": description,
            "approved_by": approved_by,
            "timestamp": time.time(),
        })

    def get_change_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self._change_log[-limit:]))

    def get_stats(self) -> Dict[str, Any]:
        by_level: Dict[str, int] = {}
        for rule in self._rules:
            by_level[rule.level.value] = by_level.get(rule.level.value, 0) + 1
        return {
            "total_rules": len(self._rules),
            "rules_by_level": by_level,
            "total_changes_logged": len(self._change_log),
        }


class SelfImprovementBoundaryPlugin:
    def __init__(self):
        self.engine = SelfImprovementBoundary()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "stats": self.engine.get_stats(),
        }


async def create(kernel=None):
    plugin = SelfImprovementBoundaryPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
