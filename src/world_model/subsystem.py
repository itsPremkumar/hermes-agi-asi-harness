"""
HERMES INTELLIGENCE OS — WORLD MODEL FIRST-CLASS SUBSYSTEM
==========================================================
The unified interface to the external and internal reality model:
- What exists (EntityGraph)
- What is believed true (BeliefSystem)
- What caused what & counterfactuals (CausalGraph)
- What actions are possible (ActionAffordanceModel)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from .entities import EntityGraph, Entity, EntityType, Relationship
from .beliefs import BeliefSystem, Belief, BeliefState
from .causal import CausalGraph, CausalEdge
from .affordances import ActionAffordanceModel, ActionAffordance

logger = logging.getLogger("hermes.world_model")


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
