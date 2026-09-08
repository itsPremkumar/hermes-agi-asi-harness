#!/usr/bin/env python3
"""
hybrid_memory.py — 9-Type Cognitive Hybrid Memory Store with SQLite FTS5 Search
Implements Working, Episodic, Semantic, Failure, Procedural, Context, Entity, Causal, and Self-Model memory.
"""

import time
import json
import sqlite3
import pathlib
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    FAILURE = "failure"
    PROCEDURAL = "procedural"
    CONTEXT = "context"
    ENTITY = "entity"
    CAUSAL = "causal"
    SELF_MODEL = "self_model"

@dataclass
class MemoryEntry:
    id: str
    memory_type: MemoryType
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

class HybridMemoryStore:
    def __init__(self, db_path: Optional[str] = None):
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
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT,
                    title TEXT,
                    content TEXT,
                    tags_json TEXT,
                    confidence REAL,
                    created_at REAL,
                    metadata_json TEXT
                )
            """)
            try:
                self._conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                        id UNINDEXED,
                        title,
                        content,
                        tags
                    )
                """)
                self._has_fts = True
            except Exception:
                self._has_fts = False

    def store(self, entry: MemoryEntry):
        with self._conn:
            self._conn.execute("""
                INSERT OR REPLACE INTO memories
                (id, memory_type, title, content, tags_json, confidence, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.memory_type.value,
                entry.title,
                entry.content,
                json.dumps(entry.tags),
                entry.confidence,
                entry.created_at,
                json.dumps(entry.metadata)
            ))
            if self._has_fts:
                try:
                    self._conn.execute("DELETE FROM memories_fts WHERE id = ?", (entry.id,))
                    self._conn.execute("""
                        INSERT INTO memories_fts (id, title, content, tags)
                        VALUES (?, ?, ?, ?)
                    """, (entry.id, entry.title, entry.content, " ".join(entry.tags)))
                except Exception:
                    pass

    def remember(
        self,
        memory_type: MemoryType,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """Convenience method to create and persist a new memory entry."""
        entry_id = f"mem_{int(time.time() * 1000)}_{abs(hash(title)) % 10000}"
        entry = MemoryEntry(
            id=entry_id,
            memory_type=memory_type,
            title=title,
            content=content,
            tags=tags or [],
            confidence=confidence,
            metadata=metadata or {}
        )
        self.store(entry)
        return entry

    def retrieve_by_type(self, memory_type: MemoryType, limit: int = 50) -> List[MemoryEntry]:
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT id, memory_type, title, content, tags_json, confidence, created_at, metadata_json
            FROM memories WHERE memory_type = ? ORDER BY created_at DESC LIMIT ?
        """, (memory_type.value, limit))
        rows = cursor.fetchall()
        return [self._row_to_entry(r) for r in rows]

    def search(self, query: str, memory_type: Optional[MemoryType] = None, limit: int = 10) -> List[MemoryEntry]:
        """Hybrid search: uses FTS5 text matching when available, falls back to SQL LIKE."""
        cursor = self._conn.cursor()
        results = []

        if self._has_fts:
            try:
                clean_q = query.replace("'", " ").replace('"', " ").strip()
                if clean_q:
                    cursor.execute("""
                        SELECT m.id, m.memory_type, m.title, m.content, m.tags_json, m.confidence, m.created_at, m.metadata_json
                        FROM memories_fts f
                        JOIN memories m ON f.id = m.id
                        WHERE memories_fts MATCH ?
                        ORDER BY rank LIMIT ?
                    """, (clean_q, limit))
                    results = cursor.fetchall()
            except Exception:
                pass

        if not results:
            pattern = f"%{query}%"
            if memory_type:
                cursor.execute("""
                    SELECT id, memory_type, title, content, tags_json, confidence, created_at, metadata_json
                    FROM memories
                    WHERE (title LIKE ? OR content LIKE ?) AND memory_type = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (pattern, pattern, memory_type.value, limit))
            else:
                cursor.execute("""
                    SELECT id, memory_type, title, content, tags_json, confidence, created_at, metadata_json
                    FROM memories
                    WHERE title LIKE ? OR content LIKE ?
                    ORDER BY created_at DESC LIMIT ?
                """, (pattern, pattern, limit))
            results = cursor.fetchall()

        entries = [self._row_to_entry(r) for r in results]
        if memory_type:
            entries = [e for e in entries if e.memory_type == memory_type]
        return entries[:limit]

    def _row_to_entry(self, row: tuple) -> MemoryEntry:
        return MemoryEntry(
            id=row[0],
            memory_type=MemoryType(row[1]),
            title=row[2],
            content=row[3],
            tags=json.loads(row[4]) if row[4] else [],
            confidence=row[5],
            created_at=row[6],
            metadata=json.loads(row[7]) if row[7] else {}
        )

    def close(self):
        self._conn.close()
