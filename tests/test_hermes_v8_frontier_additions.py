"""
HERMES INTELLIGENCE OS (v8) — FRONTIER ADDITIONS TEST SUITE
============================================================
Tests the 5 advanced architectural capabilities inspired by:
- Claude Code: Deterministic lifecycle hooks (Pre/Post tool, Git safety, secret scrubbing)
- OpenClaw 2.0: Gateway, Heartbeat vs Task separation, Device Node Registry, ACP Bridge
- Kimi K3: Swarm horizontal scaling & Evidence Compression Engine
- Long-Horizon Autonomy: Environment Drift & Goal Drift Detectors
- VISTA: Lossless Multi-Modal Perception Store & Experience Replay
- End-to-End Hermes Intelligence OS v8 Integration
"""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest

from hermes_os import (
    # Swarm
    AggregatedEvidencePacket,
    # Gateway
    DeviceNode,
    # Drift
    DriftSeverity,
    EnvironmentDriftDetector,
    EvidenceCompressor,
    ExternalHarnessBridge,
    ExternalHarnessType,
    GoalDriftDetector,
    HeartbeatMonitor,
    HermesIntelligenceOS,
    # Hooks
    HookAction,
    HookEventType,
    HookManager,
    HookResult,
    KimiSwarmScaler,
    LifecycleHook,
    # Perception
    LosslessPerceptionStore,
    NodeRegistry,
    NodeStatus,
    NodeType,
    OpenClawGateway,
    PerceptionModality,
    SwarmTask,
    SwarmWorkerResult,
    SwarmWorkerRole,
)

# =====================================================================
# 1. Deterministic Lifecycle Hooks (Claude Code Inspired)
# =====================================================================

def test_hook_manager_registration_and_priority():
    manager = HookManager(register_defaults=False)
    order = []

    def hook_low_prio(payload):
        order.append("low")
        return HookResult(action=HookAction.CONTINUE)

    def hook_high_prio(payload):
        order.append("high")
        return HookResult(action=HookAction.CONTINUE)

    manager.register(LifecycleHook(
        name="low",
        event_type=HookEventType.PRE_TOOL_USE,
        handler=hook_low_prio,
        priority=100,
    ))
    manager.register(LifecycleHook(
        name="high",
        event_type=HookEventType.PRE_TOOL_USE,
        handler=hook_high_prio,
        priority=10,
    ))

    res = manager.dispatch(HookEventType.PRE_TOOL_USE, {"command": "test"})
    assert not res.is_blocked
    assert order == ["high", "low"]


def test_git_safety_hook_blocks_destructive_command():
    manager = HookManager(register_defaults=True)

    # Benign command
    safe_res = manager.dispatch(HookEventType.PRE_TOOL_USE, {"command": "git status"})
    assert not safe_res.is_blocked

    # Destructive commands
    blocked_res1 = manager.dispatch(HookEventType.PRE_TOOL_USE, {"command": "git reset --hard HEAD~1"})
    assert blocked_res1.is_blocked
    assert "GitSafetyHook" in blocked_res1.reason

    blocked_res2 = manager.dispatch(HookEventType.PRE_TOOL_USE, {"command": "git push origin main --force"})
    assert blocked_res2.is_blocked


def test_secret_scrubber_hook_redacts_credentials():
    manager = HookManager(register_defaults=True)
    raw_payload = {
        "output": "Authorized with sk-1234567890abcdef12345678 and token ghp_abcdef1234567890abcdef12345678",
        "nested": {"key": "Bearer my_super_secret_bearer_token_12345"},
    }

    res = manager.dispatch(HookEventType.POST_TOOL_USE, raw_payload)
    assert res.action == HookAction.MODIFY
    assert res.modified_payload is not None

    scrubbed = res.modified_payload["output"]
    assert "[REDACTED_OPENAI_KEY]" in scrubbed
    assert "[REDACTED_GITHUB_TOKEN]" in scrubbed
    assert "sk-123456" not in scrubbed

    nested_scrubbed = res.modified_payload["nested"]["key"]
    assert "[REDACTED_BEARER_TOKEN]" in nested_scrubbed


# =====================================================================
# 2. OpenClaw 2.0 Gateway & Node Abstraction
# =====================================================================

