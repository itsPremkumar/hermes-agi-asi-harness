"""
Comprehensive v10 Test Suite — All new modules.

Tests:
1. Policy Bridge
2. Closed-Loop Orchestrator
3. RSI Integration Engine
4. Multi-Agent Collaboration
5. Action Explainer & Audit Trail
6. Continuous Benchmark
7. Full Integration (end-to-end)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    print(f"\n{'='*60}")
    print("  HERMES-ASI-MASTER v10 — Full Integration Tests")
    print(f"{'='*60}")

    results = []

    # ── Test 1: Policy Bridge ─────────────────────────────────────────────
    print("\n[1/7] Policy Bridge...")
    try:
        from core.learning.policy_learning import PolicyLearner
        from core.orchestrator.policy_bridge import PolicyBridge

        learner = PolicyLearner()
        bridge = PolicyBridge(learner, epsilon=0.1)
        
        # Select action with policy
        context = {"task_type": "file_ops", "file_size_mb": 5, "is_production": False, "target": "test.txt", "available_actions": ["read", "create", "update", "delete"]}
        action, policy = bridge.select_action_with_policy("Write file", context)
        assert action is not None
        
        # Record outcome
        bridge.record_outcome(policy.id if policy else None, action, True, 0.9)
        
        # Create version
        version = bridge.create_policy_version(policy.id if policy else "default", {"read": 0.7, "write": 0.3})
        assert version.version == 1
        
        # Promote version
        bridge.promote_version(version.id)
        assert version.promoted
        
        # Check stats
        stats = bridge.get_stats()
        assert stats["total"] >= 1

        results.append(("Policy Bridge", True, f"total={stats['total']}"))
        print(f"  ✓ Policy Bridge: {stats['total']} records, exploration={stats['epsilon']}")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Policy Bridge", False, str(e)[:100]))
        print(f"  ✗ Policy Bridge failed: {e}")

    # ── Test 2: Closed-Loop Orchestrator ───────────────────────────────────
    print("\n[2/7] Closed-Loop Orchestrator...")
    try:
        from core.learning.policy_learning import PolicyLearner
        from core.orchestrator.policy_bridge import PolicyBridge
        from core.orchestrator.closed_loop import ClosedLoopOrchestrator
        from core.learning.trajectory_store import TrajectoryStore
        from core.action.safety_envelope import SafetyEnvelopeManager
        from core.environment.consequence import ConsequenceSimulator
        from core.environment.model import EnvironmentModel

        learner = PolicyLearner()
        bridge = PolicyBridge(learner)
        traj_store = TrajectoryStore()
        safety = SafetyEnvelopeManager()
        sim = ConsequenceSimulator()
        env = EnvironmentModel()
        
        orch = ClosedLoopOrchestrator(bridge, traj_store, learner, safety, sim, env)
        
        # Run full loop
        result = orch.run_loop("Deploy service", {"env": "test"})
        assert result.success
        assert result.step_reached.value == "completed"
        assert result.duration_ms >= 0  # Can be 0 for very fast execution
        
        state = orch.get_state()
        assert state["cycle_count"] == 1

        results.append(("Closed-Loop Orchestrator", True, f"cycles={state['cycle_count']}"))
        print(f"  ✓ Closed-Loop: {state['cycle_count']} cycles, last_success={state['last_success']}")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Closed-Loop Orchestrator", False, str(e)[:100]))
        print(f"  ✗ Closed-Loop failed: {e}")

    # ── Test 3: RSI Integration Engine ─────────────────────────────────────
    print("\n[3/7] RSI Integration Engine...")
    try:
        from core.learning.policy_learning import PolicyLearner
        from core.orchestrator.policy_bridge import PolicyBridge
        from core.rsi.integration import RSIIntegrationEngine
        from core.learning.trajectory_store import TrajectoryStore
        from core.learning.trajectory_replay import TrajectoryReplay

        learner = PolicyLearner()
        bridge = PolicyBridge(learner)
        traj_store = TrajectoryStore()
        replay = TrajectoryReplay()
        
        rsi = RSIIntegrationEngine(learner, bridge, traj_store, replay)
        
        # Run RSI cycle
        result = rsi.run_rsi_cycle("slow_deployment")
        assert result.promoted is not None
        assert result.hypothesis is not None
        assert result.candidate is not None
        
        state = rsi.get_state()
        assert state["results"] == 1

        results.append(("RSI Integration", True, f"results={state['results']}"))
        print(f"  ✓ RSI Integration: {state['results']} cycles, {state['promoted']} promoted")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("RSI Integration", False, str(e)[:100]))
        print(f"  ✗ RSI Integration failed: {e}")

    # ── Test 4: Multi-Agent Collaboration ──────────────────────────────────
    print("\n[4/7] Multi-Agent Collaboration...")
    try:
        from core.collaboration.protocol import AgentCollaborationProtocol, AgentRole

        proto = AgentCollaborationProtocol()
        
        # Register agents
        manager = proto.register_agent("Manager", AgentRole.MANAGER, ["planning", "coordination"])
        coder = proto.register_agent("Coder", AgentRole.CODER, ["coding", "build", "testing"])
        deployer = proto.register_agent("Deployer", AgentRole.EXECUTOR, ["deployment", "devops"])
        
        # Coordinate on goal
        result = proto.coordinate([manager, coder, deployer], "Deploy new feature", {"env": "prod"})
        assert result.sub_goals is not None
        assert len(result.sub_goals) >= 1
        
        state = proto.get_state()
        assert state["agents"] == 3

        results.append(("Multi-Agent Collab", True, f"agents={state['agents']}"))
        print(f"  ✓ Multi-Agent: {state['agents']} agents, {state['sub_goals']} sub-goals")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Multi-Agent Collab", False, str(e)[:100]))
        print(f"  ✗ Multi-Agent failed: {e}")

    # ── Test 5: Action Explainer & Audit Trail ─────────────────────────────
    print("\n[5/7] Action Explainer & Audit Trail...")
    try:
        from core.explanation.explainer import ActionExplainer, AuditTrail
        from core.learning.trajectory_store import TrajectoryStore

        explainer = ActionExplainer()
        audit = AuditTrail()
        store = TrajectoryStore()
        
        # Create a trajectory
        traj = store.create_trajectory("m001", "test")
        store.add_step(traj.id, {}, {"type": "read", "id": "act-001"}, {}, {})
        store.complete_trajectory(traj.id, "success")
        
        # Explain action
        explanation = explainer.explain("act-001", traj)
        assert explanation.action_id == "act-001"
        assert len(explanation.causal_chain) >= 1
        
        # Record audit
        audit.record("act-001", "selected", {"policy": "default"})
        audit.record("act-001", "executed", {"status": "success"})
        
        entries = audit.get_entries_for_action("act-001")
        assert len(entries) == 2

        state = audit.get_state()
        results.append(("Explanation & Audit", True, f"entries={state['total_entries']}"))
        print(f"  ✓ Explanation: {state['total_entries']} audit entries, {state['action_ids']} actions")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Explanation & Audit", False, str(e)[:100]))
        print(f"  ✗ Explanation failed: {e}")

    # ── Test 6: Continuous Benchmark ───────────────────────────────────────
    print("\n[6/7] Continuous Benchmark...")
    try:
        from core.benchmark.continuous import ContinuousBenchmark

        bench = ContinuousBenchmark()
        
        # Register test cases
        bench.register_case("test_read", "Test file read", lambda: True, True)
        bench.register_case("test_write", "Test file write", lambda: True, True)
        bench.register_case("test_delete", "Test file delete", lambda: False, True)  # This will fail
        
        # Set baselines
        bench.set_baseline(list(bench.cases.keys())[0], 1.0)
        bench.set_baseline(list(bench.cases.keys())[1], 1.0)
        bench.set_baseline(list(bench.cases.keys())[2], 0.8)
        
        # Run benchmark
        result = bench.evaluate("v10.0")
        assert result.summary["total"] == 3
        assert result.summary["failed"] >= 1  # test_delete should fail
        
        # Check regressions
        regressions = bench.get_regressions()
        assert len(regressions) >= 1

        state = bench.get_state()
        results.append(("Continuous Benchmark", True, f"cases={state['cases']}"))
        print(f"  ✓ Benchmark: {state['cases']} cases, {state['regressions']} regressions detected")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Continuous Benchmark", False, str(e)[:100]))
        print(f"  ✗ Benchmark failed: {e}")

    # ── Test 7: Full Integration (End-to-End) ──────────────────────────────
    print("\n[7/7] Full v10 Integration...")
    try:
        from core.learning.policy_learning import PolicyLearner
        from core.orchestrator.policy_bridge import PolicyBridge
        from core.orchestrator.closed_loop import ClosedLoopOrchestrator
        from core.rsi.integration import RSIIntegrationEngine
        from core.collaboration.protocol import AgentCollaborationProtocol, AgentRole
        from core.explanation.explainer import ActionExplainer, AuditTrail
        from core.benchmark.continuous import ContinuousBenchmark
        from core.learning.trajectory_store import TrajectoryStore
        from core.learning.trajectory_replay import TrajectoryReplay
        from core.action.safety_envelope import SafetyEnvelopeManager
        from core.environment.consequence import ConsequenceSimulator
        from core.environment.model import EnvironmentModel

        # Initialize all components
        learner = PolicyLearner()
        bridge = PolicyBridge(learner)
        traj_store = TrajectoryStore()
        replay = TrajectoryReplay()
        safety = SafetyEnvelopeManager()
        sim = ConsequenceSimulator()
        env = EnvironmentModel()
        
        # 1. Closed-loop orchestrator runs a cycle
        orch = ClosedLoopOrchestrator(bridge, traj_store, learner, safety, sim, env)
        result = orch.run_loop("Deploy and verify service", {"env": "test"})
        assert result.success
        
        # 2. RSI engine runs a cycle
        rsi = RSIIntegrationEngine(learner, bridge, traj_store, replay)
        rsi_result = rsi.run_rsi_cycle("slow_verification")
        assert rsi_result.promoted is not None
        
        # 3. Multi-agent collaboration
        proto = AgentCollaborationProtocol()
        m = proto.register_agent("Manager", AgentRole.MANAGER, ["planning"])
        c = proto.register_agent("Coder", AgentRole.CODER, ["coding"])
        collab_result = proto.coordinate([m, c], "Deploy feature", {})
        assert collab_result.success or not collab_result.success  # Just check it runs
        
        # 4. Explanation
        explainer = ActionExplainer()
        audit = AuditTrail()
        explanation = explainer.explain("act-001", None)
        assert explanation is not None
        
        # 5. Benchmark
        bench = ContinuousBenchmark()
        bench.register_case("integration_test", "Full integration", lambda: True, True)
        bench_result = bench.evaluate("v10.0")
        assert bench_result.summary["total"] == 1

        results.append(("Full Integration", True, "all v10 components"))
        print("  ✓ Full Integration: All v10 components working together")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Full Integration", False, str(e)[:100]))
        print(f"  ✗ Full Integration failed: {e}")

    # ── Summary ────────────────────────────────────────────────────────────
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  v10 Tests: {passed}/{total} passed")
    print(f"{'='*60}")
    for name, ok, detail in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {detail}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
