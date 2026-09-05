
"""
World Model — Continuously updated, multi-scale, causally-grounded model of reality.

Extracted from SKILL.md v9.0 ASI section 5:
- Entities, relationships, resources, capabilities
- Temporal state (past, present, future scenarios)
- Causal models
- Counterfactual worlds
- Simulation ensemble
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Confidence(str, Enum):
    CONFIRMED = "confirmed"
    SUPPORTED = "supported"
    LIKELY = "likely"
    PLAUSIBLE = "plausible"
    UNCERTAIN = "uncertain"


@dataclass
class Entity:
    id: str
    name: str
    type: str  # person, system, tool, resource, concept
    properties: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict[str, str]] = field(default_factory=list)
    confidence: Confidence = Confidence.UNCERTAIN
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class CausalModel:
    cause: str
    mechanism: str
    effect: str
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)


@dataclass
class WorldTransition:
    before: dict[str, Any]
    action: dict[str, Any]
    observation: dict[str, Any]
    after: dict[str, Any]
    timestamp: str
    actor: str
    source: str
    confidence: Confidence
    causal_hypothesis: str
    reversible: bool
    strategic_implication: str = ""


class WorldModel:
    """
    Continuously updated, multi-scale, causally-grounded model of reality.
    
    Features:
    - Entities and relationships
    - Temporal state (past, present, future scenarios)
    - Causal models
    - Counterfactual worlds
    - Simulation ensemble
    """

    def __init__(self, persist_path: str | None = None):
        self.persist_path = persist_path
        self.entities: dict[str, Entity] = {}
        self.relationships: list[dict[str, str]] = []
        self.resources: list[dict[str, Any]] = []
        self.capabilities: list[dict[str, Any]] = []
        self.environment: dict[str, Any] = {}
        self.tasks: list[dict[str, Any]] = []
        self.dependencies: list[dict[str, Any]] = []
        self.observations: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.assumptions: list[dict[str, Any]] = []
        self.hypotheses: list[dict[str, Any]] = []
        self.risks: list[dict[str, Any]] = []
        self.commitments: list[dict[str, Any]] = []
        self.external_state: dict[str, Any] = {}
        self.temporal_state: dict[str, Any] = {
            "past": {},
            "present": {},
            "future_scenarios": []
        }
        self.causal_models: list[CausalModel] = []
        self.counterfactual_worlds: list[dict[str, Any]] = []
        self.simulation_ensemble: list[dict[str, Any]] = []
        self.unknowns: list[str] = []
        self.known_unknowns: list[str] = []
        self.unknown_unknowns_estimate: float = 0.5

    def add_entity(self, name: str, type: str, properties: dict[str, Any] | None = None) -> Entity:
        """Add an entity to the world model."""
        entity = Entity(
            id=str(uuid.uuid4()),
            name=name,
            type=type,
            properties=properties or {},
        )
        self.entities[entity.id] = entity
        return entity

    def add_causal_model(self, cause: str, mechanism: str, effect: str, confidence: float = 0.5):
        """Add a causal model."""
        model = CausalModel(
            cause=cause,
            mechanism=mechanism,
            effect=effect,
            confidence=confidence,
        )
        self.causal_models.append(model)

    def add_observation(self, observation: dict[str, Any], source: str = "agent"):
        """Add an observation."""
        observation["timestamp"] = time.time()
        observation["source"] = source
        self.observations.append(observation)

    def add_hypothesis(self, hypothesis: str, confidence: float = 0.5):
        """Add a testable hypothesis."""
        self.hypotheses.append({
            "text": hypothesis,
            "confidence": confidence,
            "created_at": time.time(),
            "status": "active",
        })

    def add_risk(self, risk: str, severity: str = "medium", likelihood: float = 0.5):
        """Add a risk."""
        self.risks.append({
            "text": risk,
            "severity": severity,
            "likelihood": likelihood,
            "created_at": time.time(),
        })

    def add_future_scenario(self, scenario: str, timeframe: str, probability: float = 0.5):
        """Add a future scenario."""
        self.temporal_state["future_scenarios"].append({
            "text": scenario,
            "timeframe": timeframe,
            "probability": probability,
            "created_at": time.time(),
        })

    def query(self, query: str) -> dict[str, Any]:
        """Query the world model."""
        results = {
            "entities": [],
            "relationships": [],
            "causal_models": [],
            "relevant_observations": [],
        }

        # Simple keyword matching
        query_lower = query.lower()
        for entity in self.entities.values():
            if query_lower in entity.name.lower() or query_lower in entity.type.lower():
                results["entities"].append(entity)

        for model in self.causal_models:
            if query_lower in model.cause.lower() or query_lower in model.effect.lower():
                results["causal_models"].append(model)

        for obs in self.observations[-10:]:  # Last 10 observations
            if any(query_lower in str(v).lower() for v in obs.values()):
                results["relevant_observations"].append(obs)

        return results

    def get_state(self) -> dict[str, Any]:
        """Get the current world state."""
        return {
            "entities_count": len(self.entities),
            "causal_models_count": len(self.causal_models),
            "observations_count": len(self.observations),
            "hypotheses_count": len(self.hypotheses),
            "risks_count": len(self.risks),
            "future_scenarios_count": len(self.temporal_state["future_scenarios"]),
        }

    def save(self):
        """Persist world model to disk."""
        if self.persist_path:
            data = {
                "entities": {k: v.__dict__ for k, v in self.entities.items()},
                "causal_models": [m.__dict__ for m in self.causal_models],
                "temporal_state": self.temporal_state,
                "unknowns": self.unknowns,
                "known_unknowns": self.known_unknowns,
            }
            with open(self.persist_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)

    def load(self):
        """Load world model from disk."""
        if self.persist_path and os.path.exists(self.persist_path):
            with open(self.persist_path, 'r') as f:
                data = json.load(f)
                # Reconstruct entities
                for k, v in data.get("entities", {}).items():
                    self.entities[k] = Entity(**v)
                # Reconstruct causal models
                self.causal_models = [CausalModel(**m) for m in data.get("causal_models", [])]
                self.temporal_state = data.get("temporal_state", self.temporal_state)
                self.unknowns = data.get("unknowns", [])
                self.known_unknowns = data.get("known_unknowns", [])
