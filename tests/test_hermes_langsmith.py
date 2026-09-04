"""
HERMES INTELLIGENCE OS — LANGSMITH TELEMETRY TEST SUITE
=======================================================
Comprehensive empirical tests for LangSmith integration:
- LangSmithConfig and environment detection
- Secret scrubbing and credential redaction (Plane 03 Safety Invariant)
- LocalTraceSpan and RunTree creation
- Mission, Wave, and Subagent Worker span lifecycles
- Universal Event Bus automatic subscription
- LangGraph and Composite Dual-Substrate runtime adapter tracing
- Hermes Intelligence OS kernel integration
- Feedback and evaluation recording
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from hermes_os import (
    HermesIntelligenceOS,
    HermesEvent,
    EventSource,
    UniversalEventBus,
    LangSmithConfig,
    LangSmithTelemetryExporter,
    LocalTraceSpan,
    LangGraphRuntimeAdapter,
    CompositeDualSubstrateAdapter,
    DeepAgentsRuntimeAdapter,
    GoalGraph,
    GoalNode,
    ExecutionWave,
    ExecutionPlanIR,
)
from hermes_os.capabilities import ExecutionCapabilityPlan


def _sample_plan(mission_id: str = "m-ls-01") -> ExecutionPlanIR:
    graph = GoalGraph()
    t1 = GoalNode(goal_id="task-1", title="Analyze Codebase", description="Scan AST")
    t2 = GoalNode(goal_id="task-2", title="Apply Optimization", description="Refactor functions", depends_on=["task-1"])
    graph.add_goal(t1)
    graph.add_goal(t2)

    waves = [
        ExecutionWave(wave_number=0, task_ids=["task-1"], can_parallelize=False),
        ExecutionWave(wave_number=1, task_ids=["task-2"], can_parallelize=False),
    ]

    return ExecutionPlanIR(
        plan_id=f"plan-{mission_id}",
        mission_id=mission_id,
        objective="LangSmith Telemetry Trace Verification",
        task_graph=graph,
        execution_waves=waves,
        capability_plans={
            "task-1": ExecutionCapabilityPlan(task_id="task-1", selected_tools=["tool.ast_scan"]),
            "task-2": ExecutionCapabilityPlan(task_id="task-2", selected_tools=["tool.code_edit"]),
        },
    )


# =====================================================================
# 1. Configuration and Defaults
# =====================================================================

def test_langsmith_config():
    """Verify LangSmithConfig defaults and environment loader."""
    cfg = LangSmithConfig()
    assert cfg.enabled is False
    assert cfg.project_name == "hermes-asi-master"
    assert cfg.scrub_secrets is True
    assert cfg.local_fallback is True

    from_env = LangSmithConfig.from_env()
    assert isinstance(from_env, LangSmithConfig)
    assert from_env.scrub_secrets is True


# =====================================================================
# 2. Secret Scrubbing & Privacy Redaction (Plane 03 Safety Invariant)
# =====================================================================

def test_secret_scrubber_redaction():
    """Verify that credentials and sensitive tokens are redacted before export."""
    exporter = LangSmithTelemetryExporter(config=LangSmithConfig(enabled=False, scrub_secrets=True))

    leakage_payload = {
        "api_key": "sk-123456789012345678901234567890",
        "github_pat": "ghp_abcdefghijklmnopqrstuvwx1234",
        "langsmith_key": "ls__secrettoken123456789012345",
        "auth_header": "Bearer secretbearercredentialvalue12345",
        "db_config": "password='supersecretpass'",
        "normal_text": "This is benign instruction text",
        "nested": {
            "token": "sk-99999999999999999999999999999",
            "list_of_secrets": ["ghp_0000000000000000000000000000"],
        },
    }

    scrubbed = exporter._scrub_payload(leakage_payload)

    assert "sk-123456789012345678901234567890" not in str(scrubbed)
    assert "[REDACTED_OPENAI_KEY]" in scrubbed["api_key"]
    assert "[REDACTED_GITHUB_TOKEN]" in scrubbed["github_pat"]
    assert "[REDACTED_LANGSMITH_KEY]" in scrubbed["langsmith_key"]
    assert "[REDACTED_BEARER_TOKEN]" in scrubbed["auth_header"]
    assert "[REDACTED_PASSWORD]" in scrubbed["db_config"]
    assert scrubbed["normal_text"] == "This is benign instruction text"
    assert "[REDACTED_OPENAI_KEY]" in scrubbed["nested"]["token"]
    assert "[REDACTED_GITHUB_TOKEN]" in scrubbed["nested"]["list_of_secrets"][0]


# =====================================================================
# 3. Mission, Wave, and Worker Trace Lifecycle
# =====================================================================

def test_trace_lifecycle_spans():
    """Verify root mission, wave, and subagent worker trace spans."""
    exporter = LangSmithTelemetryExporter(config=LangSmithConfig(enabled=False))

    # 1. Start root mission trace
    root_span = exporter.start_mission_trace("m-test-100", "Execute security review")
    assert root_span is not None

    # 2. Start Wave 0 span
    wave_span = exporter.start_wave_span("m-test-100", 0, ["task-1", "task-2"])
    assert wave_span is not None

    # 3. Start Subagent Worker span
    worker_span = exporter.start_worker_span(
        "m-test-100",
        "worker-01",
        "task-1",
        role="security_analyst",
        sandbox_dir=".hermes/subagent_sandboxes/m-test-100/worker-01",
    )
    assert worker_span is not None

    # 4. End Worker and Wave spans
    exporter.end_worker_span("m-test-100", "worker-01", artifacts=["vuln_report.json"])
    exporter.end_wave_span("m-test-100", 0, completed_tasks=["task-1", "task-2"], checkpoint_id="ckpt-w0")

    # 5. End root mission trace
    res = exporter.end_mission_trace(
        "m-test-100",
        status="completed",
        proof={"verified": True, "tier": "L5"},
        artifacts=["vuln_report.json"],
    )
    assert res is not None
    assert res["status"] == "completed"

    completed = exporter.get_completed_traces()
    assert len(completed) >= 1


# =====================================================================
# 4. Universal Event Bus Integration
# =====================================================================

def test_event_bus_automatic_tracing():
    """Verify exporter automatically reacts to UniversalEventBus events."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        bus = UniversalEventBus(workspace_root=tmp_dir)
        exporter = LangSmithTelemetryExporter(
            config=LangSmithConfig(enabled=False),
            event_bus=bus,
        )

        # Publish mission.started
        bus.publish(HermesEvent(
            event_type="mission.started",
            source=EventSource.CLI,
            payload={"mission_id": "m-bus-01", "request": "Deploy cache service"},
        ))

        assert "m-bus-01" in exporter._active_mission_runs

        # Publish mission.completed
        bus.publish(HermesEvent(
            event_type="mission.completed",
            source=EventSource.SYSTEM,
            payload={"mission_id": "m-bus-01", "status": "completed"},
        ))

        assert "m-bus-01" not in exporter._active_mission_runs
        traces = exporter.get_completed_traces()
        assert len(traces) == 1
        assert traces[0]["status"] == "completed"


