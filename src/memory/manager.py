"""
HERMES INTELLIGENCE OS — MEMORY OPERATING SYSTEM (MEMORY OS)
============================================================
The unified Memory Operating System coordinating all 8 memory subsystems
and the persistent Trajectory Archive.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .subsystems import (
    CapabilityMemory,
    DecisionMemory,
    EpisodicMemory,
    FailureMemory,
    ProceduralMemory,
    SemanticMemory,
    TrajectoryMemory,
    WorkingMemory,
    WorldStateMemory,
)
from .trajectories import Trajectory, TrajectoryArchive, TrajectoryStep

logger = logging.getLogger("hermes.memory")


class MemoryOS:
    """The central Memory Operating System coordinating 9 memory domains and persistent storage."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.storage_dir = Path(workspace_root) / ".hermes" / "memory"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.semantic = SemanticMemory()
        self.episodic = EpisodicMemory()
        self.procedural = ProceduralMemory()
        self.working = WorkingMemory()
        self.failure = FailureMemory()
        self.decision = DecisionMemory()
        self.world_state = WorldStateMemory()
        self.capability = CapabilityMemory()
        self.trajectory = TrajectoryMemory()
        self.trajectories = TrajectoryArchive(workspace_root=workspace_root)

        # Automatically hydrate persistent memory domains from disk
        self.load_from_disk()

    def save_to_disk(self) -> dict[str, int]:
        """Save all non-volatile memory domains into structured JSONL storage."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        counts = {}
        targets = {
            "semantic": self.semantic,
            "episodic": self.episodic,
            "procedural": self.procedural,
            "failure": self.failure,
            "decision": self.decision,
            "world_state": self.world_state,
            "capability": self.capability,
        }
        for name, subsystem in targets.items():
            records = subsystem.export_records()
            file_path = self.storage_dir / f"{name}.jsonl"
            with open(file_path, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r) + "\n")
            counts[name] = len(records)
        return counts

    def load_from_disk(self) -> dict[str, int]:
        """Load and hydrate all non-volatile memory domains from disk."""
        if not self.storage_dir.exists():
            return {}
        counts = {}
        targets = {
            "semantic": self.semantic,
            "episodic": self.episodic,
            "procedural": self.procedural,
            "failure": self.failure,
            "decision": self.decision,
            "world_state": self.world_state,
            "capability": self.capability,
        }
        for name, subsystem in targets.items():
            file_path = self.storage_dir / f"{name}.jsonl"
            if file_path.exists():
                records = []
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                records.append(json.loads(line))
                            except Exception:
                                continue
                loaded = subsystem.import_records(records)
                counts[name] = loaded
        return counts

    def flush(self) -> dict[str, int]:
        """Convenience alias to flush all memories to disk."""
        return self.save_to_disk()

    # -- Continuous-operation helpers (P22 + ranked recall) --------------
    def rank_relevant(self, query: str, limit: int = 8) -> dict[str, Any]:
        """AGX-style ranked recall across semantic/procedural/failure for prompt injection."""
        try:
            from .ranking import memory_str, rank_lessons
        except Exception:
            return {"bullets": "", "count": 0}
        items: list[Any] = []
        try:
            items.extend(list(getattr(self.semantic, "_entries", {}).values()))
        except Exception:
            pass
        try:
            items.extend(list(getattr(self.procedural, "_procedures", {}).values()))
        except Exception:
            pass
        try:
            items.extend(list(getattr(self.failure, "_failures", {}).values()))
        except Exception:
            pass
        ranked = rank_lessons(items, query, limit=limit)
        return {"bullets": memory_str(ranked), "count": len(ranked)}

    def consolidate_p22(self) -> dict[str, Any]:
        """P22 sleep/dream consolidation: dedupe + archive + calibrate + flush."""
        try:
            from .consolidation import consolidate
            return consolidate(self)
        except Exception as e:
            return {"merged": 0, "archived": 0, "calibrated": 0, "error": str(e)}

    def index_vector(self, doc_id: str, text: str, tags: Any = None) -> bool:
        try:
            from .vector_graph import VectorStore
            VectorStore(workspace_root=self.workspace_root).add(doc_id, text, list(tags or []))
            return True
        except Exception:
            return False

    def semantic_search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        try:
            from .vector_graph import VectorStore
            hits = VectorStore(workspace_root=self.workspace_root).search(query, limit=limit)
            sem = getattr(self, "semantic", None)
            out: list[dict[str, Any]] = []
            for doc_id, score in hits:
                fact = doc_id
                try:
                    entry = sem._entries.get(doc_id) if sem and hasattr(sem, "_entries") else None
                    if entry is not None:
                        fact = getattr(entry, "fact", doc_id)
                except Exception:
                    pass
                out.append({"doc_id": doc_id, "score": score, "fact": fact})
            return out
        except Exception:
            return []

    def kg_link(self, src: str, rel: str, dst: str, src_type: str = "entity", dst_type: str = "entity") -> bool:
        try:
            from .vector_graph import KnowledgeGraph
            kg = KnowledgeGraph(workspace_root=self.workspace_root)
            if src not in getattr(kg, "_nodes", {}):
                kg.add_node(src, src_type)
            if dst not in getattr(kg, "_nodes", {}):
                kg.add_node(dst, dst_type)
            kg.add_edge(src, rel, dst)
            return True
        except Exception:
            return False

    def record_usage(self, mission_id: str, tokens: int, runtime: str = "", workers: int = 0) -> dict[str, Any]:
        try:
            from .ledger import EconomicLedger
            return EconomicLedger(workspace_root=self.workspace_root).record(mission_id, tokens, runtime, workers)
        except Exception as e:
            return {"mission_id": mission_id, "tokens": tokens, "error": str(e)}

    def stats(self) -> dict[str, Any]:
        return {
            "semantic_entries": self.semantic.count(),
            "episodic_events": self.episodic.count(),
            "procedures": self.procedural.count(),
            "failures_indexed": self.failure.count(),
            "decisions_recorded": len(self.decision.all_decisions()),
            "capabilities_tracked": len(self.capability.all_capabilities()),
            "in_memory_trajectories": self.trajectory.count(),
            "archived_trajectories": self.trajectories.count(),
            "persistent_storage_dir": str(self.storage_dir),
        }