def test_node_registry_routing():
    registry = NodeRegistry()
    assert len(registry.list_nodes()) >= 1  # Default local host

    cloud_gpu_node = DeviceNode(
        node_id="node-cloud-gpu",
        node_type=NodeType.CLOUD_VM,
        platform="linux",
        capabilities=["python", "bash", "gpu", "docker"],
        status=NodeStatus.ONLINE,
        cpu_cores=32,
        memory_gb=64.0,
        has_gpu=True,
    )
    registry.register_node(cloud_gpu_node)

    best = registry.find_best_node(required_capabilities=["gpu"], prefer_gpu=True)
    assert best is not None
    assert best.node_id == "node-cloud-gpu"
    assert best.has_gpu is True


def test_heartbeat_attention_poll():
    monitor = HeartbeatMonitor()
    # Idle state
    poll = monitor.poll_attention(active_tasks_count=0)
    assert poll.needs_attention is False
    assert poll.health_ok is True

    # Register trigger and pending approval
    monitor.submit_pending_approval("approval-delete-file-42")
    poll2 = monitor.poll_attention()
    assert poll2.needs_attention is True
    assert "approval-delete-file-42" in poll2.pending_approvals

    # Resolve approval
    assert monitor.resolve_pending_approval("approval-delete-file-42") is True
    poll3 = monitor.poll_attention()
    assert poll3.needs_attention is False


def test_external_harness_bridge_acp():
    registry = NodeRegistry()
    bridge = ExternalHarnessBridge(node_registry=registry)

    session = bridge.launch_harness(
        harness_type=ExternalHarnessType.CLAUDE_CODE,
        objective="Analyze codebase dependencies",
    )
    assert session.status == "running"
    assert "acp-claude_code" in session.session_id

    # Mid-turn steering
    steered = bridge.steer_harness(session.session_id, "Focus on async submodules first")
    assert steered is True
    assert any("Focus on async" in log for log in session.telemetry_logs)

    # Complete session
    completed = bridge.complete_harness(session.session_id, {"result": "dependencies_mapped"})
    assert completed is True
    assert session.status == "completed"
    assert session.result_data["result"] == "dependencies_mapped"


# =====================================================================
# 3. Kimi K3 Swarm Horizontal Scaling & Evidence Compression
# =====================================================================

@pytest.mark.asyncio
async def test_kimi_swarm_scaling_and_compression():
    scaler = KimiSwarmScaler(max_concurrency=10)

    tasks = [
        SwarmTask(
            task_id=f"t-{i}",
            role=SwarmWorkerRole.SEARCH_WORKER,
            instruction=f"Investigate module pattern {i}",
        )
        for i in range(12)
    ]

    async def custom_worker(task: SwarmTask) -> str:
        await asyncio.sleep(0.01)
        return (
            f"Factual finding for {task.instruction}. The architecture pattern {task.task_id} "
            f"is verified and fully operational. Zero regressions were detected."
        )

    packet: AggregatedEvidencePacket = await scaler.dispatch_swarm(
        mission_id="mission-swarm-test",
        tasks=tasks,
        worker_func=custom_worker,
    )

    assert packet.total_workers_dispatched == 12
    assert len(packet.verified_claims) > 0
    assert packet.compression_ratio <= 1.0
    summary = packet.to_context_summary()
    assert "### Swarm Evidence Brief" in summary
    assert "Claim" in summary


def test_evidence_compressor_conflict_detection():
    compressor = EvidenceCompressor()
    results = [
        SwarmWorkerResult(
            task_id="t1",
            worker_id="w1",
            role=SwarmWorkerRole.FACT_CHECKER,
            raw_output="The package version 2.0 is verified and nominal in production.",
        ),
        SwarmWorkerResult(
            task_id="t2",
            worker_id="w2",
            role=SwarmWorkerRole.FACT_CHECKER,
            raw_output="Warning: package version 2.0 is deprecated and conflicts with python 3.12.",
        ),
    ]

    packet = compressor.compress("test-conflicts", results)
    assert len(packet.verified_claims) >= 1
    assert len(packet.unresolved_conflicts) >= 1
    assert "conflicts with" in packet.unresolved_conflicts[0]


# =====================================================================
# 4. Environment & Goal Drift Detectors
# =====================================================================

