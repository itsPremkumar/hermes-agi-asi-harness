
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
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


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
    properties: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    confidence: Confidence = Confidence.UNCERTAIN
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class CausalModel:
    cause: str
    mechanism: str
    effect: str
    confidence: float = 0.5
    evidence: List[str] = field(default_factory=list)


@dataclass
class WorldTransition:
    before: Dict[str, Any]
    action: Dict[str, Any]
    observation: Dict[str, Any]
    after: Dict[str, Any]
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

    def __init__(self, persist_path: Optional[str] = None):
        self.persist_path = persist_path
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Dict[str, str]] = []
        self.resources: List[Dict[str, Any]] = []
        self.capabilities: List[Dict[str, Any]] = []
        self.environment: Dict[str, Any] = {}
        self.tasks: List[Dict[str, Any]] = []
        self.dependencies: List[Dict[str, Any]] = []
        self.observations: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.assumptions: List[Dict[str, Any]] = []
        self.hypotheses: List[Dict[str, Any]] = []
        self.risks: List[Dict[str, Any]] = []
        self.commitments: List[Dict[str, Any]] = []
        self.external_state: Dict[str, Any] = {}
        self.temporal_state: Dict[str, Any] = {
            "past": {},
            "present": {},
            "future_scenarios": []
        }
        self.causal_models: List[CausalModel] = []
        self.counterfactual_worlds: List[Dict[str, Any]] = []
        self.simulation_ensemble: List[Dict[str, Any]] = []
        self.unknowns: List[str] = []
        self.known_unknowns: List[str] = []
        self.unknown_unknowns_estimate: float = 0.5

    def add_entity(self, name: str, type: str, properties: Dict[str, Any] = None) -> Entity:
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

    def add_observation(self, observation: Dict[str, Any], source: str = "agent"):
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

    def query(self, query: str) -> Dict[str, Any]:
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

    def get_state(self) -> Dict[str, Any]:
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

import os
