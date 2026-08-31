"""Memory Layer — short-term + long-term memory with LangChain-style embeddings."""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..errors import MemoryError

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry."""

    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    importance: float = 1.0
    entry_id: str = field(default_factory=lambda: hashlib.md5(str(time.time()).encode()).hexdigest()[:12])


class EmbeddingModel:
    """Simple embedding model interface."""

    def __init__(self, dimension: int = 64) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        """Simple deterministic embedding based on character codes."""
        import random
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        return [rng.random() for _ in range(self.dimension)]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class ShortTermMemory:
    """Short-term (working) memory."""

    def __init__(self, max_entries: int = 50) -> None:
        self.max_entries = max_entries
        self._entries: list[MemoryEntry] = []
        self._lock = threading.Lock()

    def add(self, content: str, **metadata: Any) -> MemoryEntry:
        entry = MemoryEntry(content=content, metadata=metadata)
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries:]
        return entry

    def recall(self, n: int = 10) -> list[MemoryEntry]:
        with self._lock:
            return list(self._entries[-n:])

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    @property
    def size(self) -> int:
        return len(self._entries)


class LongTermMemory:
    """Long-term memory with embedding-based retrieval."""

    def __init__(self, embedding_model: EmbeddingModel | None = None, max_entries: int = 1000) -> None:
        self.embedding_model = embedding_model or EmbeddingModel()
        self.max_entries = max_entries
        self._entries: list[MemoryEntry] = []
        self._lock = threading.Lock()

    def store(self, content: str, importance: float = 1.0, **metadata: Any) -> MemoryEntry:
        embedding = self.embedding_model.embed(content)
        entry = MemoryEntry(content=content, embedding=embedding, importance=importance, metadata=metadata)
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self.max_entries:
                self._entries = sorted(self._entries, key=lambda e: e.importance, reverse=True)[:self.max_entries]
        return entry

    def retrieve(self, query: str, top_k: int = 5) -> list[tuple[MemoryEntry, float]]:
        query_embedding = self.embedding_model.embed(query)
        with self._lock:
            scored = []
            for entry in self._entries:
                if entry.embedding:
                    sim = EmbeddingModel.cosine_similarity(query_embedding, entry.embedding)
                    scored.append((entry, sim))
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    @property
    def size(self) -> int:
        return len(self._entries)


class MemoryLayer:
    """Combined short-term and long-term memory."""

    def __init__(
        self,
        short_term_size: int = 50,
        long_term_size: int = 1000,
        embedding_dimension: int = 64,
    ) -> None:
        self.embedding_model = EmbeddingModel(dimension=embedding_dimension)
        self.short_term = ShortTermMemory(max_entries=short_term_size)
        self.long_term = LongTermMemory(embedding_model=self.embedding_model, max_entries=long_term_size)

    def remember(self, content: str, importance: float = 1.0, long_term: bool = True, **metadata: Any) -> MemoryEntry:
        self.short_term.add(content, **metadata)
        if long_term:
            return self.long_term.store(content, importance=importance, **metadata)
        return MemoryEntry(content=content, metadata=metadata)

    def recall_recent(self, n: int = 10) -> list[MemoryEntry]:
        return self.short_term.recall(n)

    def recall_relevant(self, query: str, top_k: int = 5) -> list[tuple[MemoryEntry, float]]:
        return self.long_term.retrieve(query, top_k)

    def consolidate(self) -> int:
        """Move important short-term memories to long-term."""
        important = [e for e in self.short_term.recall() if e.importance >= 0.7]
        for entry in important:
            self.long_term.store(entry.content, importance=entry.importance, **entry.metadata)
        return len(important)

    def clear_all(self) -> None:
        self.short_term.clear()
        self.long_term.clear()
