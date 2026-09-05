"""
Environment Model — Structured representation of everything Hermes knows
about the external world: entities, resources, state, relationships, events,
actions, constraints, permissions, dependencies, causal relationships,
uncertainty, predictions, and available affordances.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EntityType(str, Enum):
    SYSTEM = "system"
    APPLICATION = "application"
    DATABASE = "database"
    SERVICE = "service"
    API = "api"
    UI_ELEMENT = "ui_element"
    FILE = "file"
    USER = "user"
    RESOURCE = "resource"
    EXTERNAL = "external"


class RelationshipType(str, Enum):
    DEPENDS_ON = "depends_on"
    CONTAINS = "contains"
    CALLS = "calls"
    READS = "reads"
    WRITES = "writes"
    TRIGGERS = "triggers"
    BLOCKS = "blocks"
    PERMITS = "permits"


@dataclass
class Entity:
    id: str
    name: str
    type: EntityType
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    confidence: float = 0.5
    source_of_truth: str | None = None
    freshness: float = 0.0  # seconds since last update


@dataclass
class Relationship:
    source_id: str
    target_id: str
    type: RelationshipType
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5


@dataclass
class Resource:
    id: str
    type: str
    owner: str = ""
    state: dict[str, Any] = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    relationships: list[dict[str, str]] = field(default_factory=list)
    source_of_truth: str = ""
    freshness: float = 0.0
    risk: float = 0.5
    criticality: float = 0.5


@dataclass
class EnvironmentEvent:
    id: str
    type: str
    source: str
    timestamp: float
    payload: dict[str, Any]
    affected_entities: list[str] = field(default_factory=list)
    processed: bool = False


@dataclass
class Constraint:
    id: str
    type: str  # permission, rate_limit, budget, time, safety
    target: str
    value: Any
    enforced: bool = True
    violation_count: int = 0


@dataclass
class Permission:
    id: str
    resource_id: str
    action: str
    granted: bool
    scope: str = ""
    expires_at: float | None = None
    conditions: dict[str, Any] = field(default_factory=dict)


class EnvironmentModel:
    """
    Comprehensive model of the external environment.
    
    Entities → what exists
    Resources → what can be acted upon
    Relationships → how things connect
    Events → what has happened
    Constraints → what limits actions
    Permissions → what is allowed
    """

    def __init__(self):
        self.entities: dict[str, Entity] = {}
        self.resources: dict[str, Resource] = {}
        self.relationships: list[Relationship] = []
        self.events: list[EnvironmentEvent] = []
        self.constraints: dict[str, Constraint] = {}
        self.permissions: dict[str, Permission] = {}
        self.metadata: dict[str, Any] = {
            "created_at": time.time(),
            "version": "9.0",
        }

    # ── Entity Management ──────────────────────────────────────────────────

    def add_entity(
        self,
        name: str,
        type: EntityType,
        state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        source_of_truth: str | None = None,
    ) -> Entity:
        entity = Entity(
            id=str(uuid.uuid4()),
            name=name,
            type=type,
            state=state or {},
            metadata=metadata or {},
            source_of_truth=source_of_truth,
            freshness=0.0,
        )
        self.entities[entity.id] = entity
        return entity

    def get_entity(self, entity_id: str) -> Entity | None:
        return self.entities.get(entity_id)

    def find_entities_by_name(self, name: str) -> list[Entity]:
        return [e for e in self.entities.values() if name.lower() in e.name.lower()]

    def find_entities_by_type(self, type: EntityType) -> list[Entity]:
        return [e for e in self.entities.values() if e.type == type]

    def update_entity_state(self, entity_id: str, state_update: dict[str, Any]) -> bool:
        entity = self.entities.get(entity_id)
        if not entity:
            return False
        entity.state.update(state_update)
        entity.updated_at = time.time()
        entity.freshness = 0.0
        return True

    # ── Resource Management ────────────────────────────────────────────────

    def add_resource(self, type: str, state: dict[str, Any] | None = None,
                     capabilities: list[str] | None = None, owner: str = "",
                     criticality: float = 0.5) -> Resource:
        resource = Resource(
            id=str(uuid.uuid4()),
            type=type,
            owner=owner,
            state=state or {},
            capabilities=capabilities or [],
            criticality=criticality,
        )
        self.resources[resource.id] = resource
        return resource

    def get_resource(self, resource_id: str) -> Resource | None:
        return self.resources.get(resource_id)

    def find_resources_by_capability(self, capability: str) -> list[Resource]:
        return [r for r in self.resources.values() if capability in r.capabilities]

    # ── Relationship Management ────────────────────────────────────────────

    def add_relationship(self, source_id: str, target_id: str,
                         type: RelationshipType, metadata: dict[str, Any] | None = None) -> Relationship:
        rel = Relationship(
            source_id=source_id,
            target_id=target_id,
            type=type,
            metadata=metadata or {},
        )
        self.relationships.append(rel)
        return rel

    def get_relationships_for(self, entity_id: str) -> list[Relationship]:
        return [r for r in self.relationships
                if r.source_id == entity_id or r.target_id == entity_id]

    def get_dependents(self, entity_id: str) -> list[str]:
        """Get all entities that depend on the given entity."""
        return [r.source_id for r in self.relationships
                if r.target_id == entity_id and r.type == RelationshipType.DEPENDS_ON]

    def get_dependencies(self, entity_id: str) -> list[str]:
        """Get all entities the given entity depends on."""
        return [r.target_id for r in self.relationships
                if r.source_id == entity_id and r.type == RelationshipType.DEPENDS_ON]

    # ── Event Management ───────────────────────────────────────────────────

    def add_event(self, type: str, source: str, payload: dict[str, Any],
                  affected_entities: list[str] | None = None) -> EnvironmentEvent:
        event = EnvironmentEvent(
            id=str(uuid.uuid4()),
            type=type,
            source=source,
            timestamp=time.time(),
            payload=payload,
            affected_entities=affected_entities or [],
        )
        self.events.append(event)
        return event

    def get_events_for_entity(self, entity_id: str) -> list[EnvironmentEvent]:
        return [e for e in self.events if entity_id in e.affected_entities]

    def get_unprocessed_events(self) -> list[EnvironmentEvent]:
        return [e for e in self.events if not e.processed]

    def mark_event_processed(self, event_id: str):
        for e in self.events:
            if e.id == event_id:
                e.processed = True
                break

    # ── Constraint Management ──────────────────────────────────────────────

    def add_constraint(self, type: str, target: str, value: Any) -> Constraint:
        constraint = Constraint(
            id=str(uuid.uuid4()),
            type=type,
            target=target,
            value=value,
        )
        self.constraints[constraint.id] = constraint
        return constraint

    def check_constraint(self, constraint_id: str, current_value: Any) -> bool:
        constraint = self.constraints.get(constraint_id)
        if not constraint or not constraint.enforced:
            return True
        if isinstance(constraint.value, (int, float)) and isinstance(current_value, (int, float)):
            if current_value > constraint.value:
                constraint.violation_count += 1
                return False
        elif current_value != constraint.value:
            constraint.violation_count += 1
            return False
        return True

    # ── Permission Management ──────────────────────────────────────────────

    def add_permission(self, resource_id: str, action: str, granted: bool,
                       scope: str = "", expires_at: float | None = None) -> Permission:
        perm = Permission(
            id=str(uuid.uuid4()),
            resource_id=resource_id,
            action=action,
            granted=granted,
            scope=scope,
            expires_at=expires_at,
        )
        self.permissions[perm.id] = perm
        return perm

    def check_permission(self, resource_id: str, action: str) -> bool:
        for perm in self.permissions.values():
            if perm.resource_id == resource_id and perm.action == action:
                if perm.expires_at and time.time() > perm.expires_at:
                    return False
                return perm.granted
        return False  # Default deny

    # ── Query & Summary ────────────────────────────────────────────────────

    def query(self, query: str) -> dict[str, Any]:
        query_lower = query.lower()
        return {
            "entities": [e for e in self.entities.values()
                         if query_lower in e.name.lower() or query_lower in e.type.value],
            "resources": [r for r in self.resources.values()
                          if query_lower in r.type.lower()],
            "events": [e for e in self.events[-20:]
                       if query_lower in str(e.payload).lower()],
        }

    def get_state(self) -> dict[str, Any]:
        return {
            "entities_count": len(self.entities),
            "resources_count": len(self.resources),
            "relationships_count": len(self.relationships),
            "events_count": len(self.events),
            "constraints_count": len(self.constraints),
            "permissions_count": len(self.permissions),
            "unprocessed_events": len(self.get_unprocessed_events()),
        }

    def get_critical_resources(self, threshold: float = 0.7) -> list[Resource]:
        return [r for r in self.resources.values() if r.criticality >= threshold]
