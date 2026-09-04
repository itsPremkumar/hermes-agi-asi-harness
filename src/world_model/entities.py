"""
HERMES INTELLIGENCE OS — WORLD MODEL ENTITY GRAPH
=================================================
Maintains an internal, continuously-updated relational graph of what exists:
Physical/software entities, services, files, dependencies, capabilities, and resources.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("hermes.world_model.entities")


class EntityType(str, Enum):
    SYSTEM = "system"
    SERVICE = "service"
    FILE = "file"
    DATABASE = "database"
    TOOL = "tool"
    RESOURCE = "resource"
    CONCEPT = "concept"
    AGENT = "agent"


@dataclass
class Relationship:
    source_id: str
    relation_type: str  # depends_on, connects_to, implements, controls, owns, produces
    target_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)


@dataclass
class Entity:
    entity_id: str
    name: str
    entity_type: EntityType
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type.value if isinstance(self.entity_type, EntityType) else str(self.entity_type),
            "properties": self.properties,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class EntityGraph:
    """Relational knowledge graph representing the topology of reality."""

    def __init__(self):
        self._entities: dict[str, Entity] = {}
        self._relationships: list[Relationship] = []

    def add_entity(
        self,
        name: str,
        entity_type: EntityType | str = EntityType.CONCEPT,
        properties: Optional[dict[str, Any]] = None,
        entity_id: Optional[str] = None,
        confidence: float = 1.0,
    ) -> Entity:
        eid = entity_id or f"ent-{uuid.uuid4().hex[:8]}"
        if isinstance(entity_type, str):
            try:
                entity_type = EntityType(entity_type.lower())
            except ValueError:
                entity_type = EntityType.CONCEPT

        ent = Entity(
            entity_id=eid,
            name=name,
            entity_type=entity_type,
            properties=properties or {},
            confidence=confidence,
        )
        self._entities[eid] = ent
        return ent

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def find_by_name(self, name: str) -> Optional[Entity]:
        name_lower = name.lower()
        for e in self._entities.values():
            if e.name.lower() == name_lower:
                return e
        return None

    def add_relationship(
        self,
        source_id: str,
        relation_type: str,
        target_id: str,
        metadata: Optional[dict[str, Any]] = None,
        confidence: float = 1.0,
    ) -> Relationship:
        rel = Relationship(
            source_id=source_id,
            relation_type=relation_type,
            target_id=target_id,
            metadata=metadata or {},
            confidence=confidence,
        )
        self._relationships.append(rel)
        return rel

    def get_dependencies(self, entity_id: str) -> list[Entity]:
        """Return all entities that entity_id depends on."""
        dep_ids = [
            r.target_id
            for r in self._relationships
            if r.source_id == entity_id and r.relation_type in ("depends_on", "requires")
        ]
        return [self._entities[tid] for tid in dep_ids if tid in self._entities]

    def get_dependents(self, entity_id: str) -> list[Entity]:
        """Return all entities that depend on entity_id."""
        dep_ids = [
            r.source_id
            for r in self._relationships
            if r.target_id == entity_id and r.relation_type in ("depends_on", "requires")
        ]
        return [self._entities[sid] for sid in dep_ids if sid in self._entities]

    def all_entities(self) -> list[Entity]:
        return list(self._entities.values())

    def all_relationships(self) -> list[Relationship]:
        return list(self._relationships)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self._entities.values()],
            "relationships": [
                {
                    "source": r.source_id,
                    "relation": r.relation_type,
                    "target": r.target_id,
                    "confidence": r.confidence,
                }
                for r in self._relationships
            ],
        }
