#!/usr/bin/env python3
"""
world_model.py — Dynamic Causal Graph & World State Representation
Tracks entities, relations, and predictive causal branches in the agent environment.
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

@dataclass
class Entity:
    id: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)

@dataclass
class CausalRelation:
    cause: str
    effect: str
    strength: float = 1.0
    evidence_count: int = 1
    description: str = ""

class WorldModel:
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.causal_graph: Dict[str, List[CausalRelation]] = {}  # cause -> list of relations

    def upsert_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any]) -> Entity:
        if entity_id in self.entities:
            ent = self.entities[entity_id]
            ent.properties.update(properties)
            ent.last_updated = time.time()
        else:
            ent = Entity(id=entity_id, entity_type=entity_type, properties=properties)
            self.entities[entity_id] = ent
        return ent

    def add_causal_link(self, cause: str, effect: str, strength: float = 1.0, description: str = ""):
        if cause not in self.causal_graph:
            self.causal_graph[cause] = []

        # Check if relation already exists
        for rel in self.causal_graph[cause]:
            if rel.effect == effect:
                rel.evidence_count += 1
                rel.strength = (rel.strength * (rel.evidence_count - 1) + strength) / rel.evidence_count
                return rel

        new_rel = CausalRelation(cause=cause, effect=effect, strength=strength, description=description)
        self.causal_graph[cause].append(new_rel)
        return new_rel

    def predict_effects(self, action_or_event: str, min_strength: float = 0.5) -> List[CausalRelation]:
        """Predicts probable downstream effects of a given action or event."""
        relations = self.causal_graph.get(action_or_event, [])
        return [r for r in relations if r.strength >= min_strength]

    def get_world_summary(self) -> Dict[str, Any]:
        return {
            "entity_count": len(self.entities),
            "causal_link_count": sum(len(rels) for rels in self.causal_graph.values()),
            "entities": {eid: e.properties for eid, e in self.entities.items()}
        }
