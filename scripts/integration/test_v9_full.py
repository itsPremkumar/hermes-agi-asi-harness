"""
Comprehensive v9 Test Suite — All new modules.

Tests:
1. Trajectory Store
2. Trajectory Replay
3. Policy Learning
4. Counterfactual Evaluation
5. UI State Graph
6. UI State Memory
7. Application Digital Twin
8. Environment Discovery
9. Skill Transfer
10. Full Integration (end-to-end)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    print(f"\n{'='*60}")
    print("  HERMES-ASI-MASTER v9 — Full Integration Tests")
    print(f"{'='*60}")

    results = []

    # ── Test 1: Trajectory Store ───────────────────────────────────────────
    print("\n[1/10] Trajectory Store...")
    try:
        from core.learning.trajectory_store import TrajectoryStore, TrajectoryStatus

        store = TrajectoryStore()
        traj = store.create_trajectory("mission-001", "Deploy service-a", {"env": "prod"})
        
        store.add_step(traj.id, {"status": "idle"}, {"type": "deploy"}, {"status": "deploying"}, {"status": "deploying"})
        store.add_step(traj.id, {"status": "deploying"}, {"type": "verify"}, {"status": "healthy"}, {"status": "completed"})
        
        store.complete_trajectory(traj.id, "success", reward=1.0)
        
        assert traj.status == TrajectoryStatus.COMPLETED
        assert len(traj.steps) == 2
        assert traj.total_reward == 1.0
        
        state = store.get_state()
        assert state["total_trajectories"] == 1
        assert state["completed"] == 1

        results.append(("Trajectory Store", True, f"trajectories={state['total_trajectories']}"))
        print(f"  ✓ Trajectory Store: {state['total_trajectories']} trajectories, {state['completed']} completed")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Trajectory Store", False, str(e)[:100]))
        print(f"  ✗ Trajectory Store failed: {e}")

    # ── Test 2: Trajectory Replay ─────────────────────────────────────────
    print("\n[2/10] Trajectory Replay...")
    try:
        from core.learning.trajectory_store import TrajectoryStore
        from core.learning.trajectory_replay import TrajectoryReplay

        store = TrajectoryStore()
        replay = TrajectoryReplay()
        
        traj = store.create_trajectory("mission-002", "Test replay")
        store.add_step(traj.id, {}, {"type": "read"}, {}, {})
        store.add_step(traj.id, {}, {"type": "write"}, {}, {})
        store.complete_trajectory(traj.id, "success", reward=0.8)
        
        # Replay with modified policy
        def modifier(action, state):
            return {**action, "modified": True}
        
        result = replay.replay(traj, modifier)
        assert result.steps_replayed == 2
        
        # Generate counterfactual
        cf = replay.generate_counterfactual(traj, 0, {"type": "delete"}, "better", 0.9)
        assert cf is not None
        assert cf.original_action["type"] == "read"

        state = replay.get_state()
        results.append(("Trajectory Replay", True, f"replays={state['replays']}"))
        print(f"  ✓ Trajectory Replay: {state['replays']} replays, {state['counterfactuals']} counterfactuals")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Trajectory Replay", False, str(e)[:100]))
        print(f"  ✗ Trajectory Replay failed: {e}")

    # ── Test 3: Policy Learning ───────────────────────────────────────────
    print("\n[3/10] Policy Learning...")
    try:
        from core.learning.policy_learning import PolicyLearner, PolicySource

        learner = PolicyLearner()
        
        # Select action
        action = learner.select_action("file_ops", {"file_size_mb": 5, "is_production": False})
        assert action is not None
        
        # Record outcome
        policies = list(learner.policies.values())
        learner.record_outcome(policies[0].id, "file_ops", action, True, 0.9)
        
        # Learn from trajectories
        from core.learning.trajectory_store import TrajectoryStore
        store = TrajectoryStore()
        traj = store.create_trajectory("m001", "test", {"task_type": "file_ops"})
        store.add_step(traj.id, {}, {"type": "python_tool"}, {}, {"reward": 0.8})
        store.complete_trajectory(traj.id, "success", 0.8)
        learner.learn_from_trajectories([traj])
        
        best = learner.get_best_policy("file_ops")
        assert best is not None

        state = learner.get_state()
        results.append(("Policy Learning", True, f"policies={state['policies']}"))
        print(f"  ✓ Policy Learning: {state['policies']} policies, {state['outcomes']} outcomes")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Policy Learning", False, str(e)[:100]))
        print(f"  ✗ Policy Learning failed: {e}")

    # ── Test 4: Counterfactual Evaluation ──────────────────────────────────
    print("\n[4/10] Counterfactual Evaluation...")
    try:
        from core.learning.counterfactual import CounterfactualEvaluator, CounterfactualQuery

        evaluator = CounterfactualEvaluator()
        
        # Record some outcomes
        evaluator.record_action_outcome("deploy", 0.9)
        evaluator.record_action_outcome("deploy", 0.8)
        evaluator.record_action_outcome("rollback", 0.3)
        
        # Evaluate counterfactual
        query = CounterfactualQuery("traj-001", 0, "deploy", "rollback", {"env": "prod"})
        result = evaluator.evaluate(query)
        assert result.estimated_outcome in ("better", "worse", "similar")
        
        # Compare actions
        comparison = evaluator.compare_actions("deploy", "rollback")
        assert comparison["better"] == "deploy"

        state = evaluator.get_state()
        results.append(("Counterfactual Eval", True, f"evals={state['evaluations']}"))
        print(f"  ✓ Counterfactual Eval: {state['evaluations']} evaluations, {state['actions_tracked']} actions tracked")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Counterfactual Eval", False, str(e)[:100]))
        print(f"  ✗ Counterfactual Eval failed: {e}")

    # ── Test 5: UI State Graph ─────────────────────────────────────────────
    print("\n[5/10] UI State Graph...")
    try:
        from core.computer_use_v2.ui_state_graph import UIStateGraph, UIElement, UIElementType

        graph = UIStateGraph("Google Calendar")
        
        # Add states
        home = graph.add_state("Home", [
            UIElement("e1", UIElementType.BUTTON, "Create Event", (100, 50), (120, 40)),
            UIElement("e2", UIElementType.LINK, "Settings", (500, 50), (80, 30)),
        ])
        
        create = graph.add_state("Create Event", [
            UIElement("e3", UIElementType.TEXT_FIELD, "Title", (200, 100), (300, 30)),
            UIElement("e4", UIElementType.BUTTON, "Save", (200, 400), (80, 40)),
        ])
        
        # Add transitions
        graph.add_transition(home.id, create.id, {"action": "click", "target": "Create Event"}, "e1")
        graph.add_transition(create.id, home.id, {"action": "click", "target": "Save"}, "e4")
        
        # Record usage
        graph.record_transition(graph.transitions[0].id, True, 500)
        
        # Find path
        path = graph.find_path(home.id, create.id)
        assert len(path) == 1
        
        # Get best transition
        best = graph.get_best_transition(home.id)
        assert best is not None

        state = graph.get_state()
        results.append(("UI State Graph", True, f"states={state['states']}"))
        print(f"  ✓ UI State Graph: {state['states']} states, {state['transitions']} transitions")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("UI State Graph", False, str(e)[:100]))
        print(f"  ✗ UI State Graph failed: {e}")

    # ── Test 6: UI State Memory ────────────────────────────────────────────
    print("\n[6/10] UI State Memory...")
    try:
        from core.computer_use_v2.ui_memory import UIStateMemory

        memory = UIStateMemory()
        
        # Remember elements
        memory.remember_element("Google Calendar", "Create Event", "button", (100, 50), "create_button", "click")
        memory.remember_element("Google Calendar", "Settings", "link", (500, 50), "settings_link", "click")
        
        # Remember pattern
        memory.remember_pattern("Google Calendar", "create_new_event", [
            {"action": "click", "element_label": "Create Event", "expected_state": "Create Event"},
            {"action": "type", "element_label": "Title", "expected_state": "Title filled"},
            {"action": "click", "element_label": "Save", "expected_state": "Home"},
        ])
        
        # Find element
        elem = memory.find_element("Google Calendar", "create_button")
        assert elem is not None
        assert elem.typical_location == (100, 50)
        
        # Find pattern
        pattern = memory.find_pattern("Google Calendar", "create_new_event")
        assert pattern is not None
        assert len(pattern.steps) == 3
        
        # Record usage
        memory.record_element_usage(elem.id, True)
        memory.record_pattern_usage(pattern.id, True, 1500)
        
        state = memory.get_state()
        results.append(("UI State Memory", True, f"elements={state['elements']}"))
        print(f"  ✓ UI State Memory: {state['elements']} elements, {state['patterns']} patterns")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("UI State Memory", False, str(e)[:100]))
        print(f"  ✗ UI State Memory failed: {e}")

    # ── Test 7: Application Digital Twin ───────────────────────────────────
    print("\n[7/10] Application Digital Twin...")
    try:
        from core.computer_use_v2.app_digital_twin import ApplicationDigitalTwin

        twin = ApplicationDigitalTwin("GitHub", "git_hosting")
        
        # Add entities
        twin.add_entity("Repository", "code_repo", {"visibility": "public"}, ["read", "write", "delete"])
        twin.add_entity("Pull Request", "pr", {"status": "open"}, ["read", "merge", "close", "comment"])
        
        # Add screens
        twin.add_screen("Repository List", [{"name": "New Repo", "type": "button"}], ["create_repo"])
        twin.add_screen("PR Detail", [{"name": "Merge", "type": "button"}], ["merge", "close", "comment"])
        
        # Add workflow
        twin.add_workflow("Create PR", [
            {"action": "click", "target": "New PR"},
            {"action": "fill", "target": "PR title"},
            {"action": "click", "target": "Submit"},
        ], ["repo_exists"], ["pr_created"], ["network_error", "validation_error"])
        
        # Add failure mode
        twin.add_failure_mode("Merge Conflict", "merge", "Cannot merge due to conflicts", "resolve_conflicts", 0.2)
        
        # Simulate action
        result = twin.simulate_action("merge", "Pull Request")
        assert result["success"] == True
        
        # Get workflow
        wf = twin.get_workflow("Create PR")
        assert wf is not None
        assert len(wf.steps) == 3

        state = twin.get_state()
        results.append(("Digital Twin", True, f"entities={state['entities']}"))
        print(f"  ✓ Digital Twin: {state['entities']} entities, {state['workflows']} workflows")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Digital Twin", False, str(e)[:100]))
        print(f"  ✗ Digital Twin failed: {e}")

    # ── Test 8: Environment Discovery ──────────────────────────────────────
    print("\n[8/10] Environment Discovery...")
    try:
        from core.computer_use_v2.discovery import (
            EnvironmentDiscovery, DiscoveredInterface, DiscoveredCapability, DiscoveredRisk
        )

        discovery = EnvironmentDiscovery()
        
        # Start discovery
        result = discovery.start_discovery("GitHub")
        
        # Discover interfaces
        discovery.discover_interfaces(result.id, [
            DiscoveredInterface("REST API", "api", "https://api.github.com", "https"),
            DiscoveredInterface("Web UI", "gui", "https://github.com"),
            DiscoveredInterface("CLI", "cli", "gh"),
        ])
        
        # Discover capabilities
        discovery.discover_capabilities(result.id, [
            DiscoveredCapability("Create Repo", "create_repo", {"name": "string", "visibility": "public|private"}),
            DiscoveredCapability("Delete Repo", "delete_repo", {"name": "string"}),
            DiscoveredCapability("Create PR", "create_pr", {"title": "string", "branch": "string"}),
        ])
        
        # Discover state
        discovery.discover_state(result.id, {"authenticated": True, "rate_limit": 5000})
        
        # Discover permissions
        discovery.discover_permissions(result.id, {"admin": ["all"], "user": ["read", "write"]})
        
        # Discover risks
        discovery.discover_risks(result.id, [
            DiscoveredRisk("rate_limit", 0.3, "API rate limit exceeded", "wait_and_retry"),
            DiscoveredRisk("auth_failure", 0.8, "Authentication failed", "refresh_token"),
        ])
        
        # Build model
        discovery.build_model(result.id)
        
        assert result.stage.value == "completed"
        assert result.model is not None
        assert len(result.interfaces) == 3
        assert len(result.capabilities) == 3

        state = discovery.get_state()
        results.append(("Environment Discovery", True, f"completed={state['completed']}"))
        print(f"  ✓ Environment Discovery: {state['completed']}/{state['total_discoveries']} completed")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Environment Discovery", False, str(e)[:100]))
        print(f"  ✗ Environment Discovery failed: {e}")

    # ── Test 9: Skill Transfer ─────────────────────────────────────────────
    print("\n[9/10] Skill Transfer...")
    try:
        from core.learning.skill_transfer import SkillTransfer

        transfer = SkillTransfer()
        
        # Define abstract skill
        skill = transfer.define_skill(
            "verify_after_mutation",
            "Verify external state after mutation",
            ["entity_exists", "has_permission"],
            [{"action": "read", "target": "entity"}, {"action": "compare", "with": "expected"}],
            ["state_matches_expected"],
            ["state_match", "no_error"],
            source_domains=["GitHub"]
        )
        
        # Transfer to new domain
        instance = transfer.transfer_skill(skill.id, "Google Calendar", {"event_id": "123"})
        assert instance is not None
        assert instance.domain == "Google Calendar"
        
        # Find applicable skills
        applicable = transfer.find_applicable_skills("GitHub", ["entity_exists", "has_permission"])
        assert len(applicable) >= 1
        
        # Get instances
        instances = transfer.get_instances_for_domain("Google Calendar")
        assert len(instances) == 1

        state = transfer.get_state()
        results.append(("Skill Transfer", True, f"skills={state['abstract_skills']}"))
        print(f"  ✓ Skill Transfer: {state['abstract_skills']} abstract skills, {state['total_transfers']} transfers")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Skill Transfer", False, str(e)[:100]))
        print(f"  ✗ Skill Transfer failed: {e}")

    # ── Test 10: Full Integration (End-to-End) ─────────────────────────────
    print("\n[10/10] Full Integration...")
    try:
        from core.environment.model import EnvironmentModel, EntityType
        from core.environment.affordances import AffordanceModel, Reversibility, BlastRadius
        from core.environment.state_estimation import StateEstimator, ObservationSource
        from core.environment.consequence import ConsequenceSimulator
        from core.protocols.uap import UniversalActionProtocol, ActionType
        from core.protocols.uop import PerceptionFusion
        from core.protocols.event_algebra import EventBus, EventType
        from core.action.transaction import TransactionModel, RollbackType
        from core.action.safety_envelope import SafetyEnvelopeManager
        from core.orchestrator.master_loop import MasterOrchestrator
        from core.learning.trajectory_store import TrajectoryStore
        from core.learning.trajectory_replay import TrajectoryReplay
        from core.learning.policy_learning import PolicyLearner
        from core.learning.counterfactual import CounterfactualEvaluator
        from core.computer_use_v2.ui_state_graph import UIStateGraph
        from core.computer_use_v2.discovery import EnvironmentDiscovery

        # Initialize all components
        env_model = EnvironmentModel()
        aff_model = AffordanceModel()
        state_est = StateEstimator()
        sim = ConsequenceSimulator()
        sim.load_default_rules()
        uap = UniversalActionProtocol()
        uop = PerceptionFusion()
        event_bus = EventBus()
        tx_model = TransactionModel()
        safety = SafetyEnvelopeManager()
        orch = MasterOrchestrator()
        traj_store = TrajectoryStore()
        replay = TrajectoryReplay()
        policy_learner = PolicyLearner()
        cf_eval = CounterfactualEvaluator()
        ui_graph = UIStateGraph("TestApp")
        discovery = EnvironmentDiscovery()

        # 1. Discover environment
        disc = discovery.start_discovery("TestApp")
        discovery.discover_interfaces(disc.id, [])
        discovery.discover_capabilities(disc.id, [])
        discovery.discover_state(disc.id, {"status": "ready"})
        discovery.discover_permissions(disc.id, {})
        discovery.discover_risks(disc.id, [])
        discovery.build_model(disc.id)

        # 2. Create environment entity
        svc = env_model.add_entity("TestService", EntityType.SERVICE, {"status": "idle"})
        res = env_model.add_resource("deployment", {"status": "idle"}, ["deploy", "rollback"])

        # 3. Generate affordances
        aff_model.generate_affordances_for_resource(res.id, "deployment", ["deploy", "rollback"])

        # 4. Simulate consequence
        sim_result = sim.simulate("deploy", "TestService", {"is_production": False})
        assert sim_result.should_execute or not sim_result.requires_approval

        # 5. Create action
        action = uap.create_action(ActionType.EXECUTE, "TestService", {"command": "deploy"})

        # 6. Check safety envelope
        env = safety.create_envelope("test", allowed_targets=["TestService"], allowed_operations=["deploy"])
        check = safety.check_action(action.id, env.id, "TestService", "deploy", risk_score=0.3)
        assert check.passed

        # 7. Execute transaction
        tid = tx_model.begin()
        tx_model.add_action(tid, "deploy", "TestService", {}, RollbackType.HARD)
        tx_result = tx_model.commit(tid)
        assert tx_result.success

        # 8. Record trajectory
        traj = traj_store.create_trajectory("mission-001", "Deploy TestService")
        traj_store.add_step(traj.id, {"status": "idle"}, {"type": "deploy"}, {}, {"status": "deployed"})
        traj_store.complete_trajectory(traj.id, "success", 1.0)

        # 9. Learn from trajectory
        policy_learner.learn_from_trajectories(traj_store.get_all_trajectories())

        # 10. Execute mission through orchestrator
        mission = orch.create_mission("Deploy TestService")
        result = orch.execute_mission(mission.id)
        assert result["success"]

        results.append(("Full Integration", True, "all components wired"))
        print(f"  ✓ Full Integration: All 10+ components wired and working together")
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("Full Integration", False, str(e)[:100]))
        print(f"  ✗ Full Integration failed: {e}")

    # ── Summary ────────────────────────────────────────────────────────────
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  v9 Full Tests: {passed}/{total} passed")
    print(f"{'='*60}")
    for name, ok, detail in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {detail}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
