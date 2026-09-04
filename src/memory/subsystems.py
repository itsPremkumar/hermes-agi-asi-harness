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

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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


@dataclass
class EpisodicEvent:
    event_id: str
    event_type: str
    description: str
    actor: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EpisodicMemory:
    """Chronological event log tracking what happened during missions."""

    def __init__(self):
        self._events: list[EpisodicEvent] = []

    def record(self, event_type: str, description: str, actor: str = "system", details: Optional[dict[str, Any]] = None) -> EpisodicEvent:
        ev = EpisodicEvent(
            event_id=f"epi-{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            description=description,
            actor=actor,
            details=details or {},
        )
        self._events.append(ev)
        return ev

    def get_recent(self, n: int = 10) -> list[EpisodicEvent]:
        return self._events[-n:]

    def count(self) -> int:
        return len(self._events)


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

    def get_procedure(self, name: str) -> Optional[Procedure]:
        return self._procedures.get(name)

    def count(self) -> int:
        return len(self._procedures)


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

    def record_failure(self, error_type: str, component: str, root_cause: str, countermeasures: Optional[list[str]] = None) -> FailureSignature:
        key = f"{component}:{error_type}"
        if key in self._failures:
            f_sig = self._failures[key]
            f_sig.occurrences += 1
            f_sig.timestamp = time.time()
            if countermeasures:
                for cm in countermeasures:
                    if cm not in f_sig.countermeasures:
                        f_sig.countermeasures.append(cm)
            return f_sig

        f_sig = FailureSignature(
            failure_id=f"fail-{uuid.uuid4().hex[:8]}",
            error_type=error_type,
            component=component,
            root_cause=root_cause,
            countermeasures=list(countermeasures or []),
        )
        self._failures[key] = f_sig
        return f_sig

    def get_countermeasures(self, error_type: str, component: str) -> list[str]:
        key = f"{component}:{error_type}"
        f_sig = self._failures.get(key)
        return f_sig.countermeasures if f_sig else []

    def count(self) -> int:
        return len(self._failures)


@dataclass
class DecisionRecord:
    decision_id: str
    context: str
    chosen_strategy: str
    rejected_alternatives: list[str]
    rationale: str
    outcome: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class DecisionMemory:
    """Records why particular strategies were chosen over alternative paths."""

    def __init__(self):
        self._decisions: list[DecisionRecord] = []

    def record_decision(self, context: str, chosen: str, rejected: list[str], rationale: str) -> DecisionRecord:
        d = DecisionRecord(
            decision_id=f"dec-{uuid.uuid4().hex[:8]}",
            context=context,
            chosen_strategy=chosen,
            rejected_alternatives=rejected,
            rationale=rationale,
        )
        self._decisions.append(d)
        return d

    def all_decisions(self) -> list[DecisionRecord]:
        return list(self._decisions)


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

    def get_latest(self) -> Optional[dict[str, Any]]:
        return self._snapshots[-1] if self._snapshots else None


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

    def get_capability(self, name: str) -> Optional[CapabilityProfile]:
        return self._capabilities.get(name)

    def all_capabilities(self) -> list[CapabilityProfile]:
        return list(self._capabilities.values())
