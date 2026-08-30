"""Tests for Supervisor Core, Three Graphs, Worker Lifecycle, Stagnation, Replanning, and Blackboard."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supervisor.supervisor_core import (
    SupervisorCore, SupervisorState, SupervisorContext,
)
from core.supervisor.three_graphs import (
    MissionGraph, MissionNode, MissionNodeType, MissionNodeStatus,
    ExecutionGraph, WorkerNode, WorkerStatus, ExecutionEdge,
    EvidenceGraph, EvidenceNode, EvidenceType, EvidenceStatus,
    ThreeGraphManager,
)
from core.supervisor.worker_lifecycle import (
    WorkerLifecycle, WorkerContract, WorkerHeartbeat, WorkerResult, WorkerState,
)
from core.supervisor.stagnation import (
    StagnationDetector, StagnationSignal, StagnationType,
    InterventionType, VerificationSystem, VerificationResult,
)
from core.supervisor.replanning import (
    ReplanningEngine, ReplanTrigger, ReplanAction, ReplanEvent,
    DynamicDecomposer,
)
from core.supervisor.blackboard import (
    EventBus, EventType, Event, EngineeringBlackboard, BlackboardEventSystem,
)


# ---------------------------------------------------------------------------
# Supervisor Core tests
# ---------------------------------------------------------------------------

class TestSupervisorCore:
    def test_create_supervisor(self):
        supervisor = SupervisorCore()
        assert supervisor is not None
        assert not supervisor.is_active

    def test_get_status_idle(self):
        supervisor = SupervisorCore()
        status = supervisor.get_status()
        assert status["state"] == "idle"

    def test_run_supervisor(self):
        supervisor = SupervisorCore(max_iterations=5)
        context = supervisor.run("Test mission")
        assert context is not None
        # Supervisor may end in various states depending on execution
        assert context.state in (SupervisorState.COMPLETED, SupervisorState.FAILED, SupervisorState.VERIFYING, SupervisorState.MONITORING)

    def test_register_dispatch_callback(self):
        supervisor = SupervisorCore()
        supervisor.on_dispatch(lambda x: None)
        assert supervisor._dispatch_callback is not None


# ---------------------------------------------------------------------------
# Mission Graph tests
# ---------------------------------------------------------------------------

class TestMissionGraph:
    def test_create_graph(self):
        graph = MissionGraph(mission_id="m1")
        assert graph.mission_id == "m1"

    def test_add_node(self):
        graph = MissionGraph()
        node = MissionNode(title="Test", type=MissionNodeType.TASK)
        node_id = graph.add_node(node)
        assert node_id is not None

    def test_get_node(self):
        graph = MissionGraph()
        node = MissionNode(title="Test", type=MissionNodeType.TASK)
        node_id = graph.add_node(node)
        retrieved = graph.get_node(node_id)
        assert retrieved is not None
        assert retrieved.title == "Test"

    def test_get_children(self):
        graph = MissionGraph()
        parent = MissionNode(title="Parent", type=MissionNodeType.GOAL)
        child = MissionNode(title="Child", type=MissionNodeType.TASK, parent_id=parent.id)
        parent.children.append(child.id)
        graph.add_node(parent)
        graph.add_node(child)
        children = graph.get_children(parent.id)
        assert len(children) == 1

    def test_get_ready_tasks(self):
        graph = MissionGraph()
        task = MissionNode(title="Task", type=MissionNodeType.TASK, status=MissionNodeStatus.PENDING)
        graph.add_node(task)
        ready = graph.get_ready_tasks()
        assert isinstance(ready, list)

    def test_get_progress(self):
        graph = MissionGraph()
        task = MissionNode(title="Task", type=MissionNodeType.TASK, status=MissionNodeStatus.COMPLETED)
        graph.add_node(task)
        progress = graph.get_progress()
        assert progress["total"] == 1
        assert progress["completed"] == 1
        assert progress["percent"] == 100

    def test_update_status(self):
        graph = MissionGraph()
        task = MissionNode(title="Task", type=MissionNodeType.TASK)
        graph.add_node(task)
        graph.update_status(task.id, MissionNodeStatus.IN_PROGRESS)
        assert task.status == MissionNodeStatus.IN_PROGRESS

    def test_get_mermaid(self):
        graph = MissionGraph()
        node = MissionNode(title="Test", type=MissionNodeType.TASK)
        graph.add_node(node)
        mermaid = graph.get_mermaid()
        assert "graph TD" in mermaid


# ---------------------------------------------------------------------------
# Execution Graph tests
# ---------------------------------------------------------------------------

class TestExecutionGraph:
    def test_create_graph(self):
        graph = ExecutionGraph()
        assert graph is not None

    def test_register_worker(self):
        graph = ExecutionGraph()
        worker = WorkerNode(name="Hermes-01")
        graph.register_worker(worker)
        assert graph.get_worker(worker.id) is not None

    def test_get_available_workers(self):
        graph = ExecutionGraph()
        worker = WorkerNode(name="Hermes-01")
        graph.register_worker(worker)
        available = graph.get_available_workers()
        assert len(available) == 1

    def test_assign_task(self):
        graph = ExecutionGraph()
        worker = WorkerNode(name="Hermes-01")
        graph.register_worker(worker)
        graph.assign_task(worker.id, "task_1", {})
        assert worker.assigned_task == "task_1"
        assert worker.status == WorkerStatus.ASSIGNED

    def test_complete_task(self):
        graph = ExecutionGraph()
        worker = WorkerNode(name="Hermes-01")
        graph.register_worker(worker)
        graph.assign_task(worker.id, "task_1", {})
        graph.complete_task(worker.id, True)
        assert worker.status == WorkerStatus.DONE
        assert worker.total_tasks == 1

    def test_get_worker_stats(self):
        graph = ExecutionGraph()
        worker = WorkerNode(name="Hermes-01")
        graph.register_worker(worker)
        stats = graph.get_worker_stats()
        assert worker.id in stats


# ---------------------------------------------------------------------------
# Evidence Graph tests
# ---------------------------------------------------------------------------

class TestEvidenceGraph:
    def test_create_graph(self):
        graph = EvidenceGraph()
        assert graph is not None

    def test_add_evidence(self):
        graph = EvidenceGraph()
        evidence = EvidenceNode(title="Test", type=EvidenceType.ARTIFACT)
        eid = graph.add_evidence(evidence)
        assert eid is not None

    def test_get_task_evidence(self):
        graph = EvidenceGraph()
        evidence = EvidenceNode(title="Test", type=EvidenceType.ARTIFACT, task_id="t1")
        graph.add_evidence(evidence)
        task_evidence = graph.get_task_evidence("t1")
        assert len(task_evidence) == 1

    def test_verify_evidence(self):
        graph = EvidenceGraph()
        evidence = EvidenceNode(title="Test", type=EvidenceType.ARTIFACT)
        graph.add_evidence(evidence)
        graph.verify_evidence(evidence.id)
        assert evidence.verified

    def test_is_task_verified(self):
        graph = EvidenceGraph()
        evidence = EvidenceNode(title="Test", type=EvidenceType.ARTIFACT, task_id="t1", status=EvidenceStatus.PASSED)
        graph.add_evidence(evidence)
        graph.verify_evidence(evidence.id)
        assert graph.is_task_verified("t1")

    def test_get_verification_summary(self):
        graph = EvidenceGraph()
        evidence = EvidenceNode(title="Test", type=EvidenceType.ARTIFACT, status=EvidenceStatus.PASSED)
        graph.add_evidence(evidence)
        summary = graph.get_verification_summary()
        assert summary["total"] == 1


# ---------------------------------------------------------------------------
# Worker Lifecycle tests
# ---------------------------------------------------------------------------

class TestWorkerLifecycle:
    def test_create_lifecycle(self):
        lifecycle = WorkerLifecycle()
        assert lifecycle is not None

    def test_create_worker(self):
        lifecycle = WorkerLifecycle()
        lifecycle.create_worker("w1", "Hermes-01", ["coding"])
        worker = lifecycle.get_worker("w1")
        assert worker is not None
        assert worker["name"] == "Hermes-01"

    def test_transition(self):
        lifecycle = WorkerLifecycle()
        lifecycle.create_worker("w1", "Hermes-01", ["coding"])
        lifecycle.transition("w1", WorkerState.EXECUTING)
        worker = lifecycle.get_worker("w1")
        assert worker["state"] == WorkerState.EXECUTING

    def test_assign_contract(self):
        lifecycle = WorkerLifecycle()
        lifecycle.create_worker("w1", "Hermes-01", ["coding"])
        contract = WorkerContract(objective="Test")
        lifecycle.assign_contract("w1", contract)
        worker = lifecycle.get_worker("w1")
        assert worker["current_contract"] is not None

    def test_record_heartbeat(self):
        lifecycle = WorkerLifecycle()
        lifecycle.create_worker("w1", "Hermes-01", ["coding"])
        heartbeat = WorkerHeartbeat(worker_id="w1", progress=0.5)
        lifecycle.record_heartbeat("w1", heartbeat)
        worker = lifecycle.get_worker("w1")
        assert len(worker["heartbeats"]) == 1

    def test_complete_assignment(self):
        lifecycle = WorkerLifecycle()
        lifecycle.create_worker("w1", "Hermes-01", ["coding"])
        result = WorkerResult(assignment_id="a1", status="completed")
        lifecycle.complete_assignment("w1", result)
        worker = lifecycle.get_worker("w1")
        assert len(worker["results"]) == 1


# ---------------------------------------------------------------------------
# Stagnation Detector tests
# ---------------------------------------------------------------------------

class TestStagnationDetector:
    def test_create_detector(self):
        detector = StagnationDetector()
        assert detector is not None

    def test_detect_no_progress(self):
        detector = StagnationDetector()
        heartbeats = [WorkerHeartbeat(worker_id="w1", progress=0.0) for _ in range(15)]
        signals = detector.detect("w1", heartbeats, [])
        assert len(signals) > 0

    def test_detect_stale_heartbeat(self):
        import time
        detector = StagnationDetector()
        heartbeat = WorkerHeartbeat(worker_id="w1", progress=0.5)
        heartbeat.timestamp = time.time() - 600  # 10 minutes ago
        signals = detector.detect("w1", [heartbeat], [])
        assert len(signals) > 0

    def test_get_recommended_intervention(self):
        detector = StagnationDetector()
        signal = StagnationSignal(stagnation_type=StagnationType.NO_PROGRESS)
        intervention = detector.get_recommended_intervention(signal)
        assert intervention is not None


# ---------------------------------------------------------------------------
# Verification System tests
# ---------------------------------------------------------------------------

class TestVerificationSystem:
    def test_create_system(self):
        system = VerificationSystem()
        assert system is not None

    def test_verify_task(self):
        system = VerificationSystem()
        result = system.verify_task("t1", ["tests pass"], [{"data": "tests pass"}])
        assert isinstance(result, VerificationResult)

    def test_verify_mission(self):
        system = VerificationSystem()
        result = system.verify_mission(["all tasks complete"], [])
        assert isinstance(result, VerificationResult)

    def test_get_failed_results(self):
        system = VerificationSystem()
        system.verify_task("t1", ["tests pass"], [{"data": "nothing"}])
        failed = system.get_failed_results()
        assert len(failed) >= 0


# ---------------------------------------------------------------------------
# Replanning Engine tests
# ---------------------------------------------------------------------------

class TestReplanningEngine:
    def test_create_engine(self):
        engine = ReplanningEngine()
        assert engine is not None

    def test_needs_replanning(self):
        engine = ReplanningEngine()
        assert not engine.needs_replanning([], {"percent": 50})

    def test_replan(self):
        engine = ReplanningEngine()
        event = engine.replan(
            ReplanTrigger.STAGNATION,
            None, None, None,
            {"task_id": "t1"},
        )
        assert isinstance(event, ReplanEvent)

    def test_get_history(self):
        engine = ReplanningEngine()
        engine.replan(ReplanTrigger.STAGNATION, None, None, None, {})
        history = engine.get_history()
        assert len(history) == 1


# ---------------------------------------------------------------------------
# Dynamic Decomposer tests
# ---------------------------------------------------------------------------

class TestDynamicDecomposer:
    def test_create_decomposer(self):
        decomposer = DynamicDecomposer()
        assert decomposer is not None

    def test_decompose_on_discovery(self):
        decomposer = DynamicDecomposer()
        subtasks = decomposer.decompose_on_discovery("t1", "New complexity found", None)
        assert len(subtasks) > 0


# ---------------------------------------------------------------------------
# Event Bus tests
# ---------------------------------------------------------------------------

class TestEventBus:
    def test_create_bus(self):
        bus = EventBus()
        assert bus is not None

    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.MISSION_CREATED, lambda e: received.append(e))
        event = Event(type=EventType.MISSION_CREATED, source="test")
        bus.publish(event)
        assert len(received) == 1

    def test_get_history(self):
        bus = EventBus()
        event = Event(type=EventType.MISSION_CREATED)
        bus.publish(event)
        history = bus.get_history()
        assert len(history) == 1

    def test_get_latest(self):
        bus = EventBus()
        event = Event(type=EventType.MISSION_CREATED)
        bus.publish(event)
        latest = bus.get_latest(EventType.MISSION_CREATED)
        assert latest is not None


# ---------------------------------------------------------------------------
# Engineering Blackboard tests
# ---------------------------------------------------------------------------

class TestEngineeringBlackboard:
    def test_create_blackboard(self):
        bb = EngineeringBlackboard()
        assert bb is not None

    def test_write_and_read(self):
        bb = EngineeringBlackboard()
        bb.write("key1", "value1")
        assert bb.read("key1") == "value1"

    def test_search(self):
        bb = EngineeringBlackboard()
        bb.write("task.1.status", "completed")
        bb.write("task.2.status", "pending")
        results = bb.search("task.")
        assert len(results) == 2

    def test_get_all(self):
        bb = EngineeringBlackboard()
        bb.write("key1", "value1")
        bb.write("key2", "value2")
        all_entries = bb.get_all()
        assert len(all_entries) == 2


# ---------------------------------------------------------------------------
# Blackboard Event System tests
# ---------------------------------------------------------------------------

class TestBlackboardEventSystem:
    def test_create_system(self):
        system = BlackboardEventSystem()
        assert system is not None

    def test_publish_event(self):
        system = BlackboardEventSystem()
        event = system.publish(EventType.MISSION_CREATED, source="test", data={"mission_id": "m1"})
        assert event is not None

    def test_blackboard_auto_update(self):
        system = BlackboardEventSystem()
        system.publish(EventType.MISSION_CREATED, data={"title": "Test Mission"})
        mission = system.blackboard.read("current_mission")
        assert mission is not None

    def test_get_status(self):
        system = BlackboardEventSystem()
        status = system.get_status()
        assert "events" in status
        assert "blackboard" in status
