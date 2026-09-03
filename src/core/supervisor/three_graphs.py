"""Three Graphs — Mission Graph, Execution Graph, Evidence Graph.

The three central control graphs that the Supervisor uses to manage the mission.

Mission Graph: WHAT must be done (goals, tasks, dependencies)
Execution Graph: WHO is currently doing it (worker assignments)
Evidence Graph: Proof of completion (artifacts, tests, verification)
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Mission Graph — WHAT must be done
# ---------------------------------------------------------------------------

class MissionNodeType(str, Enum):
    MISSION = "mission"
    GOAL = "goal"
    TASK = "task"
    MILESTONE = "milestone"


class MissionNodeStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class MissionNode:
    """A node in the mission graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: MissionNodeType = MissionNodeType.TASK
    title: str = ""
    description: str = ""
    status: MissionNodeStatus = MissionNodeStatus.PENDING

    # Hierarchy
    parent_id: str = ""
    children: List[str] = field(default_factory=list)

    # Dependencies
    depends_on: List[str] = field(default_factory=list)

    # Requirements
    required_capabilities: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)

    # Metadata
    priority: int = 0
    estimated_effort: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


class MissionGraph:
    """Represents WHAT must be done in the mission."""

    def __init__(self, mission_id: str = ""):
        self._mission_id = mission_id
        self._nodes: Dict[str, MissionNode] = {}
        self._root_id: str = ""

    @property
    def mission_id(self) -> str:
        return self._mission_id

    @property
    def root_id(self) -> str:
        return self._root_id

    def add_node(self, node: MissionNode) -> str:
        """Add a node to the graph."""
        self._nodes[node.id] = node
        if node.type == MissionNodeType.MISSION:
            self._root_id = node.id
        return node.id

    def get_node(self, node_id: str) -> Optional[MissionNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_children(self, node_id: str) -> List[MissionNode]:
        """Get children of a node."""
        node = self._nodes.get(node_id)
        if not node:
            return []
        return [self._nodes[cid] for cid in node.children if cid in self._nodes]

    def get_ready_tasks(self) -> List[MissionNode]:
        """Get all tasks that are ready to execute."""
        ready = []
        for node in self._nodes.values():
            if node.type != MissionNodeType.TASK:
                continue
            if node.status != MissionNodeStatus.PENDING:
                continue
            # Check dependencies
            deps_met = all(
                self._nodes.get(dep_id) and
                self._nodes[dep_id].status == MissionNodeStatus.COMPLETED
                for dep_id in node.depends_on
            )
            if deps_met:
                ready.append(node)
        return ready

    def get_blocked_tasks(self) -> List[MissionNode]:
        """Get all blocked tasks."""
        blocked = []
        for node in self._nodes.values():
            if node.type != MissionNodeType.TASK:
                continue
            if node.status != MissionNodeStatus.PENDING:
                continue
            deps_met = all(
                self._nodes.get(dep_id) and
                self._nodes[dep_id].status == MissionNodeStatus.COMPLETED
                for dep_id in node.depends_on
            )
            if not deps_met:
                blocked.append(node)
        return blocked

    def get_progress(self) -> Dict[str, Any]:
        """Get overall progress."""
        tasks = [n for n in self._nodes.values() if n.type == MissionNodeType.TASK]
        if not tasks:
            return {"total": 0, "completed": 0, "percent": 0}

        completed = sum(1 for t in tasks if t.status == MissionNodeStatus.COMPLETED)
        in_progress = sum(1 for t in tasks if t.status == MissionNodeStatus.IN_PROGRESS)
        blocked = sum(1 for t in tasks if t.status == MissionNodeStatus.BLOCKED)

        return {
            "total": len(tasks),
            "completed": completed,
            "in_progress": in_progress,
            "blocked": blocked,
            "percent": (completed / len(tasks) * 100) if tasks else 0,
        }

    def get_critical_path(self) -> List[str]:
        """Get the critical path (longest dependency chain)."""
        # Find the task with the longest chain of dependencies
        longest_path = []
        for node in self._nodes.values():
            if node.type != MissionNodeType.TASK:
                continue
            path = self._trace_dependencies(node.id)
            if len(path) > len(longest_path):
                longest_path = path
        return longest_path

    def _trace_dependencies(self, node_id: str) -> List[str]:
        """Trace all dependencies for a node."""
        node = self._nodes.get(node_id)
        if not node:
            return []

        path = [node_id]
        for dep_id in node.depends_on:
            path = self._trace_dependencies(dep_id) + path
        return path

    def update_status(self, node_id: str, status: MissionNodeStatus) -> None:
        """Update node status."""
        node = self._nodes.get(node_id)
        if node:
            node.status = status
            if status == MissionNodeStatus.COMPLETED:
                node.completed_at = time.time()

    def get_all_tasks(self) -> List[MissionNode]:
        """Get all task nodes."""
        return [n for n in self._nodes.values() if n.type == MissionNodeType.TASK]

    def get_mermaid(self) -> str:
        """Generate Mermaid diagram of the mission graph."""
        lines = ["graph TD"]
        for node in self._nodes.values():
            status_marker = ""
            if node.status == MissionNodeStatus.COMPLETED:
                status_marker = " ✓"
            elif node.status == MissionNodeStatus.IN_PROGRESS:
                status_marker = " 🔄"
            elif node.status == MissionNodeStatus.BLOCKED:
                status_marker = " 🚫"

            lines.append(f"    {node.id}[{node.title}{status_marker}]")

        for node in self._nodes.values():
            for child_id in node.children:
                lines.append(f"    {node.id} --> {child_id}")
            for dep_id in node.depends_on:
                lines.append(f"    {dep_id} -.-> {node.id}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Execution Graph — WHO is doing it
# ---------------------------------------------------------------------------

class WorkerStatus(str, Enum):
    IDLE = "idle"
    ASSIGNED = "assigned"
    BOOTING = "booting"
    PLANNING = "planning"
    WORKING = "working"
    WAITING = "waiting"
    BLOCKED = "blocked"
    VERIFYING = "verifying"
    REPORTING = "reporting"
    DONE = "done"
    FAILED = "failed"
    STALLED = "stalled"
    CANCELLED = "cancelled"


@dataclass
class WorkerNode:
    """A worker in the execution graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    status: WorkerStatus = WorkerStatus.IDLE
    capabilities: List[str] = field(default_factory=list)

    # Assignment
    assigned_task: str = ""
    assignment_contract: Dict[str, Any] = field(default_factory=dict)

    # Progress
    progress: float = 0.0
    current_action: str = ""
    current_subtask: str = ""

    # Heartbeat
    last_heartbeat: float = 0.0
    heartbeat_count: int = 0

    # Results
    artifacts: List[str] = field(default_factory=list)
    commits: List[str] = field(default_factory=list)
    test_results: Dict[str, Any] = field(default_factory=dict)

    # Performance
    success_rate: float = 0.0
    total_tasks: int = 0
    completed_tasks: int = 0

    # Metadata
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionEdge:
    """An edge in the execution graph (worker → task assignment)."""
    worker_id: str = ""
    task_id: str = ""
    assigned_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0


class ExecutionGraph:
    """Represents WHO is currently doing what."""

    def __init__(self):
        self._workers: Dict[str, WorkerNode] = {}
        self._edges: List[ExecutionEdge] = []

    def register_worker(self, worker: WorkerNode) -> None:
        """Register a worker."""
        self._workers[worker.id] = worker

    def get_worker(self, worker_id: str) -> Optional[WorkerNode]:
        """Get a worker by ID."""
        return self._workers.get(worker_id)

    def get_available_workers(self) -> List[WorkerNode]:
        """Get all available (idle) workers."""
        return [w for w in self._workers.values() if w.status == WorkerStatus.IDLE]

    def get_active_workers(self) -> List[WorkerNode]:
        """Get all active workers."""
        return [w for w in self._workers.values() if w.status in (
            WorkerStatus.WORKING, WorkerStatus.PLANNING, WorkerStatus.VERIFYING
        )]

    def get_stalled_workers(self) -> List[WorkerNode]:
        """Get all stalled workers."""
        return [w for w in self._workers.values() if w.status == WorkerStatus.STALLED]

    def assign_task(self, worker_id: str, task_id: str, contract: Dict[str, Any]) -> None:
        """Assign a task to a worker."""
        worker = self._workers.get(worker_id)
        if worker:
            worker.assigned_task = task_id
            worker.assignment_contract = contract
            worker.status = WorkerStatus.ASSIGNED
            worker.assigned_task = task_id

            edge = ExecutionEdge(
                worker_id=worker_id,
                task_id=task_id,
                assigned_at=time.time(),
            )
            self._edges.append(edge)

    def update_worker_status(self, worker_id: str, status: WorkerStatus) -> None:
        """Update worker status."""
        worker = self._workers.get(worker_id)
        if worker:
            worker.status = status

    def record_heartbeat(self, worker_id: str, data: Dict[str, Any]) -> None:
        """Record a worker heartbeat."""
        worker = self._workers.get(worker_id)
        if worker:
            worker.last_heartbeat = time.time()
            worker.heartbeat_count += 1
            worker.progress = data.get("progress", worker.progress)
            worker.current_action = data.get("current_action", worker.current_action)

    def complete_task(self, worker_id: str, success: bool) -> None:
        """Complete a worker's task."""
        worker = self._workers.get(worker_id)
        if worker:
            worker.total_tasks += 1
            if success:
                worker.completed_tasks += 1
                worker.status = WorkerStatus.DONE
            else:
                worker.status = WorkerStatus.FAILED
            worker.success_rate = worker.completed_tasks / worker.total_tasks if worker.total_tasks > 0 else 0.0

    def get_worker_stats(self) -> Dict[str, Any]:
        """Get stats for all workers."""
        return {
            wid: {
                "name": w.name,
                "status": w.status.value,
                "assigned_task": w.assigned_task,
                "progress": w.progress,
                "success_rate": w.success_rate,
            }
            for wid, w in self._workers.items()
        }


# ---------------------------------------------------------------------------
# Evidence Graph — Proof of completion
# ---------------------------------------------------------------------------

class EvidenceType(str, Enum):
    ARTIFACT = "artifact"
    TEST_RESULT = "test_result"
    COMMIT = "commit"
    REVIEW = "review"
    BUILD_RESULT = "build_result"
    DEPLOYMENT = "deployment"
    SECURITY_SCAN = "security_scan"
    PERFORMANCE_BENCHMARK = "performance_benchmark"


class EvidenceStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class EvidenceNode:
    """A piece of evidence in the graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: EvidenceType = EvidenceType.ARTIFACT
    title: str = ""
    description: str = ""
    status: EvidenceStatus = EvidenceStatus.PENDING

    # Source
    task_id: str = ""
    worker_id: str = ""

    # Evidence
    artifacts: List[str] = field(default_factory=list)
    test_results: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)

    # Verification
    verified: bool = False
    verified_at: float = 0.0
    verified_by: str = ""

    # Metadata
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EvidenceGraph:
    """Represents proof of completion for tasks."""

    def __init__(self):
        self._evidence: Dict[str, EvidenceNode] = {}
        self._task_evidence: Dict[str, List[str]] = {}  # task_id → evidence_ids

    def add_evidence(self, evidence: EvidenceNode) -> str:
        """Add evidence to the graph."""
        self._evidence[evidence.id] = evidence
        if evidence.task_id:
            self._task_evidence.setdefault(evidence.task_id, []).append(evidence.id)
        return evidence.id

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceNode]:
        """Get evidence by ID."""
        return self._evidence.get(evidence_id)

    def get_task_evidence(self, task_id: str) -> List[EvidenceNode]:
        """Get all evidence for a task."""
        evidence_ids = self._task_evidence.get(task_id, [])
        return [self._evidence[eid] for eid in evidence_ids if eid in self._evidence]

    def verify_evidence(self, evidence_id: str, verifier: str = "supervisor") -> None:
        """Mark evidence as verified."""
        evidence = self._evidence.get(evidence_id)
        if evidence:
            evidence.verified = True
            evidence.verified_at = time.time()
            evidence.verified_by = verifier

    def is_task_verified(self, task_id: str) -> bool:
        """Check if all evidence for a task is verified."""
        evidence_list = self.get_task_evidence(task_id)
        if not evidence_list:
            return False
        return all(e.verified for e in evidence_list)

    def get_verification_summary(self) -> Dict[str, Any]:
        """Get verification summary."""
        total = len(self._evidence)
        verified = sum(1 for e in self._evidence.values() if e.verified)
        passed = sum(1 for e in self._evidence.values() if e.status == EvidenceStatus.PASSED)
        failed = sum(1 for e in self._evidence.values() if e.status == EvidenceStatus.FAILED)

        return {
            "total": total,
            "verified": verified,
            "passed": passed,
            "failed": failed,
            "percent": (verified / total * 100) if total > 0 else 0,
        }

    def get_evidence_by_type(self, evidence_type: EvidenceType) -> List[EvidenceNode]:
        """Get all evidence of a specific type."""
        return [e for e in self._evidence.values() if e.type == evidence_type]

    def get_failed_evidence(self) -> List[EvidenceNode]:
        """Get all failed evidence."""
        return [e for e in self._evidence.values() if e.status == EvidenceStatus.FAILED]


# ---------------------------------------------------------------------------
# Three Graph Manager
# ---------------------------------------------------------------------------

class ThreeGraphManager:
    """Manages all three graphs and their interactions."""

    def __init__(self, mission_id: str = "", data_dir: Optional[Path] = None):
        self._mission_id = mission_id
        self._data_dir = data_dir or Path.home() / ".hermes" / "supervisor" / "graphs"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._mission_graph = MissionGraph(mission_id)
        self._execution_graph = ExecutionGraph()
        self._evidence_graph = EvidenceGraph()

    @property
    def mission_graph(self) -> MissionGraph:
        return self._mission_graph

    @property
    def execution_graph(self) -> ExecutionGraph:
        return self._execution_graph

    @property
    def evidence_graph(self) -> EvidenceGraph:
        return self._evidence_graph

    def get_status(self) -> Dict[str, Any]:
        """Get status of all three graphs."""
        return {
            "mission": self._mission_graph.get_progress(),
            "execution": self._execution_graph.get_worker_stats(),
            "evidence": self._evidence_graph.get_verification_summary(),
        }

    def save(self) -> None:
        """Save all graphs to disk."""
        data = {
            "mission_id": self._mission_id,
            "mission_graph": {
                nid: {
                    "id": n.id,
                    "type": n.type.value,
                    "title": n.title,
                    "status": n.status.value,
                    "parent_id": n.parent_id,
                    "children": n.children,
                    "depends_on": n.depends_on,
                }
                for nid, n in self._mission_graph._nodes.items()
            },
            "execution_graph": {
                wid: {
                    "id": w.id,
                    "name": w.name,
                    "status": w.status.value,
                    "assigned_task": w.assigned_task,
                    "progress": w.progress,
                }
                for wid, w in self._execution_graph._workers.items()
            },
            "evidence_graph": {
                eid: {
                    "id": e.id,
                    "type": e.type.value,
                    "title": e.title,
                    "status": e.status.value,
                    "task_id": e.task_id,
                    "verified": e.verified,
                }
                for eid, e in self._evidence_graph._evidence.items()
            },
        }
        path = self._data_dir / f"graphs_{self._mission_id}.json"
        path.write_text(json.dumps(data, indent=2))

    def load(self, mission_id: str) -> None:
        """Load graphs from disk."""
        path = self._data_dir / f"graphs_{mission_id}.json"
        if not path.exists():
            return
        # Load logic would go here
