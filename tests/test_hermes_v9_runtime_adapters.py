"""
HERMES INTELLIGENCE OS (v9) — RUNTIME ADAPTERS & DUAL-SUBSTRATE TEST SUITE
==========================================================================
Comprehensive empirical tests for the v9 Universal RuntimeAdapter SPI and
Dual-Substrate Architecture (LangGraph foundation + Deep Agents worker harness):
- RuntimeAdapter SPI contract & ExecutionResult properties
- LangGraphRuntimeAdapter (Durable wave-level state graph execution & checkpointing)
- DeepAgentsRuntimeAdapter (Isolated filesystem sandboxes & context containment)
- CompositeDualSubstrateAdapter (Outer LangGraph DAG + Inner Deep Agents sandboxes)
- OpenClawRuntimeAdapter & PrimeRuntimeAdapter (Edge nodes & Persistent REPL)
- RuntimeRouter (Registry, dynamic capability routing, fallback dispatch)
- HermesIntelligenceOS integration with execute_plan_with_runtime()
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from hermes_os import (
    HermesIntelligenceOS,
    CognitiveCompiler,
    ExecutionPlanIR,
    ExecutionWave,
    GoalGraph,
    GoalNode,
    # Runtime SPI & Adapters
    RuntimeAdapter,
    ExecutionResult,
    ExecutionStatus,
    LangGraphRuntimeAdapter,
    DeepAgentsRuntimeAdapter,
    CompositeDualSubstrateAdapter,
    OpenClawRuntimeAdapter,
    PrimeRuntimeAdapter,
    RuntimeRouter,
)
from hermes_os.capabilities import CapabilityKind, CapabilityManifest, ExecutionCapabilityPlan


def _create_sample_plan(mission_id: str = "m-test-runtime-01") -> ExecutionPlanIR:
    """Helper to synthesize an ExecutionPlanIR with 3 tasks across 2 waves."""
    graph = GoalGraph()
    t1 = GoalNode(goal_id="task-1", title="Gather Domain Docs", description="Research API specs")
    t2 = GoalNode(goal_id="task-2", title="Implement Worker Logic", description="Write core algorithm", depends_on=["task-1"])
    t3 = GoalNode(goal_id="task-3", title="Telemetry Verification", description="Audit proofs", depends_on=["task-1"])
    graph.add_goal(t1)
    graph.add_goal(t2)
    graph.add_goal(t3)

    waves = [
        ExecutionWave(wave_number=0, task_ids=["task-1"], can_parallelize=False),
        ExecutionWave(wave_number=1, task_ids=["task-2", "task-3"], can_parallelize=True),
    ]

    cap_plan1 = ExecutionCapabilityPlan(
        task_id="task-1",
        selected_tools=["tool.web_search"],
    )
    cap_plan2 = ExecutionCapabilityPlan(
        task_id="task-2",
        selected_tools=["tool.python_exec"],
    )
    cap_plan3 = ExecutionCapabilityPlan(
        task_id="task-3",
        selected_tools=["tool.invariant_checker"],
    )

    return ExecutionPlanIR(
        plan_id=f"plan-{mission_id}",
        mission_id=mission_id,
        objective="Empirical test of runtime substrate execution",
        task_graph=graph,
        execution_waves=waves,
        capability_plans={"task-1": cap_plan1, "task-2": cap_plan2, "task-3": cap_plan3},
        resource_budget={"max_tokens": 12000, "max_wallclock_seconds": 60.0},
    )


# =====================================================================
# 1. RuntimeAdapter SPI & ExecutionResult Tests
# =====================================================================

def test_runtime_adapter_spi_contract():
    """Verify that RuntimeAdapter enforces interface contract via abc."""
    # Attempting to instantiate RuntimeAdapter directly without abstract methods must raise TypeError
    with pytest.raises(TypeError):
        RuntimeAdapter()  # type: ignore

    # Verify ExecutionResult data integrity
    res = ExecutionResult(
        mission_id="m-test-01",
        runtime_id="mock_runtime",
        status=ExecutionStatus.COMPLETED,
        completed_tasks=["t1", "t2"],
        checkpoints_created=["chk-01"],
        tokens_consumed=1500,
        elapsed_seconds=0.452,
        proof={"verified": True},
        artifacts_produced=["artifact1.json"],
    )

    assert res.is_success is True
    res_dict = res.to_dict()
    assert res_dict["mission_id"] == "m-test-01"
    assert res_dict["status"] == "completed"
    assert res_dict["checkpoints"] == ["chk-01"]
    assert res_dict["tokens_consumed"] == 1500
    assert res_dict["artifacts"] == ["artifact1.json"]

    # Test failure status
    res_failed = ExecutionResult(
        mission_id="m-test-02",
        runtime_id="mock_runtime",
        status=ExecutionStatus.FAILED,
    )
    assert res_failed.is_success is False


# =====================================================================
# 2. LangGraph Runtime Adapter Tests
# =====================================================================

@pytest.mark.asyncio
async def test_langgraph_runtime_adapter():
    """Verify LangGraph substrate executes waves with durable checkpoints."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = LangGraphRuntimeAdapter(workspace_root=tmp_dir)
        assert adapter.runtime_id == "langgraph"
        assert "LangGraph" in adapter.description

        plan = _create_sample_plan("m-langgraph-01")

        # 1. Substrate Compilation
        substrate = await adapter.compile_execution_substrate(plan)
        assert substrate is not None
        assert len(substrate.nodes) == 3

        # 2. Execution to Completion
        res = await adapter.execute_plan(plan)
        assert res.is_success is True
        assert res.status == ExecutionStatus.COMPLETED
        assert set(res.completed_tasks) == {"task-1", "task-2", "task-3"}
        assert len(res.checkpoints_created) == 2  # 1 checkpoint per wave
        assert res.proof.get("verified") is True
        assert res.proof.get("tier") == "L5_compiler_proof"
        assert len(res.artifacts_produced) >= 1

        # 3. Pause & Resume Flow
        pause_ok = await adapter.pause("m-langgraph-01", reason="External intervention")
        assert pause_ok is True

        res_paused = await adapter.execute_plan(plan)
        assert res_paused.status == ExecutionStatus.PAUSED

        res_resumed = await adapter.resume("m-langgraph-01")
        assert res_resumed.status == ExecutionStatus.COMPLETED


