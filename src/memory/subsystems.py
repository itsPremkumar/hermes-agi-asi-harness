"""
HERMES INTELLIGENCE OS — 8-SYSTEM MEMORY ARCHITECTURE
=====================================================
Formalizes the 8 distinct memory systems:
1. Semantic Memory    — Facts and domain knowledge
2. Episodic Memory    — What happened chronologically
3. Procedural Memory  — How to perform workflows and procedures
4. Working Memory     — Active scratchpad & short-term registers
5. Failure Memory     — Anti-patterns, root causes, failure signatures
6. Decision Memory    — Why a strategy was chosen over alternatives
7. World-State Memory — Environment snapshots over time
8. Capability Memory  — Calibrated skill success rates and limits
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("hermes.memory.subsystems")


@dataclass
class SemanticEntry:
    entry_id: str
    fact: str
    category: str
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.95
    source: str = "internal"
    created_at: float = field(default_factory=time.time)


class SemanticMemory:
    """Stores and retrieves verifiable facts and declarative domain knowledge."""

    def __init__(self):
        self._entries: dict[str, SemanticEntry] = {}

    def store(self, fact: str, category: str = "general", tags: Optional[list[str]] = None, confidence: float = 0.95, source: str = "internal") -> SemanticEntry:
        eid = f"sem-{uuid.uuid4().hex[:8]}"
        entry = SemanticEntry(entry_id=eid, fact=fact, category=category, tags=list(tags or []), confidence=confidence, source=source)
        self._entries[eid] = entry
        return entry

    def search(self, query: str, limit: int = 5) -> list[SemanticEntry]:
        query_words = set(re.findall(r"\w+", query.lower()))
        scored = []
        for e in self._entries.values():
            e_words = set(re.findall(r"\w+", e.fact.lower()))
            overlap = len(query_words & e_words)
            if overlap > 0:
                scored.append((overlap, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def count(self) -> int:
        return len(self._entries)

    def export_records(self) -> list[dict[str, Any]]:
        return [
            {
                "entry_id": e.entry_id,
                "fact": e.fact,
                "category": e.category,
                "tags": e.tags,
                "confidence": e.confidence,
                "source": e.source,
                "created_at": e.created_at,
            }
            for e in self._entries.values()
        ]

    def import_records(self, records: list[dict[str, Any]]) -> int:
        loaded = 0
        for r in records:
            entry = SemanticEntry(**r)
            self._entries[entry.entry_id] = entry
            loaded += 1
        return loaded


@dataclass
class EpisodicEvent:
    event_id: str
    event_type: str
    description: str
    actor: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def mission_id(self) -> str:
        return self.details.get("mission_id", self.event_id)


class EpisodicMemory:
    """Chronological event log tracking what happened during missions."""

    def __init__(self):
        self._events: list[EpisodicEvent] = []

    def record(
        self,
        event_type: str = "mission_step",
        description: str = "",
        actor: str = "system",
        details: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> EpisodicEvent:
        merged_details = dict(details or {})
        merged_details.update(kwargs)
        if not description and kwargs:
            description = str(kwargs.get("user_request") or kwargs.get("plan_summary") or kwargs.get("mission_id") or "Mission event")
        ev = EpisodicEvent(
            event_id=kwargs.get("mission_id") or f"epi-{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            description=description,
            actor=actor,
            details=merged_details,
        )
        self._events.append(ev)
        return ev

    def get_recent(self, n: int = 10) -> list[EpisodicEvent]:
        return self._events[-n:]

    def count(self) -> int:
        return len(self._events)

    def export_records(self) -> list[dict[str, Any]]:
        return [
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "description": ev.description,
                "actor": ev.actor,
                "details": ev.details,
                "timestamp": ev.timestamp,
            }
            for ev in self._events
        ]

    def import_records(self, records: list[dict[str, Any]]) -> int:
        loaded = 0
        for r in records:
            ev = EpisodicEvent(**r)
            self._events.append(ev)
            loaded += 1
        return loaded


@dataclass
class Procedure:
    procedure_id: str
    name: str
    steps: list[str]
    preconditions: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    success_rate: float = 1.0
    executions: int = 0


class ProceduralMemory:
    """Stores how-to recipes and executable procedures."""

    def __init__(self):
        self._procedures: dict[str, Procedure] = {}

    def store_procedure(self, name: str, steps: list[str], preconditions: Optional[list[str]] = None, tags: Optional[list[str]] = None) -> Procedure:
        pid = f"proc-{uuid.uuid4().hex[:8]}"
        proc = Procedure(
            procedure_id=pid,
            name=name,
            steps=steps,
            preconditions=list(preconditions or []),
            tags=list(tags or []),
        )
        self._procedures[name] = proc
        return proc

    def store_skill(
        self,
        name: str,
        trigger_context: str = "",
        preconditions: Optional[list[str]] = None,
        action_sequence: Optional[list[str]] = None,
        steps: Optional[list[str]] = None,
        verification_method: str = "oracle_check",
        tags: Optional[list[str]] = None,
    ) -> Procedure:
        step_list = action_sequence or steps or []
        t = list(tags or [])
        if trigger_context:
            t.append(f"context:{trigger_context}")
        t.append(f"verify:{verification_method}")
        return self.store_procedure(name=name, steps=step_list, preconditions=preconditions, tags=t)

    def get_procedure(self, name: str) -> Optional[Procedure]:
        return self._procedures.get(name)

    def get_skill(self, name: str) -> Optional[Procedure]:
        return self.get_procedure(name)

    def count(self) -> int:
        return len(self._procedures)

    def export_records(self) -> list[dict[str, Any]]:
        return [
            {
                "procedure_id": p.procedure_id,
                "name": p.name,
                "steps": p.steps,
                "preconditions": p.preconditions,
                "tags": p.tags,
                "success_rate": p.success_rate,
                "executions": p.executions,
            }
            for p in self._procedures.values()
        ]

    def import_records(self, records: list[dict[str, Any]]) -> int:
        loaded = 0
        for r in records:
            p = Procedure(**r)
            self._procedures[p.name] = p
            loaded += 1
        return loaded


class WorkingMemory:
    """Active registers and scratchpad for the current cognitive turn."""

    def __init__(self):
        self._registers: dict[str, Any] = {}
        self._scratchpad: list[str] = []

    def set_register(self, key: str, value: Any) -> None:
        self._registers[key] = value

    def get_register(self, key: str, default: Any = None) -> Any:
        return self._registers.get(key, default)

    def append_scratchpad(self, note: str) -> None:
        self._scratchpad.append(note)

    def read_scratchpad(self) -> list[str]:
        return list(self._scratchpad)

    def clear(self) -> None:
        self._registers.clear()
        self._scratchpad.clear()


@dataclass
class FailureSignature:
    failure_id: str
    error_type: str
    component: str
    root_cause: str
    countermeasures: list[str]
    occurrences: int = 1
    timestamp: float = field(default_factory=time.time)


class FailureMemory:
    """Learned anti-patterns, recurring failure modes, and circuit breaker limits."""

    def __init__(self):
        self._failures: dict[str, FailureSignature] = {}

    def record_failure(
        self,
        error_type: str,
        component: str = "general",
        root_cause: str = "",
        countermeasures: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
        traceback_str: str = "",
        recovery_attempted: str = "",
        resolved: bool = True,
        **kwargs: Any,
    ) -> FailureSignature:
        comp = component if component != "general" else (context.get("file") if isinstance(context, dict) else "general")
        rc = root_cause or traceback_str or "Failure recorded"
        cms = list(countermeasures or [])
        if recovery_attempted:
            cms.append(recovery_attempted)
        key = f"{comp}:{error_type}"
        if key in self._failures:
            f_sig = self._failures[key]
            f_sig.occurrences += 1
            f_sig.timestamp = time.time()
            if cms:
                for cm in cms:
                    if cm not in f_sig.countermeasures:
                        f_sig.countermeasures.append(cm)
            return f_sig

        f_sig = FailureSignature(
            failure_id=f"fail-{uuid.uuid4().hex[:8]}",
            error_type=error_type,
            component=comp,
            root_cause=rc,
            countermeasures=cms,
        )
        self._failures[key] = f_sig
        return f_sig

    def get_failures(self, resolved_only: bool = False) -> list[FailureSignature]:
        return list(self._failures.values())

    def get_countermeasures(self, error_type: str, component: str) -> list[str]:
        key = f"{component}:{error_type}"
        f_sig = self._failures.get(key)
        return f_sig.countermeasures if f_sig else []

    def count(self) -> int:
        return len(self._failures)

    def export_records(self) -> list[dict[str, Any]]:
        return [
            {
                "failure_id": f.failure_id,
                "error_type": f.error_type,
                "component": f.component,
                "root_cause": f.root_cause,
                "countermeasures": f.countermeasures,
                "occurrences": f.occurrences,
                "timestamp": f.timestamp,
            }
            for f in self._failures.values()
        ]

    def import_records(self, records: list[dict[str, Any]]) -> int:
        loaded = 0
        for r in records:
            f = FailureSignature(**r)
            key = f"{f.component}:{f.error_type}"
            self._failures[key] = f
            loaded += 1
        return loaded


@dataclass
class DecisionRecord:
    decision_id: str
    context: str
    chosen_strategy: str
    rejected_alternatives: list[str]
    rationale: str
    outcome: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def chosen(self) -> str:
        return self.chosen_strategy


class DecisionMemory:
    """Records why particular strategies were chosen over alternative paths."""

    def __init__(self):
        self._decisions: list[DecisionRecord] = []

    def record_decision(
        self,
        context: str = "",
        chosen: str = "",
        rejected: Optional[list[str]] = None,
        rationale: str = "",
        task_id: str = "",
        alternatives: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> DecisionRecord:
        ctx = context or task_id or "decision"
        ch = chosen or kwargs.get("chosen_strategy", "")
        rej = rejected if rejected is not None else (alternatives or [])
        rat = rationale or kwargs.get("reason", "")
        d = DecisionRecord(
            decision_id=f"dec-{uuid.uuid4().hex[:8]}",
            context=ctx,
            chosen_strategy=ch,
            rejected_alternatives=rej,
            rationale=rat,
        )
        self._decisions.append(d)
        return d

    def all_decisions(self) -> list[DecisionRecord]:
        return list(self._decisions)

    def get_history(self) -> list[DecisionRecord]:
        return self.all_decisions()

    def export_records(self) -> list[dict[str, Any]]:
        return [
            {
                "decision_id": d.decision_id,
                "context": d.context,
                "chosen_strategy": d.chosen_strategy,
                "rejected_alternatives": d.rejected_alternatives,
                "rationale": d.rationale,
                "outcome": d.outcome,
                "timestamp": d.timestamp,
            }
            for d in self._decisions
        ]

    def import_records(self, records: list[dict[str, Any]]) -> int:
        loaded = 0
        for r in records:
            d = DecisionRecord(**r)
            self._decisions.append(d)
            loaded += 1
        return loaded


class WorldStateMemory:
    """Historical snapshots of environment state across time."""

    def __init__(self):
        self._snapshots: list[dict[str, Any]] = []

    def record_snapshot(self, state_data: dict[str, Any], label: str = "") -> None:
        self._snapshots.append({
            "timestamp": time.time(),
            "label": label,
            "data": state_data,
        })

    def update_state(self, key: str, value: Any, confidence: float = 1.0) -> None:
        latest = self.get_latest()
        data = dict(latest.get("data", {})) if latest and isinstance(latest.get("data"), dict) else {}
        data[key] = value
        self.record_snapshot(data, label=f"update:{key}")

    def get_state(self, key: str, default: Any = None) -> Any:
        latest = self.get_latest()
        if latest and "data" in latest and isinstance(latest["data"], dict):
            return latest["data"].get(key, default)
        return default

    def get_latest(self) -> Optional[dict[str, Any]]:
        return self._snapshots[-1] if self._snapshots else None

    def export_records(self) -> list[dict[str, Any]]:
        return list(self._snapshots)

    def import_records(self, records: list[dict[str, Any]]) -> int:
        self._snapshots.extend(records)
        return len(records)


@dataclass
class CapabilityProfile:
    name: str
    domain: str
    success_rate: float
    invocations: int
    tools_required: list[str]
    difficulty_ceiling: float = 1.0


class CapabilityMemory:
    """Empirical self-model tracking what Hermes can actually do."""

    def __init__(self):
        self._capabilities: dict[str, CapabilityProfile] = {}

    def update_capability(self, name: str, domain: str, success: bool, tools: Optional[list[str]] = None) -> CapabilityProfile:
        if name not in self._capabilities:
            self._capabilities[name] = CapabilityProfile(
                name=name,
                domain=domain,
                success_rate=1.0 if success else 0.0,
                invocations=1,
                tools_required=list(tools or []),
            )
            return self._capabilities[name]

        cap = self._capabilities[name]
        total = cap.invocations + 1
        new_rate = ((cap.success_rate * cap.invocations) + (1.0 if success else 0.0)) / total
        cap.invocations = total
        cap.success_rate = round(new_rate, 4)
        return cap

    def update_success_rate(self, name: str, success: bool, domain: str = "general") -> CapabilityProfile:
        return self.update_capability(name=name, domain=domain, success=success)

    def get_capability(self, name: str) -> Optional[CapabilityProfile]:
        return self._capabilities.get(name)

    def get_metrics(self, name: str) -> dict[str, Any]:
        cap = self.get_capability(name)
        if not cap:
            return {"successes": 0, "invocations": 0, "success_rate": 0.0}
        successes = round(cap.success_rate * cap.invocations)
        return {
            "name": cap.name,
            "successes": successes,
            "invocations": cap.invocations,
            "success_rate": cap.success_rate,
        }

    def all_capabilities(self) -> list[CapabilityProfile]:
        return list(self._capabilities.values())

    def export_records(self) -> list[dict[str, Any]]:
        return [
            {
                "name": c.name,
                "domain": c.domain,
                "success_rate": c.success_rate,
                "invocations": c.invocations,
                "tools_required": c.tools_required,
                "difficulty_ceiling": c.difficulty_ceiling,
            }
            for c in self._capabilities.values()
        ]

    def import_records(self, records: list[dict[str, Any]]) -> int:
        loaded = 0
        for r in records:
            c = CapabilityProfile(**r)
            self._capabilities[c.name] = c
            loaded += 1
        return loaded



class TrajectoryMemory:
    """In-memory index and ring-buffer of active and recent execution trajectories."""

    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self._trajectories: dict[str, Any] = {}

    def store(self, trajectory: Any) -> None:
        self._trajectories[trajectory.trajectory_id] = trajectory
        if len(self._trajectories) > self.capacity:
            oldest_key = next(iter(self._trajectories))
            del self._trajectories[oldest_key]

    def get(self, trajectory_id: str) -> Optional[Any]:
        return self._trajectories.get(trajectory_id)

    def all_trajectories(self) -> list[Any]:
        return list(self._trajectories.values())

    def count(self) -> int:
        return len(self._trajectories)

