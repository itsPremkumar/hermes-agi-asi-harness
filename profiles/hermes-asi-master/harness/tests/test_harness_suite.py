#!/usr/bin/env python3
"""
test_harness_suite.py — Comprehensive Pytest Validation for Hermes AGI/ASI Harness
Validates all 8 subsystems: Kernel, Plugins, Supervisor, Memory, Sandbox, Verifier, JIT, and Benchmarks.
"""

import sys
import pathlib
import pytest

# Add parent dir to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from src.kernel.event_bus import EventBus, Event
from src.kernel.model_router import ModelRouter, DeterministicSimulationAdapter
from src.kernel.state_store import TransactionalStateStore
from src.kernel.agent_loop import AgentKernelLoop
from src.plugins.manifest_schema import PluginManifest, ToolContract, PermissionLevel
from src.plugins.plugin_manager import PluginManager, BasePlugin
from src.orchestration.goal_engine import GoalEngine, Goal, TaskStatus
from src.orchestration.supervisor import AgentSupervisor, SpecialistRole
from src.memory.hybrid_memory import HybridMemoryStore, MemoryType, MemoryEntry
from src.memory.world_model import WorldModel
from src.environment.sandbox import ExecutionSandbox
from src.reliability.verifier import ReliabilityVerifier
from src.reliability.critic import RedTeamCritic
from src.evolution.jit_harness import JITHarnessGenerator
from src.evolution.gepa_optimizer import GEPAOptimizer
from src.benchmarks.benchmark_engine import BenchmarkEngine

# 1. Kernel Tests
def test_event_bus_pub_sub_and_history():
    bus = EventBus()
    received = []

    def handler(evt: Event):
        received.append(evt.payload.get("data"))

    bus.subscribe("tool.*", handler)
    bus.emit("tool.execute", {"data": "calc_v1"})
    bus.emit("agent.step", {"data": "step_1"})

    assert len(received) == 1
    assert received[0] == "calc_v1"
    assert len(bus.get_history()) == 2

def test_model_router_zero_cost_fallback():
    router = ModelRouter(zero_cost_only=True)
    resp = router.route("Decompose this architecture into 3 subtasks")
    assert resp is not None
    assert resp.cost_usd == 0.0
    assert len(resp.content) > 0

def test_transactional_state_store_snapshot_rollback():
    store = TransactionalStateStore()
    store.set("stage", "phase_1")
    store.set("active_agents", ["agent_a", "agent_b"])

    snap_id = store.create_snapshot("initial_phase")

    # Mutate state
    store.set("stage", "phase_2_corrupted")
    store.delete("active_agents")
    assert store.get("stage") == "phase_2_corrupted"
    assert store.get("active_agents") is None

    # Rollback
    ok = store.rollback_to_snapshot(snap_id)
    assert ok is True
    assert store.get("stage") == "phase_1"
    assert store.get("active_agents") == ["agent_a", "agent_b"]

def test_agent_kernel_loop_execution():
    loop = AgentKernelLoop(max_steps=5)
    loop.register_tool("echo_tool", lambda args: f"Echo: {args.get('text')}")
    res = loop.run(task="Test echo capability")
    assert res["success"] is True
    assert res["steps"] >= 1

# 2. Plugin Tests
def test_plugin_manifest_validation_and_hooks():
    manifest = PluginManifest(
        name="crypto_audit_plugin",
        version="1.0.0",
        description="Cryptographic auditor",
        permission_ring=PermissionLevel.R2_LOCAL_SANDBOX_WRITE,
        capabilities=["merkle_tree", "sha256"]
    )
    plugin = BasePlugin(manifest)
    pm = PluginManager()
    assert pm.register_plugin(plugin) is True
    assert pm.has_capability("merkle_tree") is True
    assert len(pm.list_plugins()) == 1