# =====================================================================
# 3. Deep Agents Runtime Adapter Tests
# =====================================================================

@pytest.mark.asyncio
async def test_deep_agents_runtime_adapter():
    """Verify Deep Agents substrate executes in isolated filesystem sandboxes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = DeepAgentsRuntimeAdapter(workspace_root=tmp_dir)
        assert adapter.runtime_id == "deep_agents"
        assert "Deep Agents" in adapter.description

        plan = _create_sample_plan("m-deepagents-01")

        # 1. Substrate Compilation (isolated workspaces spawned)
        workspaces = await adapter.compile_execution_substrate(plan)
        assert len(workspaces) == 3
        for gid, ws in workspaces.items():
            assert Path(ws.workspace_dir).exists()
            assert ws.task_id == gid
            assert ws.context_package is not None

        # 2. Execution to Completion
        res = await adapter.execute_plan(plan)
        assert res.is_success is True
        assert res.status == ExecutionStatus.COMPLETED
        assert set(res.completed_tasks) == {"task-1", "task-2", "task-3"}
        assert len(res.artifacts_produced) == 3
        # Ensure produced artifacts are real files inside subagent sandboxes
        for art_path in res.artifacts_produced:
            assert Path(art_path).exists()
            assert "subagent_sandboxes" in art_path

        # 3. Pause & Resume Flow
        await adapter.pause("m-deepagents-01")
        res_paused = await adapter.execute_plan(plan)
        assert res_paused.status == ExecutionStatus.PAUSED

        res_resumed = await adapter.resume("m-deepagents-01")
        assert res_resumed.status == ExecutionStatus.COMPLETED


# =====================================================================
# 4. Composite Dual-Substrate Adapter Tests
# =====================================================================

@pytest.mark.asyncio
async def test_composite_dual_substrate_adapter():
    """Verify synergy: LangGraph outer wave DAG + Deep Agents inner worker sandboxes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = CompositeDualSubstrateAdapter(workspace_root=tmp_dir)
        assert adapter.runtime_id == "composite_dual_substrate"
        assert "Dual-Substrate" in adapter.description

        plan = _create_sample_plan("m-composite-01")

        # 1. Dual Substrate Compilation
        substrate = await adapter.compile_execution_substrate(plan)
        assert "state_graph" in substrate
        assert "workspaces" in substrate
        assert len(substrate["workspaces"]) == 3

        # 2. Execution
        res = await adapter.execute_plan(plan)
        assert res.is_success is True
        assert res.status == ExecutionStatus.COMPLETED
        assert set(res.completed_tasks) == {"task-1", "task-2", "task-3"}
        assert len(res.checkpoints_created) == 2  # Wave 0 and Wave 1 checkpoints
        assert len(res.artifacts_produced) == 3
        assert res.metadata.get("waves_executed") == 2
        assert res.metadata.get("sandboxes_active") == 3
        assert res.proof.get("verified") is True

        # Check that individual task json artifacts exist in sandboxes
        for art in res.artifacts_produced:
            assert Path(art).exists()
            content = Path(art).read_text(encoding="utf-8")
            assert "verified" in content

        # 3. Pause & Resume Flow
        await adapter.pause("m-composite-01")
        res_resumed = await adapter.resume("m-composite-01")
        assert res_resumed.status == ExecutionStatus.COMPLETED
        assert res_resumed.runtime_id == "composite_dual_substrate"