# =====================================================================
# 5. Runtime Adapters with LangSmith Telemetry
# =====================================================================

@pytest.mark.asyncio
async def test_runtime_adapters_with_langsmith():
    """Verify LangGraph and Composite Dual-Substrate adapters trace execution to LangSmith."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        exporter = LangSmithTelemetryExporter(config=LangSmithConfig(enabled=False))
        adapter = CompositeDualSubstrateAdapter(workspace_root=tmp_dir, exporter=exporter)

        plan = _sample_plan("m-composite-trace-01")
        res = await adapter.execute_plan(plan)

        assert res.is_success is True
        traces = exporter.get_completed_traces()
        assert len(traces) >= 1
        last_trace = traces[-1]
        assert last_trace["status"] == "completed"
        # Check artifacts recorded in trace
        assert len(last_trace["outputs"]["artifacts"]) == 2


# =====================================================================
# 6. Hermes Intelligence OS Kernel Integration
# =====================================================================

@pytest.mark.asyncio
async def test_hermes_intelligence_os_langsmith_integration():
    """Verify kernel initializes exporter and records mission telemetry."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        os_kernel = HermesIntelligenceOS(workspace_root=tmp_dir)
        assert isinstance(os_kernel.langsmith_exporter, LangSmithTelemetryExporter)

        # Execute mission
        out = await os_kernel.execute_mission(
            request="Verify LangSmith telemetry exporter in Hermes OS",
            invariants=["zero leakage"],
            risk_level="low",
        )

        assert out["status"] == "completed"
        assert "runtime_result" in out
        traces = os_kernel.langsmith_exporter.get_completed_traces()
        assert len(traces) >= 1


# =====================================================================
# 7. Feedback and Evaluation Logging
# =====================================================================

def test_record_feedback():
    """Verify feedback logging interface."""
    exporter = LangSmithTelemetryExporter(config=LangSmithConfig(enabled=False))
    ok = exporter.record_feedback(
        run_id="run-test-01",
        key="correctness",
        score=0.98,
        comment="Deterministic AST invariant verification passed with secret sk-12345678901234567890",
    )
    assert ok is True
