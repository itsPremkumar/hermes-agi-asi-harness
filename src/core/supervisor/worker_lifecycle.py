"""Worker Lifecycle, Contracts, Heartbeats, and Monitoring.

Manages the full lifecycle of Hermes workers from creation to completion.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class WorkerState(str, Enum):
    """Worker lifecycle states."""
    CREATED = "created"
    INITIALIZING = "initializing"
    ASSIGNED = "assigned"
    CONTEXT_LOADING = "context_loading"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    VERIFYING = "verifying"
    REPORTING = "reporting"
    WAITING = "waiting"
    CONTINUING = "continuing"
    COMPLETED = "completed"
    FAILED = "failed"
    STALLED = "stalled"
    CANCELLED = "cancelled"


@dataclass
class WorkerContract:
    """Complete contract for a worker assignment."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mission_id: str = ""
    task_id: str = ""

    # Task definition
    objective: str = ""
    description: str = ""

    # Context
    repository: str = ""
    branch: str = ""
    dependencies: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)

    # Expected outputs
    expected_outputs: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    # Tools and permissions
    tools: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)

    # Constraints
    risk_level: str = "low"
    deadline: float = 0.0
    report_frequency_seconds: int = 120

    # Metadata
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerHeartbeat:
    """Worker heartbeat signal."""
    worker_id: str = ""
    assignment_id: str = ""
    status: str = ""
    current_action: str = ""
    current_subtask: str = ""
    progress: float = 0.0
    blockers: List[str] = field(default_factory=list)
    confidence: float = 1.0
    tests_passed: int = 0
    tests_failed: int = 0
    files_changed: int = 0
    commits: int = 0
    token_usage: int = 0
    runtime_seconds: float = 0.0
    last_event: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class WorkerResult:
    """Result of a worker assignment."""
    assignment_id: str = ""
    worker_id: str = ""
    status: str = ""

    # Outputs
    outputs: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    commits: List[str] = field(default_factory=list)

    # Verification
    expected: List[str] = field(default_factory=list)
    observed: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

    # Issues
    unresolved: List[str] = field(default_factory=list)
    confidence: float = 0.0

    # Metadata
    completed_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkerLifecycle:
    """Manages worker lifecycle transitions."""

    def __init__(self):
        self._workers: Dict[str, Dict[str, Any]] = {}
        self._transitions: List[Dict[str, Any]] = []

    def create_worker(self, worker_id: str, name: str, capabilities: List[str]) -> None:
        """Create a new worker."""
        self._workers[worker_id] = {
            "id": worker_id,
            "name": name,
            "capabilities": capabilities,
            "state": WorkerState.CREATED,
            "current_contract": None,
            "heartbeats": [],
            "results": [],
            "created_at": time.time(),
        }

    def transition(self, worker_id: str, new_state: WorkerState, reason: str = "") -> None:
        """Transition a worker to a new state."""
        if worker_id in self._workers:
            old_state = self._workers[worker_id]["state"]
            self._workers[worker_id]["state"] = new_state
            self._transitions.append({
                "worker_id": worker_id,
                "from": old_state.value,
                "to": new_state.value,
                "reason": reason,
                "timestamp": time.time(),
            })

    def assign_contract(self, worker_id: str, contract: WorkerContract) -> None:
        """Assign a contract to a worker."""
        if worker_id in self._workers:
            self._workers[worker_id]["current_contract"] = contract
            self.transition(worker_id, WorkerState.ASSIGNED, "Contract assigned")

    def record_heartbeat(self, worker_id: str, heartbeat: WorkerHeartbeat) -> None:
        """Record a worker heartbeat."""
        if worker_id in self._workers:
            self._workers[worker_id]["heartbeats"].append(heartbeat)

    def complete_assignment(self, worker_id: str, result: WorkerResult) -> None:
        """Complete a worker assignment."""
        if worker_id in self._workers:
            self._workers[worker_id]["results"].append(result)
            self.transition(worker_id, WorkerState.COMPLETED, "Assignment completed")

    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get worker state."""
        return self._workers.get(worker_id)

    def get_all_workers(self) -> List[Dict[str, Any]]:
        """Get all workers."""
        return list(self._workers.values())


class WorkerMonitor:
    """Monitors worker progress and health."""

    def __init__(self, lifecycle: WorkerLifecycle):
        self._lifecycle = lifecycle
        self._alerts: List[Dict[str, Any]] = []

    def check_health(self, worker_id: str) -> Dict[str, Any]:
        """Check worker health."""
        worker = self._lifecycle.get_worker(worker_id)
        if not worker:
            return {"status": "unknown"}

        heartbeats = worker.get("heartbeats", [])
        latest = heartbeats[-1] if heartbeats else None

        # Check for stale heartbeat
        stale = False
        if latest:
            time_since_heartbeat = time.time() - latest.timestamp
            stale = time_since_heartbeat > 300  # 5 minutes

        # Check for low progress
        low_progress = False
        if latest and latest.progress < 0.1 and len(heartbeats) > 10:
            low_progress = True

        # Check for blockers
        blockers = latest.blockers if latest else []

        return {
            "status": worker.get("state"),
            "stale": stale,
            "low_progress": low_progress,
            "blockers": blockers,
            "latest_heartbeat": latest.timestamp if latest else None,
        }

    def get_progress(self, worker_id: str) -> float:
        """Get worker progress."""
        worker = self._lifecycle.get_worker(worker_id)
        if not worker:
            return 0.0

        heartbeats = worker.get("heartbeats", [])
        if not heartbeats:
            return 0.0

        return heartbeats[-1].progress

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health for all workers."""
        health = {}
        for worker in self._lifecycle.get_all_workers():
            health[worker["id"]] = self.check_health(worker["id"])
        return health
