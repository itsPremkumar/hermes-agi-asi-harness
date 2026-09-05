"""World Model — Persistent state representation of the environment.

Continuously maintained state representation with entities, relationships,
properties, events, actions, dependencies, resources, constraints, beliefs,
uncertainty, causal relationships, temporal state, external changes,
forecasts, and counterfactual branches.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class EntityType(str, Enum):
    GOAL = "goal"
    TASK = "task"
    AGENT = "agent"
    RESOURCE = "resource"
    CONSTRAINT = "constraint"
    BELIEF = "belief"
    SKILL = "skill"
    TOOL = "tool"


@dataclass
class Entity:
    """An entity in the world model."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: EntityType = EntityType.GOAL
    name: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    confidence: float = 1.0


@dataclass
class Belief:
    """A belief about the world."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    claim: str = ""
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    independent_sources: int = 0
    contradictory_evidence: List[str] = field(default_factory=list)
    freshness: float = 0.0
    causal_support: float = 0.0
    last_validated: float = 0.0
    dependent_beliefs: List[str] = field(default_factory=list)


@dataclass
class CausalLink:
    """A causal relationship between entities."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    cause_id: str = ""
    effect_id: str = ""
    strength: float = 0.0
    evidence: List[str] = field(default_factory=list)


@dataclass
class Forecast:
    """A future-state prediction."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    probability: float = 0.0
    horizon: str = ""  # short, medium, long
    conditions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class Counterfactual:
    """A counterfactual branch."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    condition: str = ""
    outcome: str = ""
    probability: float = 0.0
    evidence: List[str] = field(default_factory=list)


class WorldModel:
    """Continuously maintained state representation."""

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or Path.home() / ".hermes" / "supervisor" / "world_model"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._entities: Dict[str, Entity] = {}
        self._beliefs: Dict[str, Belief] = {}
        self._causal_links: List[CausalLink] = []
        self._forecasts: List[Forecast] = []
        self._counterfactuals: List[Counterfactual] = []
        self._state_history: List[Dict[str, Any]] = []

    # --- Entity management ---

    def add_entity(
        self,
        name: str,
        entity_type: EntityType,
        properties: Optional[Dict[str, Any]] = None,
        relationships: Optional[Dict[str, List[str]]] = None,
    ) -> Entity:
        """Add an entity to the world model."""
        entity = Entity(
            name=name,
            type=entity_type,
            properties=properties or {},
            relationships=relationships or {},
        )
        self._entities[entity.id] = entity
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    def update_entity(self, entity_id: str, **kwargs) -> Optional[Entity]:
        """Update an entity."""
        entity = self._entities.get(entity_id)
        if not entity:
            return None
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        entity.updated_at = time.time()
        return entity

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self._entities.values() if e.type == entity_type]

    # --- Belief management ---

    def add_belief(
        self,
        claim: str,
        confidence: float = 0.0,
        evidence: Optional[List[str]] = None,
    ) -> Belief:
        """Add a belief."""
        belief = Belief(
            claim=claim,
            confidence=confidence,
            evidence=evidence or [],
            last_validated=time.time(),
        )
        self._beliefs[belief.id] = belief
        return belief

    def update_belief(self, belief_id: str, confidence: float, evidence: str = "") -> None:
        """Update a belief with new evidence."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return
        belief.confidence = confidence
        if evidence:
            belief.evidence.append(evidence)
            belief.independent_sources += 1
        belief.last_validated = time.time()

    def get_beliefs_by_confidence(self, min_confidence: float = 0.0) -> List[Belief]:
        """Get beliefs above a confidence threshold."""
        return [b for b in self._beliefs.values() if b.confidence >= min_confidence]

    # --- Causal model ---

    def add_causal_link(
        self,
        cause_id: str,
        effect_id: str,
        strength: float = 0.5,
        evidence: Optional[List[str]] = None,
    ) -> CausalLink:
        """Add a causal link."""
        link = CausalLink(
            cause_id=cause_id,
            effect_id=effect_id,
            strength=strength,
            evidence=evidence or [],
        )
        self._causal_links.append(link)
        return link

    def get_causal_links(self, entity_id: str) -> List[CausalLink]:
        """Get all causal links for an entity."""
        return [link for link in self._causal_links if link.cause_id == entity_id or link.effect_id == entity_id]

    # --- Forecasts ---

    def add_forecast(
        self,
        description: str,
        probability: float,
        horizon: str = "medium",
        conditions: Optional[List[str]] = None,
    ) -> Forecast:
        """Add a forecast."""
        forecast = Forecast(
            description=description,
            probability=probability,
            horizon=horizon,
            conditions=conditions or [],
        )
        self._forecasts.append(forecast)
        return forecast

    def get_forecasts(self, horizon: Optional[str] = None) -> List[Forecast]:
        """Get forecasts, optionally filtered by horizon."""
        if horizon:
            return [f for f in self._forecasts if f.horizon == horizon]
        return self._forecasts.copy()

    # --- Counterfactuals ---

    def add_counterfactual(
        self,
        condition: str,
        outcome: str,
        probability: float = 0.0,
    ) -> Counterfactual:
        """Add a counterfactual branch."""
        cf = Counterfactual(
            condition=condition,
            outcome=outcome,
            probability=probability,
        )
        self._counterfactuals.append(cf)
        return cf

    # --- State estimation ---

    def estimate_state(self, observations: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate current state from observations."""
        return {
            "timestamp": time.time(),
            "observations": observations,
            "entities": len(self._entities),
            "beliefs": len(self._beliefs),
            "confident_beliefs": len(self.get_beliefs_by_confidence(0.7)),
            "forecasts": len(self._forecasts),
        }

    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the world model state."""
        return {
            "entities": len(self._entities),
            "beliefs": len(self._beliefs),
            "causal_links": len(self._causal_links),
            "forecasts": len(self._forecasts),
            "counterfactuals": len(self._counterfactuals),
            "entity_types": {
                t.value: len(self.get_entities_by_type(t))
                for t in EntityType
            },
        }

    # --- Persistence ---

    def save(self) -> None:
        """Persist world model to disk."""
        data = {
            "entities": {
                eid: {
                    "id": e.id,
                    "type": e.type.value,
                    "name": e.name,
                    "properties": e.properties,
                    "confidence": e.confidence,
                }
                for eid, e in self._entities.items()
            },
            "beliefs": {
                bid: {
                    "id": b.id,
                    "claim": b.claim,
                    "confidence": b.confidence,
                    "evidence_count": len(b.evidence),
                }
                for bid, b in self._beliefs.items()
            },
        }
        path = self._data_dir / "world_model.json"
        path.write_text(json.dumps(data, indent=2))

    def load(self) -> None:
        """Load world model from disk."""
        path = self._data_dir / "world_model.json"
        if not path.exists():
            return
        data = json.loads(path.read_text())
        for eid, edata in data.get("entities", {}).items():
            entity = Entity(
                id=edata["id"],
                type=EntityType(edata["type"]),
                name=edata.get("name", ""),
                properties=edata.get("properties", {}),
                confidence=edata.get("confidence", 1.0),
            )
            self._entities[eid] = entity
