"""
world_model.py — Dynamic Causal Graph & World State Representation

Tracks entities, relations, and predictive causal branches in the agent environment.
"""

import json
import logging
import pathlib
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    id: str
    entity_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)


@dataclass
class CausalRelation:
    cause: str
    effect: str
    strength: float = 1.0
    evidence_count: int = 1
    description: str = ""


class WorldModel:
    """
    Dynamic causal graph and world state representation.
    Uses SQLite for persistence with FTS5 full-text search.
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            self.db_path = ":memory:"
        else:
            p = pathlib.Path(db_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(p)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._has_fts = False
        self.entities: dict[str, Entity] = {}
        self.causal_graph: dict[str, list[CausalRelation]] = {}
        self._init_db()

    def _init_db(self):
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT,
                    properties_json TEXT,
                    last_updated REAL
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS causal_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cause TEXT,
                    effect TEXT,
                    strength REAL,
                    evidence_count INTEGER,
                    description TEXT
                )
            """)
            try:
                self._conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                        id UNINDEXED,
                        entity_type,
                        properties
                    )
                """)
                self._has_fts = True
            except Exception:
                self._has_fts = False

    def upsert_entity(self, entity_id: str, entity_type: str, properties: dict[str, Any]) -> Entity:
        """Adds or updates an entity."""
        if entity_id in self.entities:
            ent = self.entities[entity_id]
            ent.properties.update(properties)
            ent.last_updated = time.time()
        else:
            ent = Entity(id=entity_id, entity_type=entity_type, properties=properties)
            self.entities[entity_id] = ent

        with self._conn:
            self._conn.execute("""
                INSERT OR REPLACE INTO entities (id, entity_type, properties_json, last_updated)
                VALUES (?, ?, ?, ?)
            """, (entity_id, entity_type, json.dumps(properties), time.time()))
        return ent

    def add_causal_link(self, cause: str, effect: str, strength: float = 1.0, description: str = ""):
        """Adds a causal link to the graph."""
        if cause not in self.causal_graph:
            self.causal_graph[cause] = []

        for rel in self.causal_graph[cause]:
            if rel.effect == effect:
                rel.evidence_count += 1
                rel.strength = (rel.strength * (rel.evidence_count - 1) + strength) / rel.evidence_count
                return rel

        new_rel = CausalRelation(cause=cause, effect=effect, strength=strength, description=description)
        self.causal_graph[cause].append(new_rel)

        with self._conn:
            self._conn.execute("""
                INSERT INTO causal_relations (cause, effect, strength, evidence_count, description)
                VALUES (?, ?, ?, ?, ?)
            """, (cause, effect, strength, 1, description))
        return new_rel

    def predict_effects(self, action_or_event: str, min_strength: float = 0.5) -> list[CausalRelation]:
        """Predicts probable downstream effects of a given action or event."""
        relations = self.causal_graph.get(action_or_event, [])
        return [r for r in relations if r.strength >= min_strength]

    def get_world_summary(self) -> dict[str, Any]:
        """Returns a summary of the world model."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM causal_relations")
        relation_count = cursor.fetchone()[0]

        return {
            "entity_count": entity_count,
            "causal_link_count": relation_count,
            "entities": {eid: e.properties for eid, e in self.entities.items()},
            "causal_graph_depth": max(len(v) for v in self.causal_graph.values()) if self.causal_graph else 0,
        }

    def close(self):
        self._conn.close()


class WorldModelPlugin:
    """Plugin wrapper for WorldModel."""

    def __init__(self, kernel=None):
        self.state = "started"
        self.kernel = kernel
        self.world_model = WorldModel()
        self.manifest = type('Manifest', (), {'name': 'world_model', 'version': '1.0.0'})()

    async def load(self):
        return True

    async def start(self):
        return True

    async def stop(self):
        self.world_model.close()
        return True

    async def health(self):
        summary = self.world_model.get_world_summary()
        return {
            "status": "healthy",
            "plugin": "world_model",
            "version": "1.0.0",
            "state": self.state,
            "healthy": True,
            "entities": summary["entity_count"],
            "causal_links": summary["causal_link_count"],
        }

    def get_capabilities(self):
        return ["world_model", "causal_graph", "entity_tracking"]

    # WorldModel passthrough methods
    def upsert_entity(self, *args, **kwargs):
        return self.world_model.upsert_entity(*args, **kwargs)

    def add_causal_link(self, *args, **kwargs):
        return self.world_model.add_causal_link(*args, **kwargs)

    def predict_effects(self, *args, **kwargs):
        return self.world_model.predict_effects(*args, **kwargs)

    def get_world_summary(self):
        return self.world_model.get_world_summary()


async def create(kernel=None) -> WorldModelPlugin:
    """Factory function for kernel integration."""
    plugin = WorldModelPlugin(kernel)
    await plugin.load()
    await plugin.start()
    return plugin