# 3. Orchestration Tests
def test_goal_engine_dag_decomposition_and_resolution():
    engine = GoalEngine()
    goal = engine.create_goal("Autonomous Trading System", "Build trading engine")
    tasks = engine.auto_decompose(goal)

    assert len(tasks) == 4
    ready_initial = engine.get_ready_tasks(goal)
    assert len(ready_initial) == 1
    assert ready_initial[0].id == "task_1_research"

    # Complete task 1 -> Unlocks task 2
    engine.complete_task(goal, "task_1_research", result="Research complete")
    ready_step2 = engine.get_ready_tasks(goal)
    assert len(ready_step2) == 1
    assert ready_step2[0].id == "task_2_architecture"

def test_agent_supervisor_multi_role_execution():
    supervisor = AgentSupervisor()
    goal = GoalEngine().create_goal("Quick Test Goal", "Verify supervisor dispatching")
    GoalEngine().auto_decompose(goal)
    res = supervisor.execute_goal(goal)
    assert res["success"] is True
    assert len(res["trace"]) == 4

# 4. Memory & World Model Tests
def test_hybrid_memory_9_types_and_fts_search():
    mem = HybridMemoryStore()
    mem.remember(
        memory_type=MemoryType.FAILURE,
        title="ZeroDivisionInSizer",
        content="Encountered division by zero when volatility was zero. Fixed with max(0.001, vol).",
        tags=["risk", "math", "bug"]
    )
    mem.remember(
        memory_type=MemoryType.SEMANTIC,
        title="VolatilityParityTheory",
        content="Volatility parity balances risk contribution equally across asset classes.",
        tags=["finance", "math"]
    )

    failures = mem.retrieve_by_type(MemoryType.FAILURE)
    assert len(failures) == 1
    assert failures[0].title == "ZeroDivisionInSizer"

    search_res = mem.search("division by zero")
    assert len(search_res) >= 1
    assert "ZeroDivisionInSizer" in [s.title for s in search_res]

def test_world_model_causal_prediction():
    wm = WorldModel()
    wm.upsert_entity("portfolio_1", "trading_portfolio", {"cash": 100000.0, "risk_mode": "active"})
    wm.add_causal_link(
        cause="market_flash_crash",
        effect="trigger_emergency_liquidation",
        strength=0.99,
        description="Flash crash automatically causes cash lock"
    )

    effects = wm.predict_effects("market_flash_crash")
    assert len(effects) == 1
    assert effects[0].effect == "trigger_emergency_liquidation"

# 5. Environment & Sandbox Tests
def test_sandbox_execution_and_isolation():
    sandbox = ExecutionSandbox()
    res = sandbox.run_python_code("print(sum([10, 20, 30]))")
    assert res.exit_code == 0
    assert "60" in res.stdout

# 6. Reliability & Verifier Tests
def test_reliability_verifier_ast_and_secrets():
    verifier = ReliabilityVerifier()

    # Valid code
    v1 = verifier.verify_python_code("def add(a, b):\n    return a + b\n")
    assert v1.passed is True

    # Syntax error
    v2 = verifier.verify_python_code("def broken_func(\n")
    assert v2.passed is False

    # Secret token leak detection
    v3 = verifier.verify_python_code("API_KEY = 'sk-1234567890abcdef1234567890'\n")
    assert v3.passed is False

# 7. Evolution & JIT Tests
def test_jit_harness_and_gepa_evolution():
    jit = JITHarnessGenerator()
    p_code = jit.analyze_task("Write a Python script for testing crypto hashes")
    assert p_code.domain == "software_engineering"
    assert p_code.recommended_temperature == 0.1

    gepa = GEPAOptimizer("Base system instruction.")
    evolved = gepa.evolve_population(iterations=1)
    assert len(evolved) > 1

# 8. Benchmark Engine Tests
def test_benchmark_engine_suite_run():
    engine = BenchmarkEngine()
    summary = engine.run_suite([
        {"id": "TEST-01", "category": "logic", "prompt": "Verify logical consistency."}
    ])
    assert summary.total_tasks == 1
    assert summary.passed_tasks == 1
    assert summary.overall_accuracy == 1.0
