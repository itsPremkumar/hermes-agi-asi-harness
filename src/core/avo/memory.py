"""AVO memory: persistent, cross-iteration knowledge store."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    kind: str = "observation"
    content: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    parent_id: str | None = None
    success: bool | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "content": self.content,
            "data": self.data,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "parent_id": self.parent_id,
            "success": self.success,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MemoryEntry:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class AVOMemory:
    """Persistent memory that survives individual model contexts.

    Stores observations, experiments, failures, successes, and learned
    constraints so the agent does not repeatedly reconstruct the search.
    """

    def __init__(self, store_dir: str = ".avo_memory") -> None:
        self._store_dir = Path(store_dir)
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._entries: Dict[str, MemoryEntry] = {}
        self._index: Dict[str, List[str]] = {"kind": {}, "tag": {}, "success": {}}
        self._load()

    # -- CRUD --------------------------------------------------------

    def add(self, entry: MemoryEntry) -> MemoryEntry:
        self._entries[entry.id] = entry
        self._index_entry(entry)
        self._persist()
        return entry

    def get(self, entry_id: str) -> MemoryEntry | None:
        return self._entries.get(entry_id)

    def remove(self, entry_id: str) -> bool:
        if entry_id not in self._entries:
            return False
        entry = self._entries.pop(entry_id)
        self._unindex_entry(entry)
        self._persist()
        return True

    # -- Queries -----------------------------------------------------

    def query(
        self,
        kind: str | None = None,
        tag: str | None = None,
        success: bool | None = None,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        ids = set(self._entries.keys())
        if kind is not None:
            ids &= set(self._index["kind"].get(kind, []))
        if tag is not None:
            ids &= set(self._index["tag"].get(tag, []))
        if success is not None:
            ids &= set(self._index["success"].get(str(success), []))
        return [self._entries[i] for i in list(ids)[:limit]]

    def recent(self, n: int = 20) -> List[MemoryEntry]:
        return sorted(self._entries.values(), key=lambda e: e.timestamp, reverse=True)[:n]

    def stats(self) -> Dict[str, Any]:
        kinds: Dict[str, int] = {}
        successes = 0
        for e in self._entries.values():
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
            if e.success:
                successes += 1
        return {
            "total_entries": len(self._entries),
            "by_kind": kinds,
            "successes": successes,
            "store_dir": str(self._store_dir),
        }

    # -- Persistence -------------------------------------------------

    def _index_entry(self, entry: MemoryEntry) -> None:
        self._index["kind"].setdefault(entry.kind, []).append(entry.id)
        for t in entry.tags:
            self._index["tag"].setdefault(t, []).append(entry.id)
        self._index["success"].setdefault(str(entry.success), []).append(entry.id)

    def _unindex_entry(self, entry: MemoryEntry) -> None:
        bucket = self._index["kind"].get(entry.kind, [])
        if entry.id in bucket:
            bucket.remove(entry.id)
        for t in entry.tags:
            b = self._index["tag"].get(t, [])
            if entry.id in b:
                b.remove(entry.id)
        b = self._index["success"].get(str(entry.success), [])
        if entry.id in b:
            b.remove(entry.id)

    def _persist(self) -> None:
        path = self._store_dir / "memory.json"
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._entries.values()], f, indent=2)
        tmp.replace(path)

    def _load(self) -> None:
        path = self._store_dir / "memory.json"
        if not path.exists():
            return
        try:
            with open(path, encoding="utf-8") as f:
                records = json.load(f)
            for r in records:
                entry = MemoryEntry.from_dict(r)
                self._entries[entry.id] = entry
                self._index_entry(entry)
        except (json.JSONDecodeError, OSError):
            pass
