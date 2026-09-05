"""
HERMES INTELLIGENCE OS — WORLD MODEL FIRST-CLASS SUBSYSTEM
==========================================================
The unified interface to the external and internal reality model:
- What exists (EntityGraph)
- What is believed true (BeliefSystem)
- What caused what & counterfactuals (CausalGraph)
- What actions are possible (ActionAffordanceModel)
- Active Abstraction Gate (Tycho): Decides when constructing a world model is worth the cost
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .affordances import ActionAffordanceModel
from .beliefs import BeliefSystem
from .causal import CausalGraph
from .entities import EntityGraph, EntityType

logger = logging.getLogger("hermes.world_model")


class AbstractionMode(str, Enum):
    DIRECT_INTERACTION = "direct_interaction"
    WORLD_MODEL_GROUNDED = "world_model_grounded"


@dataclass
class AbstractionDecision:
    mode: AbstractionMode
    rationale: str
    estimated_cost_ratio: float  # 0.05 for direct, 1.0 for grounded
    requires_causal_graph: bool


class ActiveAbstractionGate:
    """
    Tycho-inspired Active Abstraction Gate.
    Decides whether constructing or updating an elaborate world model graph is worth
    the compute and latency cost, or whether direct interaction is optimal.
    """

    def evaluate(self, task_description: str, risk_level: str = "medium") -> AbstractionDecision:
        desc_lower = task_description.lower()
        is_simple = any(k in desc_lower for k in ("read", "view", "cat", "print", "echo", "status", "format", "list"))
        is_complex = any(k in desc_lower for k in ("refactor", "architect", "consensus", "security", "causal", "optimize", "race_condition", "distributed", "allocator"))

        if risk_level in ("high", "critical") or is_complex:
            return AbstractionDecision(
                mode=AbstractionMode.WORLD_MODEL_GROUNDED,
                rationale="Task involves high complexity or risk; constructing grounded world model is justified.",
                estimated_cost_ratio=1.0,
                requires_causal_graph=True,
            )
        if is_simple and risk_level == "low":
            return AbstractionDecision(
                mode=AbstractionMode.DIRECT_INTERACTION,
                rationale="Task is simple/stateless; bypassing world model graph to conserve compute and latency.",
                estimated_cost_ratio=0.05,
                requires_causal_graph=False,
            )
        return AbstractionDecision(
            mode=AbstractionMode.WORLD_MODEL_GROUNDED,
            rationale="Standard mission execution; grounded world model enabled.",
            estimated_cost_ratio=0.5,
            requires_causal_graph=False,
        )


class WorldModel:
    """
    First-Class World Model Subsystem.
    Maintains a continuous, grounded, multi-scale representation of reality.
    """

    def __init__(self):
        self.entities = EntityGraph()
        self.beliefs = BeliefSystem()
        self.causal = CausalGraph()
        self.affordances = ActionAffordanceModel()
        self.abstraction_gate = ActiveAbstractionGate()
        self._last_snapshot_time = time.time()

    def update_from_observation(self, observation: dict[str, Any]) -> None:
        """Ingest raw perception/observation into the world model."""
        entity_name = observation.get("entity")
        if entity_name:
            self.entities.add_entity(
                name=entity_name,
                entity_type=observation.get("type", EntityType.CONCEPT),
                properties=observation.get("properties", {}),
            )

        fact = observation.get("fact")
        if fact:
            source = observation.get("source", "observation://local")
            is_contra = observation.get("is_contradiction", False)
            self.beliefs.add_evidence(proposition=fact, evidence_ref=source, is_contradiction=is_contra)

    def snapshot(self) -> dict[str, Any]:
        """Capture point-in-time state of the entire world model."""
        self._last_snapshot_time = time.time()
        return {
            "timestamp": self._last_snapshot_time,
            "entities": self.entities.to_dict(),
            "beliefs": self.beliefs.to_dict(),
            "causal": self.causal.to_dict(),
            "available_affordances_count": len(self.affordances.all_affordances()),
        }
