#!/usr/bin/env python3
"""
Memory Curator Plugin — Intelligent memory management with FTS5
============================================================
Features:
- Store memories with embeddings (TF-IDF based)
- Semantic search across memory
- Memory consolidation and deduplication
- Importance scoring and decay
- Hierarchical memory organization
- Cross-session persistence
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_memory_curator")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum
    
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: List[str] = field(default_factory=list)
        shell_commands: List[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: List[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: List[str] = field(default_factory=list)
        path: Optional[Path] = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


@dataclass
class Memory:
    """A memory entry."""
    id: str
    content: str
    category: str
    importance: float
    created_at: str
    last_accessed: str
    access_count: int
    embedding: List[float]
    tags: List[str] = field(default_factory=list)
    decay_rate: float = 0.01


class SimpleEmbedder:
    """TF-IDF based embedder for memory."""
    
    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
    
    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b[a-z0-9_]+\b', text.lower())
    
    def fit(self, documents: List[str]):
        """Fit on corpus."""
        doc_freq: Dict[str, int] = {}
        for doc in documents:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1
        
        self.vocab = {t: i for i, t in enumerate(sorted(doc_freq.keys()))}
        for token, freq in doc_freq.items():
            self.idf[token] = math.log((len(documents) + 1) / (freq + 1)) + 1
    
    def embed(self, text: str) -> List[float]:
        """Embed text."""
        if not self.vocab:
            return []
        
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * len(self.vocab)
        
        token_counts = {}
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1
        
        vector = [0.0] * len(self.vocab)
        for token, count in token_counts.items():
            if token in self.vocab:
                idx = self.vocab[token]
                tf = count / len(tokens)
                vector[idx] = tf * self.idf.get(token, 0)
        
        # Normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    def similarity(self, a: List[float], b: List[float]) -> float:
        """Cosine similarity."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class MemoryCurator:
    """Intelligent memory management."""
    
    def __init__(self, db_path: str = ".hermes/memory.db"):
        self.db_path = Path(db_path)
        self.embedder = SimpleEmbedder()
        self.memories: Dict[str, Memory] = {}
        self._loaded = False
    
    def load(self):
        """Load memories from SQLite."""
        if self._loaded:
            return
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT,
                category TEXT,
                importance REAL,
                created_at TEXT,
                last_accessed TEXT,
                access_count INTEGER,
                embedding TEXT,
                tags TEXT,
                decay_rate REAL
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, tags)
        """)
        conn.commit()
        
        cursor = conn.execute("SELECT * FROM memories")
        documents = []
        for row in cursor:
            embedding = json.loads(row[7]) if row[7] else []
            memory = Memory(
                id=row[0],
                content=row[1],
                category=row[2],
                importance=row[3],
                created_at=row[4],
                last_accessed=row[5],
                access_count=row[6],
                embedding=embedding,
                tags=json.loads(row[8]) if row[8] else [],
                decay_rate=row[9],
            )
            self.memories[memory.id] = memory
            documents.append(memory.content)
        
        if documents:
            self.embedder.fit(documents)
            # Re-embed if needed
            for memory in self.memories.values():
                if not memory.embedding:
                    memory.embedding = self.embedder.embed(memory.content)
        
        conn.close()
        self._loaded = True
    
    def save(self):
        """Save memories to SQLite."""
        conn = sqlite3.connect(str(self.db_path))
        
        for memory in self.memories.values():
            conn.execute("""
                INSERT OR REPLACE INTO memories 
                (id, content, category, importance, created_at, last_accessed, access_count, embedding, tags, decay_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id, memory.content, memory.category, memory.importance,
                memory.created_at, memory.last_accessed, memory.access_count,
                json.dumps(memory.embedding), json.dumps(memory.tags), memory.decay_rate
            ))
            
            # Update FTS
            conn.execute("DELETE FROM memories_fts WHERE rowid = (SELECT rowid FROM memories WHERE id = ?)", (memory.id,))
            conn.execute("INSERT INTO memories_fts (rowid, content, tags) SELECT rowid, ?, ? FROM memories WHERE id = ?",
                        (memory.content, " ".join(memory.tags), memory.id))
        
        conn.commit()
        conn.close()
    
    def add_memory(self, content: str, category: str = "general", 
                   importance: float = 0.5, tags: List[str] = None) -> str:
        """Add a memory."""
        memory_id = f"mem_{hashlib.md5(content.encode()).hexdigest()[:12]}"
        
        if not self.embedder.vocab and self.memories:
            # Fit if not fitted
            self.embedder.fit([m.content for m in self.memories.values()] + [content])
        
        embedding = self.embedder.embed(content)
        
        memory = Memory(
            id=memory_id,
            content=content,
            category=category,
            importance=importance,
            created_at=datetime.utcnow().isoformat(),
            last_accessed=datetime.utcnow().isoformat(),
            access_count=0,
            embedding=embedding,
            tags=tags or [],
        )
        
        self.memories[memory_id] = memory
        return memory_id
    
    def search(self, query: str, top_k: int = 5, category: str = None) -> List[Dict[str, Any]]:
        """Search memories."""
        if not self.memories:
            return []
        
        query_embedding = self.embedder.embed(query)
        
        results = []
        for memory in self.memories.values():
            if category and memory.category != category:
                continue
            
            # Semantic similarity
            semantic_score = self.embedder.similarity(query_embedding, memory.embedding)
            
            # Keyword match via FTS
            keyword_score = 0.0
            query_tokens = set(self.embedder._tokenize(query))
            memory_tokens = set(self.embedder._tokenize(memory.content))
            overlap = len(query_tokens.intersection(memory_tokens))
            keyword_score = overlap / max(len(query_tokens), 1)
            
            # Combined score with importance and recency
            combined = (semantic_score * 0.5 + keyword_score * 0.3 + memory.importance * 0.2)
            
            results.append((combined, memory))
        
        results.sort(key=lambda x: x[0], reverse=True)
        
        return [
            {
                "id": m.id,
                "content": m.content,
                "category": m.category,
                "importance": m.importance,
                "score": score,
                "tags": m.tags,
                "created_at": m.created_at,
            }
            for score, m in results[:top_k]
        ]
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID."""
        memory = self.memories.get(memory_id)
        if memory:
            memory.last_accessed = datetime.utcnow().isoformat()
            memory.access_count += 1
        return memory
    
    def consolidate(self) -> Dict[str, Any]:
        """Consolidate memories: deduplicate and apply decay."""
        # Deduplicate by content hash
        seen_hashes = set()
        duplicates = []
        for memory in list(self.memories.values()):
            content_hash = hashlib.md5(memory.content.encode()).hexdigest()
            if content_hash in seen_hashes:
                duplicates.append(memory.id)
            else:
                seen_hashes.add(content_hash)
        
        for dup_id in duplicates:
            del self.memories[dup_id]
        
        # Apply decay to importance
        now = datetime.utcnow()
        decayed = 0
        for memory in self.memories.values():
            created = datetime.fromisoformat(memory.created_at)
            age_days = (now - created).days
            decay_factor = math.exp(-memory.decay_rate * age_days)
            old_importance = memory.importance
            memory.importance = memory.importance * decay_factor
            if memory.importance < 0.05:
                # Remove very low importance memories
                del self.memories[memory.id]
                decayed += 1
        
        return {
            "duplicates_removed": len(duplicates),
            "low_importance_removed": decayed,
            "remaining": len(self.memories),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory stats."""
        categories: Dict[str, int] = {}
        for memory in self.memories.values():
            categories[memory.category] = categories.get(memory.category, 0) + 1
        
        return {
            "total_memories": len(self.memories),
            "categories": categories,
            "vocab_size": len(self.embedder.vocab),
        }


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Memory Curator Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="memory_curator",
            version="1.0.0",
            description="Intelligent memory management with TF-IDF embeddings, semantic search, consolidation, and decay",
            license="MIT",
            source="internal",
            capabilities=["memory_store", "memory_search", "memory_consolidation", "importance_scoring"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=20,
            ),
        )
        self.curator: Optional[MemoryCurator] = None
    
    async def load(self) -> bool:
        self.curator = MemoryCurator()
        self.curator.load()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.curator:
            self.curator = MemoryCurator()
            self.curator.load()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        if self.curator:
            self.curator.save()
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> Dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.curator is not None,
            "memories": len(self.curator.memories) if self.curator else 0,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def add_memory(self, content: str, category: str = "general", importance: float = 0.5, tags: List[str] = None) -> str:
        return self.curator.add_memory(content, category, importance, tags)
    
    def search(self, query: str, top_k: int = 5, category: str = None) -> List[Dict[str, Any]]:
        return self.curator.search(query, top_k, category)
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        memory = self.curator.get_memory(memory_id)
        if memory:
            return {
                "id": memory.id,
                "content": memory.content,
                "category": memory.category,
                "importance": memory.importance,
                "tags": memory.tags,
                "created_at": memory.created_at,
            }
        return None
    
    def consolidate(self) -> Dict[str, Any]:
        return self.curator.consolidate()
    
    def get_stats(self) -> Dict[str, Any]:
        return self.curator.get_stats()
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
