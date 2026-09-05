
"""
Hybrid Memory — 9-Type Cognitive Memory Store with SQLite FTS5 Search.

Extracted & enhanced from agi-hermes-advanced-master:
- hybrid_memory.py: 9-type memory (working, episodic, semantic, failure, procedural, context, entity, causal, self_model)

Memory types map to cognitive science:
- Working: current context window
- Episodic: past experiences with timestamps
- Semantic: general knowledge
- Procedural: how-to knowledge
- Failure: failure lessons
- Context: project-specific
- Entity: people/things
- Causal: cause-effect relationships
- Self-model: agent identity
"""

import json
import logging
import pathlib
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


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
    tags: list[str] = field(default_factory=list)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class HybridMemoryStore:
    """
    9-type cognitive memory store with FTS5 full-text search.
    
    Features:
    - 9 memory types (cognitive science inspired)
    - FTS5 full-text search with fallback to SQL LIKE
    - Confidence scoring
    - Tag-based organization
    - Metadata support
    - Thread-safe operations
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
        """Initialize database schema."""
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
                    updated_at REAL,
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
        """Store a memory entry."""
        with self._conn:
            self._conn.execute("""
                INSERT OR REPLACE INTO memories
                (id, memory_type, title, content, tags_json, confidence, created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.memory_type.value,
                entry.title,
                entry.content,
                json.dumps(entry.tags),
                entry.confidence,
                entry.created_at,
                entry.updated_at,
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
        tags: list[str] | None = None,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None
    ) -> MemoryEntry:
        """Create and persist a new memory entry."""
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
    
    def retrieve_by_type(self, memory_type: MemoryType, limit: int = 50) -> list[MemoryEntry]:
        """Retrieve memories by type."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT id, memory_type, title, content, tags_json, confidence, created_at, updated_at, metadata_json
            FROM memories WHERE memory_type = ? ORDER BY created_at DESC LIMIT ?
        """, (memory_type.value, limit))
        rows = cursor.fetchall()
        return [self._row_to_entry(r) for r in rows]
    
    def search(self, query: str, memory_type: MemoryType | None = None, limit: int = 10) -> list[MemoryEntry]:
        """Hybrid search: FTS5 when available, SQL LIKE fallback."""
        cursor = self._conn.cursor()
        results = []
        
        if self._has_fts:
            try:
                clean_q = query.replace("'", " ").replace('"', " ").strip()
                if clean_q:
                    cursor.execute("""
                        SELECT m.id, m.memory_type, m.title, m.content, m.tags_json, m.confidence, m.created_at, m.updated_at, m.metadata_json
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
                    SELECT id, memory_type, title, content, tags_json, confidence, created_at, updated_at, metadata_json
                    FROM memories
                    WHERE (title LIKE ? OR content LIKE ?) AND memory_type = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (pattern, pattern, memory_type.value, limit))
            else:
                cursor.execute("""
                    SELECT id, memory_type, title, content, tags_json, confidence, created_at, updated_at, metadata_json
                    FROM memories
                    WHERE title LIKE ? OR content LIKE ?
                    ORDER BY created_at DESC LIMIT ?
                """, (pattern, pattern, limit))
            results = cursor.fetchall()
        
        entries = [self._row_to_entry(r) for r in results]
        if memory_type:
            entries = [e for e in entries if e.memory_type == memory_type]
        return entries[:limit]
    
    def get_by_id(self, memory_id: str) -> MemoryEntry | None:
        """Get a memory by ID."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT id, memory_type, title, content, tags_json, confidence, created_at, updated_at, metadata_json
            FROM memories WHERE id = ?
        """, (memory_id,))
        row = cursor.fetchone()
        return self._row_to_entry(row) if row else None
    
    def update(self, memory_id: str, **kwargs):
        """Update a memory entry."""
        entry = self.get_by_id(memory_id)
        if not entry:
            return
        
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = time.time()
        self.store(entry)
    
    def delete(self, memory_id: str):
        """Delete a memory entry."""
        with self._conn:
            self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            if self._has_fts:
                self._conn.execute("DELETE FROM memories_fts WHERE id = ?", (memory_id,))
    
    def count_by_type(self) -> dict[str, int]:
        """Count memories by type."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type")
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def _row_to_entry(self, row: tuple) -> MemoryEntry:
        return MemoryEntry(
            id=row[0],
            memory_type=MemoryType(row[1]),
            title=row[2],
            content=row[3],
            tags=json.loads(row[4]) if row[4] else [],
            confidence=row[5],
            created_at=row[6],
            updated_at=row[7],
            metadata=json.loads(row[8]) if row[8] else {}
        )
    
    def close(self):
        self._conn.close()


# Plugin wrapper for the memory system
class HybridMemoryPlugin:
    """Plugin wrapper for HybridMemoryStore."""
    
    def __init__(self, db_path: str | None = None):
        self.store = HybridMemoryStore(db_path)
        self.manifest = None
    
    async def load(self) -> bool:
        return True
    
    async def start(self) -> bool:
        logger.info("Hybrid memory plugin started")
        return True
    
    async def stop(self) -> bool:
        self.store.close()
        return True
    
    async def health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "type": "hybrid_memory",
            "counts": self.store.count_by_type()
        }


async def create(kernel: Any) -> HybridMemoryPlugin:
    """Factory function."""
    db_path = None
    if kernel and hasattr(kernel, 'config'):
        db_path = str(kernel.config.state_path / "memory.db")
    return HybridMemoryPlugin(db_path=db_path)
