"""AVO lineage: version history with matches-or-improves commit policy."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class VersionRecord:
    version: str = field(default_factory=lambda: "v0")
    parent: str | None = None
    source: str = ""
    hypothesis: str = ""
    modification: str = ""
    test_results: Dict[str, Any] = field(default_factory=dict)
    benchmark_results: Dict[str, Any] = field(default_factory=dict)
    correctness: bool = False
    performance: float = 0.0
    environment: str = ""
    reasoning_summary: str = ""
    commit_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dataclass_fields__.items()}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> VersionRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class Lineage:
    """Maintains historical evolution and enforces matches-or-improves commit policy.

    AVO does not simply keep ``best_solution`` — it preserves the full
    evolution tree so the supervisor can detect stagnation and the
    agent can reason about what worked.
    """

    def __init__(self, store_dir: str = ".avo_memory/lineage") -> None:
        self._store_dir = Path(store_dir)
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._versions: Dict[str, VersionRecord] = {}
        self._head: str | None = None
        self._load()

    # -- Commit policy ------------------------------------------------

    def commit_candidate(
        self,
        record: VersionRecord,
        parent_version: str | None = None,
    ) -> bool:
        """Commit a candidate ONLY if it matches or improves on parent.

        Matches-or-improves policy (per AVO paper reconstruction):
        - FAIL correctness  → discard
        - Worse than parent  → reject
        - Equal              → optionally preserve
        - Better             → commit
        """
        if not record.correctness:
            return False
        if parent_version and parent_version in self._versions:
            parent = self._versions[parent_version]
            if record.performance < parent.performance:
                return False
        vid = record.version or uuid.uuid4().hex[:8]
        record.version = vid
        self._versions[vid] = record
        if parent_version:
            record.parent = parent_version
        if self._head is None or record.performance >= self._versions.get(self._head, VersionRecord()).performance:
            self._head = vid
        self._persist()
        return True

    def get(self, version: str) -> VersionRecord | None:
        return self._versions.get(version)

    def head(self) -> VersionRecord | None:
        if self._head is None:
            return None
        return self._versions.get(self._head)

    def branch(self, parent_version: str) -> List[VersionRecord]:
        return [v for v in self._versions.values() if v.parent == parent_version]

    def all_versions(self) -> List[VersionRecord]:
        return sorted(self._versions.values(), key=lambda v: v.created_at)

    def stats(self) -> Dict[str, Any]:
        accepted = sum(1 for v in self._versions.values() if v.correctness and (self.head() is None or v.performance >= self.head().performance))
        return {
            "total_versions": len(self._versions),
            "head": self._head,
            "accepted_or_better": accepted,
            "rejected": len(self._versions) - accepted,
        }

    # -- Persistence -------------------------------------------------

    def _persist(self) -> None:
        path = self._store_dir / "lineage.json"
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([v.to_dict() for v in self._versions.values()], f, indent=2)
        tmp.replace(path)

    def _load(self) -> None:
        path = self._store_dir / "lineage.json"
        if not path.exists():
            return
        try:
            with open(path, encoding="utf-8") as f:
                records = json.load(f)
            for r in records:
                rec = VersionRecord.from_dict(r)
                self._versions[rec.version] = rec
        except (json.JSONDecodeError, OSError):
            pass