# =====================================================================
# 5. OpenClaw & Prime Runtime Adapters Tests
# =====================================================================

@pytest.mark.asyncio
async def test_openclaw_and_prime_adapters():
    """Verify OpenClaw node bridge and Prime REPL runtime adapters."""
    plan = _create_sample_plan("m-other-01")

    # OpenClaw
    oc = OpenClawRuntimeAdapter()
    assert oc.runtime_id == "openclaw"
    assert "OpenClaw" in oc.description
    oc_res = await oc.execute_plan(plan)
    assert oc_res.is_success is True
    assert oc_res.proof.get("tier") == "L3_node_crosscheck"

    # Prime REPL
    prime = PrimeRuntimeAdapter()
    assert prime.runtime_id == "prime"
    assert "Prime" in prime.description
    prime_res = await prime.execute_plan(plan)
    assert prime_res.is_success is True
    assert prime_res.proof.get("tier") == "L5_repl_execution"


# =====================================================================
# 6. RuntimeRouter Dynamic Routing & Execution Tests
# =====================================================================

@pytest.mark.asyncio
async def test_runtime_router():
    """Verify RuntimeRouter registers adapters and dynamically routes plans."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        router = RuntimeRouter(workspace_root=tmp_dir)

        # 1. Registered Adapters
        adapters = router.list_adapters()
        runtime_ids = [a["runtime_id"] for a in adapters]
        assert "composite_dual_substrate" in runtime_ids
        assert "langgraph" in runtime_ids
        assert "deep_agents" in runtime_ids
        assert "openclaw" in runtime_ids
        assert "prime" in runtime_ids

        # 2. Auto-routing general plan -> Composite Dual-Substrate
        plan = _create_sample_plan("m-route-01")
        routed_adapter = router.route(plan)
        assert routed_adapter.runtime_id == "composite_dual_substrate"

        # 3. Auto-routing persistent REPL plan -> Prime
        repl_plan = _create_sample_plan("m-repl-01")
        # Set REPL tool and single goal
        repl_plan.capability_plans["task-1"].selected_tools = ["tool.python_repl"]
        # Limit tasks to 1
        repl_plan.task_graph._nodes = {"task-1": repl_plan.task_graph._nodes["task-1"]}
        routed_prime = router.route(repl_plan)
        assert routed_prime.runtime_id == "prime"

        # 4. Explicit Runtime Execution via router
        res_lg = await router.execute_plan(plan, runtime_id="langgraph")
        assert res_lg.runtime_id == "langgraph"
        assert res_lg.is_success is True

        res_da = await router.execute_plan(plan, runtime_id="deep_agents")
        assert res_da.runtime_id == "deep_agents"
        assert res_da.is_success is True

        # 5. Invalid runtime ID handling
        with pytest.raises(ValueError, match="Unknown runtime adapter"):
            await router.execute_plan(plan, runtime_id="non_existent_engine")


# =====================================================================
# 7. Hermes Intelligence OS v9 Runtime Integration
# =====================================================================

@pytest.mark.asyncio
async def test_hermes_intelligence_os_dual_substrate_integration():
    """Verify full OS kernel integration with RuntimeRouter and Dual-Substrate execution."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        os_kernel = HermesIntelligenceOS(workspace_root=tmp_dir)

        # Verify router initialized on kernel
        assert isinstance(os_kernel.runtime_router, RuntimeRouter)

        # 1. Direct plan execution with explicit runtime
        plan_ir = os_kernel.compile_mission(
            request="Deploy self-monitoring microservices cluster",
            invariants=["zero crash loop", "high availability"],
            risk_level="low",
        )
        res = await os_kernel.execute_plan_with_runtime(plan_ir, runtime_id="composite_dual_substrate")
        assert res.is_success is True
        assert res.runtime_id == "composite_dual_substrate"
        assert len(res.completed_tasks) >= 1

        # 2. End-to-End Mission execution through OS
        mission_out = await os_kernel.execute_mission(
            request="Deploy self-monitoring microservices cluster",
            invariants=["zero crash loop", "high availability"],
            risk_level="low",
        )

        assert mission_out["status"] == "completed"
        assert "runtime_result" in mission_out
        runtime_res = mission_out["runtime_result"]
        assert runtime_res["status"] == "completed"
        assert runtime_res["runtime_id"] == "composite_dual_substrate"
        assert len(runtime_res["completed_tasks"]) >= 1
        assert "checkpoints" in runtime_res
