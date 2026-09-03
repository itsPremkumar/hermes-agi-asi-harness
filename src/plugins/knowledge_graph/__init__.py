"""
knowledge_graph.py — Dynamic Knowledge Graph with Entity-Relation Tracking

Implements a causal graph and entity store for tracking relationships between
concepts, sources, and findings across research sessions and multi-agent coordination.
"""

import json
import pathlib
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class RelationType(str, Enum):
    CAUSES = "causes"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"
    PART_OF = "part_of"
    INSTANCE_OF = "instance_of"
    ASSOCIATED_WITH = "associated_with"


@dataclass
class KGEntity:
    id: str
    name: str
    entity_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)


@dataclass
class KGRelation:
    source_id: str
    target_id: str
    relation_type: RelationType
    strength: float = 1.0
    evidence: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class KnowledgeGraph:
    """
    Dynamic knowledge graph for tracking entities, relations, and causal links.
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
        self._init_db()

    def _init_db(self):
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    entity_type TEXT,
                    properties_json TEXT,
                    created_at REAL,
                    last_updated REAL
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT,
                    target_id TEXT,
                    relation_type TEXT,
                    strength REAL,
                    evidence_json TEXT,
                    created_at REAL
                )
            """)
            try:
                self._conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                        id UNINDEXED,
                        name,
                        entity_type,
                        properties
                    )
                """)
                self._has_fts = True
            except Exception:
                self._has_fts = False

    def add_entity(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        properties: dict[str, Any] | None = None,
    ) -> KGEntity:
        """Adds or updates an entity."""
        now = time.time()
        props = properties or {}
        with self._conn:
            self._conn.execute("""
                INSERT OR REPLACE INTO entities
                (id, name, entity_type, properties_json, created_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entity_id, name, entity_type,
                json.dumps(props),
                now if entity_id not in self._get_entity_ids() else self._get_created_at(entity_id),
                now,
            ))
        if self._has_fts:
            try:
                self._conn.execute("DELETE FROM entities_fts WHERE id = ?", (entity_id,))
                self._conn.execute("""
                    INSERT INTO entities_fts (id, name, entity_type, properties)
                    VALUES (?, ?, ?, ?)
                """, (entity_id, name, entity_type, json.dumps(props)))
            except Exception:
                pass
        return KGEntity(id=entity_id, name=name, entity_type=entity_type, properties=props)

    def _get_entity_ids(self) -> set[str]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT id FROM entities")
        return {row[0] for row in cursor.fetchall()}

    def _get_created_at(self, entity_id: str) -> float:
        cursor = self._conn.cursor()
        cursor.execute("SELECT created_at FROM entities WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        return row[0] if row else time.time()

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 1.0,
        evidence: list[str] | None = None,
    ):
        """Adds a relation between two entities."""
        with self._conn:
            self._conn.execute("""
                INSERT INTO relations
                (source_id, target_id, relation_type, strength, evidence_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                source_id, target_id,
                relation_type.value,
                strength,
                json.dumps(evidence or []),
                time.time(),
            ))

    def get_entity(self, entity_id: str) -> KGEntity | None:
        """Retrieves an entity by ID."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT id, name, entity_type, properties_json, created_at, last_updated FROM entities WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        if row:
            return KGEntity(
                id=row[0], name=row[1], entity_type=row[2],
                properties=json.loads(row[3]) if row[3] else {},
                created_at=row[4], last_updated=row[5],
            )
        return None

    def search_entities(self, query: str, limit: int = 20) -> list[KGEntity]:
        """Searches entities by name, type, or properties."""
        cursor = self._conn.cursor()
        if self._has_fts:
            try:
                clean_q = query.replace("'", " ").replace('"', " ").strip()
                if clean_q:
                    cursor.execute("""
                        SELECT e.id, e.name, e.entity_type, e.properties_json,
                               e.created_at, e.last_updated
                        FROM entities_fts f
                        JOIN entities e ON f.id = e.id
                        WHERE entities_fts MATCH ?
                        ORDER BY rank LIMIT ?
                    """, (clean_q, limit))
                else:
                    cursor.execute("SELECT * FROM entities LIMIT ?", (limit,))
            except Exception:
                cursor.execute("""
                    SELECT id, name, entity_type, properties_json, created_at, last_updated
                    FROM entities
                    WHERE name LIKE ? OR entity_type LIKE ?
                    ORDER BY last_updated DESC LIMIT ?
                """, (f"%{query}%", f"%{query}%", limit))
        else:
            cursor.execute("""
                SELECT id, name, entity_type, properties_json, created_at, last_updated
                FROM entities
                WHERE name LIKE ? OR entity_type LIKE ?
                ORDER BY last_updated DESC LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))

        rows = cursor.fetchall()
        return [
            KGEntity(
                id=row[0], name=row[1], entity_type=row[2],
                properties=json.loads(row[3]) if row[3] else {},
                created_at=row[4], last_updated=row[5],
            )
            for row in rows
        ]

    def get_relations(self, entity_id: str, direction: str = "both") -> list[tuple[KGEntity, KGRelation]]:
        """Gets all relations for an entity."""
        cursor = self._conn.cursor()
        if direction in ("outgoing", "both"):
            cursor.execute("""
                SELECT r.source_id, r.target_id, r.relation_type, r.strength, r.evidence_json,
                       e.name, e.entity_type, e.properties_json, e.created_at, e.last_updated
                FROM relations r
                JOIN entities e ON e.id = r.target_id
                WHERE r.source_id = ?
            """, (entity_id,))
        else:
            cursor.execute("""
                SELECT r.source_id, r.target_id, r.relation_type, r.strength, r.evidence_json,
                       e.name, e.entity_type, e.properties_json, e.created_at, e.last_updated
                FROM relations r
                JOIN entities e ON e.id = r.source_id
                WHERE r.target_id = ?
            """, (entity_id,))

        results = []
        for row in cursor.fetchall():
            entity = KGEntity(
                id=row[8] if direction != "outgoing" else row[1],
                name=row[5], entity_type=row[6],
                properties=json.loads(row[7]) if row[7] else {},
                created_at=row[8], last_updated=row[9],
            ) if direction != "outgoing" else KGEntity(
                id=row[1], name=row[5], entity_type=row[6],
                properties=json.loads(row[7]) if row[7] else {},
                created_at=row[8], last_updated=row[9],
            )
            relation = KGRelation(
                source_id=entity_id,
                target_id=row[1],
                relation_type=RelationType(row[2]),
                strength=row[3],
                evidence=json.loads(row[4]) if row[4] else [],
            )
            results.append((entity, relation))
        return results

    def get_summary(self) -> dict[str, Any]:
        """Returns summary statistics."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM relations")
        relation_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT entity_type) FROM entities")
        type_count = cursor.fetchone()[0]

        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "entity_type_count": type_count,
            "has_fts": self._has_fts,
        }

    def close(self):
        self._conn.close()


async def create(kernel=None) -> KnowledgeGraph:
    """Factory function for kernel integration."""
    kg = KnowledgeGraph()
    return kg
