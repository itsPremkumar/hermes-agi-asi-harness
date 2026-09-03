"""Persistent Memory System with consolidation and experience replay.

Carries state across context windows and sessions.
Supports: episodic, semantic, procedural, strategic memory types.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List


class MemoryType(str, Enum):
    EPISODIC = "episodic"       # What happened
    SEMANTIC = "semantic"       # What we know
    PROCEDURAL = "procedural"   # How to do things
    STRATEGIC = "strategic"     # Why and what next
    FAILURE = "failure"         # What went wrong
    SKILL = "skill"             # Reusable procedures


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: MemoryType = MemoryType.SEMANTIC
    key: str = ""
    value: Any = None
    importance: float = 1.0
    confidence: float = 1.0
    source: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    accessed_at: float = 0.0
    access_count: int = 0
    related: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Mark as accessed."""
        self.accessed_at = time.time()
        self.access_count += 1


@dataclass
class Experience:
    """A learning experience (for replay)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    context: str = ""
    action: str = ""
    outcome: str = ""
    score: float = 0.0
    lesson: str = ""
    created_at: float = field(default_factory=time.time)
    replay_count: int = 0
    verified: bool = False


class PersistentMemory:
    """Persistent memory with consolidation and experience replay."""

    def __init__(
        self,
        data_dir: Path | None = None,
        max_entries: int = 10000,
        consolidation_threshold: int = 1000,
    ):
        self._data_dir = data_dir or Path.home() / ".hermes" / "supervisor" / "memory"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._entries: Dict[str, MemoryEntry] = {}
        self._experiences: List[Experience] = []
        self._max_entries = max_entries
        self._consolidation_threshold = consolidation_threshold

    # --- Core operations ---

    def store(
        self,
        key: str,
        value: Any,
        mem_type: MemoryType = MemoryType.SEMANTIC,
        importance: float = 1.0,
        confidence: float = 1.0,
        source: str = "",
        tags: List[str] | None = None,
        related: List[str] | None = None,
    ) -> MemoryEntry:
        """Store a memory entry."""
        entry = MemoryEntry(
            type=mem_type,
            key=key,
            value=value,
            importance=importance,
            confidence=confidence,
            source=source,
            tags=tags or [],
            related=related or [],
        )
        self._entries[entry.id] = entry
        self._maybe_consolidate()
        return entry

    def retrieve(self, key: str) -> MemoryEntry | None:
        """Retrieve a memory entry by key."""
        for entry in self._entries.values():
            if entry.key == key:
                entry.touch()
                return entry
        return None

    def search(
        self,
        query: str,
        mem_type: MemoryType | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> List[MemoryEntry]:
        """Search memory entries by query."""
        results = []
        query_lower = query.lower()

        for entry in self._entries.values():
            if mem_type and entry.type != mem_type:
                continue
            if entry.importance < min_importance:
                continue

            # Score by relevance
            score = 0.0
            if query_lower in entry.key.lower():
                score += 3.0
            if query_lower in str(entry.value).lower():
                score += 2.0
            if any(query_lower in tag.lower() for tag in entry.tags):
                score += 2.0
            if query_lower in entry.source.lower():
                score += 1.0

            if score > 0:
                entry.touch()
                results.append((score, entry))

        # Sort by score (descending), then importance
        results.sort(key=lambda x: (x[0], x[1].importance), reverse=True)
        return [entry for _, entry in results[:limit]]

    def update(self, entry_id: str, **kwargs) -> MemoryEntry | None:
        """Update a memory entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            return None
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        return entry

    def forget(self, entry_id: str) -> bool:
        """Remove a memory entry."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    # --- Experience replay ---

    def record_experience(
        self,
        context: str,
        action: str,
        outcome: str,
        score: float,
        lesson: str = "",
    ) -> Experience:
        """Record a learning experience."""
        exp = Experience(
            context=context,
            action=action,
            outcome=outcome,
            score=score,
            lesson=lesson,
        )
        self._experiences.append(exp)
        return exp

    def replay_experiences(
        self,
        context: str | None = None,
        min_score: float = 0.0,
        limit: int = 10,
    ) -> List[Experience]:
        """Replay relevant experiences."""
        results = []
        for exp in self._experiences:
            if exp.score < min_score:
                continue
            if context and context.lower() not in exp.context.lower():
                continue
            exp.replay_count += 1
            results.append(exp)

        # Sort by score (best first), then replay count (least replayed first)
        results.sort(key=lambda x: (-x.score, x.replay_count))
        return results[:limit]

    def verify_experience(self, exp_id: str, verified: bool = True) -> None:
        """Mark an experience as verified."""
        for exp in self._experiences:
            if exp.id == exp_id:
                exp.verified = verified
                break

    # --- Consolidation ---

    def _maybe_consolidate(self) -> None:
        """Consolidate if over threshold."""
        if len(self._entries) < self._consolidation_threshold:
            return
        self.consolidate()

    def consolidate(self) -> Dict[str, int]:
        """Consolidate memories: compress, merge, evict."""
        stats = {"merged": 0, "evicted": 0, "compressed": 0}

        # 1. Evict low-importance, low-access entries
        to_evict = [
            eid for eid, e in self._entries.items()
            if e.importance < 0.3 and e.access_count < 2
        ]
        for eid in to_evict[:len(to_evict) // 2]:  # evict bottom 50%
            del self._entries[eid]
            stats["evicted"] += 1

        # 2. Merge similar entries (same key, similar values)
        keys_seen: Dict[str, List[str]] = {}
        for eid, entry in self._entries.items():
            keys_seen.setdefault(entry.key, []).append(eid)

        for key, eids in keys_seen.items():
            if len(eids) > 1:
                entries = [self._entries[eid] for eid in eids]
                entries.sort(key=lambda e: e.importance, reverse=True)
                keeper = entries[0]
                for other in entries[1:]:
                    keeper.confidence = min(1.0, keeper.confidence + 0.1)
                    keeper.importance = min(2.0, keeper.importance + other.importance * 0.5)
                    self._entries.pop(other.id, None)
                    stats["merged"] += 1

        return stats

    def get_consolidation_summary(self) -> Dict[str, Any]:
        """Get summary of memory state."""
        type_counts = {}
        for entry in self._entries.values():
            t = entry.type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_entries": len(self._entries),
            "total_experiences": len(self._experiences),
            "by_type": type_counts,
            "high_importance": sum(1 for e in self._entries.values() if e.importance >= 1.5),
            "verified_experiences": sum(1 for e in self._experiences if e.verified),
        }

    # --- Persistence ---

    def save(self) -> None:
        """Persist memory to disk."""
        data = {
            "entries": {
                eid: {
                    "id": e.id,
                    "type": e.type.value,
                    "key": e.key,
                    "value": e.value,
                    "importance": e.importance,
                    "confidence": e.confidence,
                    "source": e.source,
                    "tags": e.tags,
                    "created_at": e.created_at,
                    "access_count": e.access_count,
                }
                for eid, e in self._entries.items()
            },
            "experiences": [
                {
                    "id": exp.id,
                    "context": exp.context,
                    "action": exp.action,
                    "outcome": exp.outcome,
                    "score": exp.score,
                    "lesson": exp.lesson,
                    "verified": exp.verified,
                }
                for exp in self._experiences
            ],
        }
        path = self._data_dir / "memory.json"
        path.write_text(json.dumps(data, indent=2, default=str))

    def load(self) -> None:
        """Load memory from disk."""
        path = self._data_dir / "memory.json"
        if not path.exists():
            return

        data = json.loads(path.read_text())

        for eid, edata in data.get("entries", {}).items():
            entry = MemoryEntry(
                id=edata["id"],
                type=MemoryType(edata["type"]),
                key=edata["key"],
                value=edata["value"],
                importance=edata.get("importance", 1.0),
                confidence=edata.get("confidence", 1.0),
                source=edata.get("source", ""),
                tags=edata.get("tags", []),
                created_at=edata.get("created_at", 0),
                access_count=edata.get("access_count", 0),
            )
            self._entries[eid] = entry

        for exp_data in data.get("experiences", []):
            exp = Experience(
                id=exp_data["id"],
                context=exp_data["context"],
                action=exp_data["action"],
                outcome=exp_data["outcome"],
                score=exp_data.get("score", 0),
                lesson=exp_data.get("lesson", ""),
                verified=exp_data.get("verified", False),
            )
            self._experiences.append(exp)

    # --- Utility ---

    def get_all_by_type(self, mem_type: MemoryType) -> List[MemoryEntry]:
        """Get all entries of a specific type."""
        return [e for e in self._entries.values() if e.type == mem_type]

    def get_top_entries(self, n: int = 10) -> List[MemoryEntry]:
        """Get top N entries by importance."""
        sorted_entries = sorted(
            self._entries.values(),
            key=lambda e: (e.importance, e.confidence),
            reverse=True,
        )
        return sorted_entries[:n]
