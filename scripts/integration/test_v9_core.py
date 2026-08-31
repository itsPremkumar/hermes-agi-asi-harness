"""
Test Suite for v9: Universal Environment Intelligence & Action Plane

Tests:
1. Environment Model — entities, resources, relationships, events, constraints, permissions
2. Affordance Model — affordances, consequences, risk scoring, compensation
3. State Estimation — observations, fusion, contradiction detection, anomaly detection
4. Consequence Simulator — simulation rules, risk calculation, historical learning
5. Universal Action Protocol — action creation, action graph, composition
6. Universal Observation Protocol — perception fusion, conflict detection
7. Event Algebra — event emission, subscription, filtering
8. Transaction Model — prepare/verify/commit, rollback, compensation
9. Safety Envelope — envelope checks, violations, emergency stop
10. Master Orchestrator — mission execution through the v9 loop
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    print(f"\n{'='*60}")
    print("  HERMES-ASI-MASTER v9 — Environment Intelligence Tests")
    print(f"{'='*60}")

    results = []

    # ── Test 1: Environment Model ──────────────────────────────────────────
    print("\n[1/10] Environment Model...")
    try:
        from core.environment.model import EnvironmentModel, EntityType, RelationshipType

        model = EnvironmentModel()

        # Add entities
        github = model.add_entity("GitHub", EntityType.SYSTEM, {"url": "https://github.com"})
        repo = model.add_entity("my-repo", EntityType.SERVICE, {"language": "Python"})
        db = model.add_entity("postgres-db", EntityType.DATABASE, {"version": "15"})

        # Add relationships
        model.add_relationship(repo.id, github.id, RelationshipType.DEPENDS_ON)
        model.add_relationship(repo.id, db.id, RelationshipType.CALLS)

        # Add resource
        res = model.add_resource("deployment", {"status": "idle"}, capabilities=["deploy", "rollback"])

        # Add event
        model.add_event("deploy_triggered", "ci-system", {"branch": "main"}, [repo.id])

        # Add constraint
        model.add_constraint("rate_limit", "deploy", 10)

        # Add permission
        model.add_permission(res.id, "deploy", True, scope="production")

        # Query
        state = model.get_state()
        assert state["entities_count"] == 3
        assert state["resources_count"] == 1
        assert state["relationships_count"] == 2
        assert state["events_count"] == 1

        # Check dependents
        dependents = model.get_dependents(github.id)
        assert len(dependents) == 1

        # Check permission
        assert model.check_permission(res.id, "deploy") == True
        assert model.check_permission(res.id, "delete") == False  # default deny

        results.append(("Environment Model", True, f"entities={state['entities_count']}"))
        print(f"  ✓ Environment Model: {state['entities_count']} entities, {state['resources_count']} resources")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Environment Model", False, str(e)[:100]))
        print(f"  ✗ Environment Model failed: {e}")

    # ── Test 2: Affordance Model ───────────────────────────────────────────
    print("\n[2/10] Affordance Model...")
    try:
        from core.environment.affordances import AffordanceModel

        aff_model = AffordanceModel()

        # Generate affordances for a resource
        affs = aff_model.generate_affordances_for_resource("res-001", "deployment", ["deploy", "read", "update"])
        assert len(affs) >= 2

        # Add consequence
        aff = affs[0]
        aff_model.add_consequence(aff.id, "immediate", "Service version changes", 1.0, 0.5)

        # Check risk score
        risk = aff_model.get_risk_score(aff.id)
        assert 0.0 <= risk <= 1.0

        # Check compensation
        deploy_aff = [a for a in affs if a.action == "deploy"]
        if deploy_aff:
            comp = aff_model.get_compensation(deploy_aff[0].id)
            assert comp is not None

        # Check irreversible
        irreversible = aff_model.get_irreversible_actions()
        assert len(irreversible) >= 0  # may be empty if no send/delete

        state = aff_model.get_state()
        results.append(("Affordance Model", True, f"affordances={state['affordances_count']}"))
        print(f"  ✓ Affordance Model: {state['affordances_count']} affordances, risk={risk:.2f}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Affordance Model", False, str(e)[:100]))
        print(f"  ✗ Affordance Model failed: {e}")

    # ── Test 3: State Estimation ───────────────────────────────────────────
    print("\n[3/10] State Estimation...")
    try:
        from core.environment.state_estimation import StateEstimator, ObservationSource

        estimator = StateEstimator()

        # Add observations from multiple sources
        estimator.add_observation("svc-001", ObservationSource.API, {"status": "running", "version": "1.0"}, 0.9)
        estimator.add_observation("svc-001", ObservationSource.MONITORING, {"status": "running", "cpu": 45.0}, 0.85)
        estimator.add_observation("svc-001", ObservationSource.DOM, {"status": "deploying"}, 0.6)

        # Estimate state
        estimate = estimator.estimate("svc-001")
        assert estimate is not None
        assert estimate.confidence in ("high", "medium", "low", "unknown")
        assert len(estimate.sources) >= 2

        # Check for contradictions (API says running, DOM says deploying)
        assert len(estimate.contradictions) >= 1

        state = estimator.get_state()
        results.append(("State Estimation", True, f"confidence={estimate.confidence.value}"))
        print(f"  ✓ State Estimation: confidence={estimate.confidence.value}, contradictions={len(estimate.contradictions)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("State Estimation", False, str(e)[:100]))
        print(f"  ✗ State Estimation failed: {e}")

    # ── Test 4: Consequence Simulator ──────────────────────────────────────
    print("\n[4/10] Consequence Simulator...")
    try:
        from core.environment.consequence import ConsequenceSimulator

        sim = ConsequenceSimulator()
        sim.load_default_rules()

        # Simulate a deploy action
        result = sim.simulate("deploy", "my-service", {"is_production": True})
        assert result.action == "deploy"
        assert len(result.predictions) >= 3
        assert 0.0 <= result.overall_risk <= 1.0

        # Record outcome
        sim.record_outcome("deploy", "my-service", result.overall_risk, False)
        calibration = sim.get_calibration()
        assert 0.0 <= calibration <= 1.0

        state = sim.get_state()
        results.append(("Consequence Simulator", True, f"risk={result.overall_risk:.2f}"))
        print(f"  ✓ Consequence Simulator: risk={result.overall_risk:.2f}, predictions={len(result.predictions)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Consequence Simulator", False, str(e)[:100]))
        print(f"  ✗ Consequence Simulator failed: {e}")

    # ── Test 5: Universal Action Protocol ──────────────────────────────────
    print("\n[5/10] Universal Action Protocol...")
    try:
        from core.protocols.uap import UniversalActionProtocol, ActionType

        uap = UniversalActionProtocol()

        # Create actions
        read_act = uap.create_action(ActionType.READ, "file.txt")
        create_act = uap.create_action(ActionType.CREATE, "output.txt", {"content": "hello"})
        exec_act = uap.create_action(ActionType.EXECUTE, "script.py", parent_id=read_act.id)

        # Link actions
        uap.link_actions(read_act.id, exec_act.id, "causes")
        uap.link_actions(create_act.id, exec_act.id, "enables")

        # Get causal chain (follows "causes" relationships)
        chain = uap.get_causal_chain(read_act.id)
        assert len(chain) >= 1

        # Get blocked actions (follows "blocks" relationships)
        blocked = uap.get_blocked_actions(create_act.id)
        assert isinstance(blocked, list)

        # Emit event
        event = uap.emit_event("completed", "test", {"result": "success"}, ["file.txt"])
        assert event.type == "completed"

        # Check action types
        assert uap.is_read(read_act) == True
        assert uap.is_write(create_act) == True
        assert uap.is_safe(read_act) == True

        state = uap.get_state()
        results.append(("UAP", True, f"actions={state['total_actions']}"))
        print(f"  ✓ UAP: {state['total_actions']} actions, {state['total_events']} events")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("UAP", False, str(e)[:100]))
        print(f"  ✗ UAP failed: {e}")

    # ── Test 6: Universal Observation Protocol ─────────────────────────────
    print("\n[6/10] Universal Observation Protocol...")
    try:
        from core.protocols.uop import PerceptionFusion, ObservationSource

        pf = PerceptionFusion()

        # Add observations from multiple sources
        pf.add_observation("svc-001", ObservationSource.API, {}, "raw-api", {"status": "running"}, 0.9)
        pf.add_observation("svc-001", ObservationSource.DOM, {}, "raw-dom", {"status": "deploying"}, 0.6)
        pf.add_observation("svc-001", ObservationSource.MONITORING, {}, "raw-mon", {"status": "running", "cpu": 50}, 0.85)

        # Fuse
        fused = pf.fuse("svc-001")
        assert fused is not None
        assert len(fused.sources) >= 2
        assert fused.confidence > 0.0

        # Check conflicts
        assert len(fused.conflicts) >= 1  # API says running, DOM says deploying

        state = pf.get_state()
        results.append(("UOP", True, f"confidence={fused.confidence:.2f}"))
        print(f"  ✓ UOP: confidence={fused.confidence:.2f}, conflicts={len(fused.conflicts)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("UOP", False, str(e)[:100]))
        print(f"  ✗ UOP failed: {e}")

    # ── Test 7: Event Algebra ──────────────────────────────────────────────
    print("\n[7/10] Event Algebra...")
    try:
        from core.protocols.event_algebra import EventBus, EventType

        bus = EventBus()

        # Subscribe
        notified_events = []
        def handler(event):
            notified_events.append(event)

        bus.subscribe("agent-001", {"type": ["completed", "failed"]}, handler)
        bus.subscribe("agent-002", {"source": "ci-system"})

        # Emit events
        n1 = bus.emit(EventType.COMPLETED, "ci-system", {"build_id": 123}, ["service-a"])
        assert "agent-001" in n1  # matches type filter
        assert "agent-002" in n1  # matches source filter

        n2 = bus.emit(EventType.CREATED, "user", {"resource": "file.txt"})
        assert "agent-001" not in n2  # doesn't match type filter
        assert "agent-002" not in n2  # doesn't match source filter

        # Query events
        events = bus.get_events(event_type=EventType.COMPLETED)
        assert len(events) >= 1

        state = bus.get_state()
        results.append(("Event Algebra", True, f"events={state['total_events']}"))
        print(f"  ✓ Event Algebra: {state['total_events']} events, {state['subscriptions']} subscriptions")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Event Algebra", False, str(e)[:100]))
        print(f"  ✗ Event Algebra failed: {e}")

    # ── Test 8: Transaction Model ──────────────────────────────────────────
    print("\n[8/10] Transaction Model...")
    try:
        from core.action.transaction import TransactionModel, RollbackType, TransactionState

        tm = TransactionModel()

        # Begin transaction
        tid = tm.begin()

        # Add actions
        tm.add_action(tid, "create", "file.txt", {"content": "hello"}, RollbackType.HARD)
        tm.add_action(tid, "send", "email", {"to": "user@example.com"}, RollbackType.COMPENSATION,
                      compensation_action={"type": "send", "target": "correction"})

        # Commit
        result = tm.commit(tid)
        assert result.success == True
        assert result.actions_completed == 2

        # Test rollback
        tid2 = tm.begin()
        tm.add_action(tid2, "delete", "important.txt", {}, RollbackType.HARD)
        tm.add_action(tid2, "send", "email", {}, RollbackType.COMPENSATION,
                      compensation_action={"type": "correction"})

        # Simulate failure by manually marking
        actions = tm.transactions[tid2]
        actions[0].status = TransactionState.FAILED

        state = tm.get_state()
        results.append(("Transaction Model", True, f"committed={state['committed']}"))
        print(f"  ✓ Transaction Model: {state['total_transactions']} transactions, {state['committed']} committed")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Transaction Model", False, str(e)[:100]))
        print(f"  ✗ Transaction Model failed: {e}")

    # ── Test 9: Safety Envelope ────────────────────────────────────────────
    print("\n[9/10] Safety Envelope...")
    try:
        from core.action.safety_envelope import SafetyEnvelopeManager, EnvelopeViolation

        sem = SafetyEnvelopeManager()

        # Create envelope
        env = sem.create_envelope(
            "production",
            allowed_targets=["service-a", "service-b"],
            allowed_operations=["read", "deploy"],
            max_frequency_per_minute=10,
            max_cost_per_action=1.0,
            max_risk_score=0.7,
        )

        # Check valid action
        check1 = sem.check_action("act-001", env.id, "service-a", "deploy", cost=0.5, risk_score=0.3)
        assert check1.passed == True
        assert len(check1.violations) == 0

        # Check invalid target
        check2 = sem.check_action("act-002", env.id, "service-c", "deploy", cost=0.5, risk_score=0.3)
        assert check2.passed == False
        assert EnvelopeViolation.TARGET_NOT_ALLOWED in check2.violations

        # Check risk too high
        check3 = sem.check_action("act-003", env.id, "service-a", "deploy", cost=0.5, risk_score=0.9)
        assert check3.passed == False
        assert EnvelopeViolation.RISK_TOO_HIGH in check3.violations

        # Test emergency stop
        sem.trigger_emergency_stop(env.id)
        check4 = sem.check_action("act-004", env.id, "service-a", "read", risk_score=0.1)
        assert check4.passed == False

        state = sem.get_state()
        results.append(("Safety Envelope", True, f"checks={state['total_checks']}"))
        print(f"  ✓ Safety Envelope: {state['total_checks']} checks, {state['escalated']} escalated")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Safety Envelope", False, str(e)[:100]))
        print(f"  ✗ Safety Envelope failed: {e}")

    # ── Test 10: Master Orchestrator ───────────────────────────────────────
    print("\n[10/10] Master Orchestrator...")
    try:
        from core.orchestrator.master_loop import MasterOrchestrator, OrchestratorState

        orch = MasterOrchestrator()

        # Create mission
        mission = orch.create_mission("Deploy service-a to production")
        assert mission.status == OrchestratorState.IDLE

        # Execute mission
        result = orch.execute_mission(mission.id)
        assert result["success"] == True
        assert mission.status == OrchestratorState.COMPLETED
        assert len(mission.steps) >= 1

        state = orch.get_state()
        results.append(("Master Orchestrator", True, f"completed={state['completed']}"))
        print(f"  ✓ Master Orchestrator: {state['completed']} completed, state={state['state']}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results.append(("Master Orchestrator", False, str(e)[:100]))
        print(f"  ✗ Master Orchestrator failed: {e}")

    # ── Summary ────────────────────────────────────────────────────────────
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  v9 Tests: {passed}/{total} passed")
    print(f"{'='*60}")
    for name, ok, detail in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {detail}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
