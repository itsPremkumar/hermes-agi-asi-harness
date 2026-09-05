"""
Hermes AGI/ASI Harness — Scoped Continual Harness State Manager.

Ported from Prime Agent (prime-agent-runtime/src/rlm/harness.py):
- 4 Formal Harness Kinds: prompt, memory, skill, subagent
- Dual Scopes: local (session/project-specific) vs global (machine-wide)
- Snapshot rollbacks and append-only refinement audit log (refinements.jsonl)
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("hermes.refine.harness_state")

HarnessKind = Literal["prompt", "memory", "skill", "subagent"]
HarnessScope = Literal["local", "global"]


@dataclass
class HarnessEntry:
    """A durable item in the harness state (prompt, memory, skill, or subagent)."""
    id: str
    kind: HarnessKind
    title: str
    content: str
    scope: HarnessScope = "local"
    metadata: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HarnessEntry:
        return cls(**data)


@dataclass
class RefinementEvent:
    """An audit record of an evidence-backed update to the harness."""
    event_id: str
    trigger: str
    changes: list[str]
    evidence: str
    outcome: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HarnessStateManager:
    """
    Manages durable, versioned harness state across local and global scopes.
    Allows the harness to retain specialized subagents, skills, instructions,
    and verified memory across reboots and disconnects.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.local_dir = self.workspace_root / ".hermes" / "harness"
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self.local_state_file = self.local_dir / "harness_state.json"
        self.refinements_log = self.local_dir / "refinements.jsonl"
        self.snapshots_dir = self.local_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        self._local_entries: dict[str, HarnessEntry] = {}
        self._load_local_state()

    def _load_local_state(self) -> None:
        if self.local_state_file.exists():
            try:
                data = json.loads(self.local_state_file.read_text(encoding="utf-8"))
                for item in data.get("entries", []):
                    entry = HarnessEntry.from_dict(item)
                    self._local_entries[entry.id] = entry
            except Exception as e:
                logger.warning("Error loading harness state: %s", e)

    def _save_local_state(self) -> None:
        data = {
            "schema_version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entries": [e.to_dict() for e in self._local_entries.values()],
        }
        self.local_state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_entry(
        self,
        kind: HarnessKind,
        title: str,
        content: str,
        scope: HarnessScope = "local",
        metadata: dict[str, Any] | None = None,
    ) -> HarnessEntry:
        """Add a new prompt, memory, skill, or subagent entry."""
        entry_id = f"{kind}-{uuid.uuid4().hex[:6]}"
        entry = HarnessEntry(
            id=entry_id,
            kind=kind,
            title=title,
            content=content,
            scope=scope,
            metadata=metadata or {},
        )
        self._local_entries[entry_id] = entry
        self._save_local_state()
        return entry

    def get_entries(
        self,
        kind: HarnessKind | None = None,
        scope: HarnessScope | None = None,
    ) -> list[HarnessEntry]:
        """Retrieve stored harness entries filtered by kind and scope."""
        entries = list(self._local_entries.values())
        if kind:
            entries = [e for e in entries if e.kind == kind]
        if scope:
            entries = [e for e in entries if e.scope == scope]
        return entries

    def remove_entry(self, entry_id: str) -> bool:
        """Delete an entry by ID."""
        if entry_id in self._local_entries:
            del self._local_entries[entry_id]
            self._save_local_state()
            return True
        return False

    def record_refinement_event(
        self,
        trigger: str,
        changes: list[str],
        evidence: str,
        outcome: str,
    ) -> RefinementEvent:
        """Append an audit event to refinements.jsonl."""
        event = RefinementEvent(
            event_id=f"refine-{uuid.uuid4().hex[:6]}",
            trigger=trigger,
            changes=changes,
            evidence=evidence,
            outcome=outcome,
        )
        with open(self.refinements_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")
        return event

    def create_snapshot(self) -> str:
        """Create a point-in-time snapshot of current harness state."""
        snap_id = f"snap-{uuid.uuid4().hex[:8]}"
        snap_file = self.snapshots_dir / f"{snap_id}.json"
        data = {
            "snapshot_id": snap_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "entries": [e.to_dict() for e in self._local_entries.values()],
        }
        snap_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return snap_id

    def rollback_snapshot(self, snapshot_id: str) -> bool:
        """Revert harness state to a prior snapshot."""
        snap_file = self.snapshots_dir / f"{snapshot_id}.json"
        if not snap_file.exists():
            return False
        try:
            data = json.loads(snap_file.read_text(encoding="utf-8"))
            self._local_entries.clear()
            for item in data.get("entries", []):
                entry = HarnessEntry.from_dict(item)
                self._local_entries[entry.id] = entry
            self._save_local_state()
            return True
        except Exception as e:
            logger.error("Failed to rollback snapshot %s: %s", snapshot_id, e)
            return False

    def overview(self) -> dict[str, Any]:
        """Produce an overview summary of durable harness state."""
        return {
            "total_entries": len(self._local_entries),
            "prompts_count": len(self.get_entries(kind="prompt")),
            "memories_count": len(self.get_entries(kind="memory")),
            "skills_count": len(self.get_entries(kind="skill")),
            "subagents_count": len(self.get_entries(kind="subagent")),
            "state_file": str(self.local_state_file),
            "refinements_log": str(self.refinements_log),
        }