def test_environment_drift_detection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        req_file = os.path.join(tmp_dir, "requirements.txt")
        with open(req_file, "w", encoding="utf-8") as f:
            f.write("pytest==8.0.0\n")

        detector = EnvironmentDriftDetector(workspace_root=tmp_dir)
        fp1 = detector.capture_fingerprint()
        assert "requirements.txt" in fp1.critical_file_hashes

        # No drift initially
        report_clean = detector.detect_drift(fp1)
        assert report_clean.severity == DriftSeverity.NONE
        assert report_clean.is_safe_to_resume is True

        # Modify file
        with open(req_file, "w", encoding="utf-8") as f:
            f.write("pytest==9.0.2\nanyio==4.12.0\n")

        report_modified = detector.detect_drift(fp1)
        assert report_modified.severity in [DriftSeverity.LOW, DriftSeverity.HIGH]
        assert "requirements.txt" in report_modified.modified_files


def test_goal_drift_detector():
    detector = GoalDriftDetector(warning_threshold=0.3, critical_threshold=0.6)

    # Nominal steps aligned with objective
    alert_nominal = detector.evaluate(
        objective="Implement database cache layer",
        invariants=["preserve tests", "no deletion of existing tables"],
        completed_steps=[
            {"action": "create_cache_table", "description": "Create redis database cache layer"},
        ],
        pending_steps=[],
    )
    assert alert_nominal.alert_level == "NOMINAL"
    assert alert_nominal.drift_score < 0.3

    # Derailed steps violating invariant and off-objective
    alert_derailed = detector.evaluate(
        objective="Implement database cache layer",
        invariants=["no deletion of existing tables"],
        completed_steps=[
            {"action": "delete_all_tables", "description": "Delete all existing schema tables and format disk"},
        ],
        pending_steps=[
            {"action": "play_music", "description": "Play unrelated background audio"},
        ],
    )
    assert alert_derailed.alert_level == "INTERVENTION_REQUIRED"
    assert len(alert_derailed.violated_invariants) > 0


# =====================================================================
# 5. VISTA Lossless Multi-Modal Perception Store
# =====================================================================

def test_lossless_perception_store_and_replay():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = LosslessPerceptionStore(workspace_root=tmp_dir, persist_to_disk=True)

        rec1 = store.record_perception(
            mission_id="m-vista-001",
            action_id="act-terminal-exec",
            modality=PerceptionModality.TERMINAL_STREAM,
            raw_content="python -m pytest tests/test_hermes.py\n24 passed in 0.5s",
        )
        rec2 = store.record_perception(
            mission_id="m-vista-001",
            action_id="act-ui-click",
            modality=PerceptionModality.SCREENSHOT,
            raw_content="<base64_encoded_png_bytes_sample>",
            metadata={"width": 1920, "height": 1080},
        )

        assert rec1.modality == PerceptionModality.TERMINAL_STREAM
        assert rec2.modality == PerceptionModality.SCREENSHOT

        # Retrieve by action
        act_recs = store.get_by_action("act-terminal-exec")
        assert len(act_recs) == 1
        assert act_recs[0].perception_id == rec1.perception_id

        # Experience Replay
        replay = store.replay_experience("m-vista-001")
        assert len(replay) == 2
        assert replay[0]["modality"] in ["terminal_stream", "screenshot"]


# =====================================================================
# 6. Full Hermes Intelligence OS v8 Integration
# =====================================================================

@pytest.mark.asyncio
async def test_hermes_intelligence_os_frontier_integration():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os_kernel = HermesIntelligenceOS(workspace_root=tmp_dir)

        # Verify frontier subsystems are loaded
        assert isinstance(os_kernel.hooks, HookManager)
        assert isinstance(os_kernel.gateway, OpenClawGateway)
        assert isinstance(os_kernel.swarm_scaler, KimiSwarmScaler)
        assert isinstance(os_kernel.drift_detector, EnvironmentDriftDetector)
        assert isinstance(os_kernel.goal_drift_detector, GoalDriftDetector)
        assert isinstance(os_kernel.perception_store, LosslessPerceptionStore)

        # Execute mission with invariants
        result = await os_kernel.execute_mission(
            request="Integrate resilient telemetry monitor",
            invariants=["zero deletion", "preserve verified claims"],
            risk_level="low",
        )

        assert result["status"] == "completed"
        assert result["goal_drift"] == "NOMINAL"
        assert result["perceptions_count"] >= 1
        assert result["hooks_executed"] >= 1
