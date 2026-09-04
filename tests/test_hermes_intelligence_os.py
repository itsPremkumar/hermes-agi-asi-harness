"""
Unit and Integration Tests for Hermes Intelligence Operating System (vNext)
===========================================================================
Validates:
1. World Model Subsystem (Entities, Beliefs, Causal Graph, Affordances)
2. 8-System Memory Architecture & Trajectory Archive
3. Context OS Dynamic Budgets & Immutable Invariants
4. Multi-Level Reality Verification Engine (L0–L6 & 3-D Proofs)
5. Hermes Intelligence OS Master Kernel & 6 Nested Control Loops
"""

import asyncio
import os
import pytest
from pathlib import Path

from world_model import (
    WorldModel,
    EntityGraph,
    EntityType,
    BeliefSystem,
    BeliefState,
    CausalGraph,
    ActionAffordanceModel,
)
from memory import (
    MemoryOS,
    SemanticMemory,
    EpisodicMemory,
    ProceduralMemory,
    WorkingMemory,
    FailureMemory,
    DecisionMemory,
    WorldStateMemory,
    CapabilityMemory,
    Trajectory,
    TrajectoryStep,
    TrajectoryArchive,
)
from context_os import (
    ContextBudget,
    GoalInvariant,
    GoalContract,
    ContextCompiler,
)
from verification.vnext import (
    VerificationTier,
    RealityVerificationEngine,
    EarnedCompletionProof,
)
from hermes_os import (
    HermesIntelligenceOS,
    ExecutiveKernel,
    GoalController,
    StateController,
    ResourceController,
    SafetyController,
    MetaPlanner,
    ExecutionArchitecture,
    LoopEngine,
)


# =============================================================================
# 1. World Model Tests
# =============================================================================

class TestWorldModel:
    def test_entity_graph_relationships_and_dependencies(self):
        graph = EntityGraph()
        s1 = graph.add_entity(name="auth_service", entity_type=EntityType.SERVICE)
        d1 = graph.add_entity(name="user_db", entity_type=EntityType.DATABASE)
        t1 = graph.add_entity(name="jwt_validator", entity_type=EntityType.TOOL)

        assert graph.get_entity(s1.entity_id) is not None
        assert graph.find_by_name("auth_service") == s1

        # s1 depends on d1 and t1
        graph.add_relationship(s1.entity_id, "depends_on", d1.entity_id)
        graph.add_relationship(s1.entity_id, "depends_on", t1.entity_id)

        deps = graph.get_dependencies(s1.entity_id)
        assert len(deps) == 2
        dep_names = {d.name for d in deps}
        assert "user_db" in dep_names
        assert "jwt_validator" in dep_names

        dependents = graph.get_dependents(d1.entity_id)
        assert len(dependents) == 1
        assert dependents[0].name == "auth_service"

        data = graph.to_dict()
        assert len(data["entities"]) == 3
        assert len(data["relationships"]) == 2

    def test_belief_system_bayesian_updates_and_contradiction(self):
        bs = BeliefSystem(default_ttl_seconds=3600)
        b = bs.assert_belief("sandbox_is_isolated", probability=0.85)
        assert b.state == BeliefState.LIKELY
        assert not b.contradictory_evidence

        # Add supporting evidence -> probability increases
        bs.add_evidence("sandbox_is_isolated", evidence_ref="test_run_1", is_contradiction=False)
        assert b.probability > 0.85

        # Add contradictory evidence -> marks CONTRADICTED and decreases probability
        bs.add_evidence("sandbox_is_isolated", evidence_ref="leak_detector_alert", is_contradiction=True)
        assert b.state == BeliefState.CONTRADICTED
        assert "leak_detector_alert" in b.contradictory_evidence
        assert len(bs.detect_contradictions()) == 1

        # Test decay
        b_expired = bs.assert_belief("temporary_port_open", probability=0.95, ttl_seconds=-10)
        assert b_expired.is_expired()
        bs.decay_beliefs(decay_rate=0.5)
        # Probability regresses towards 0.5
        assert b_expired.probability < 0.95

    def test_causal_graph_counterfactual_simulation(self):
        cg = CausalGraph()
        cg.add_relationship(
            cause="increase_cache_size",
            mechanism="higher_hit_rate",
            effect="lower_latency",
            strength=0.9,
            confidence=0.95,
        )
        cg.add_relationship(
            cause="lower_latency",
            mechanism="faster_page_load",
            effect="higher_user_conversion",
            strength=0.8,
            confidence=0.9,
        )

        effects = cg.get_effects_of("increase_cache_size")
        assert len(effects) == 1
        assert effects[0].effect == "lower_latency"

        # Counterfactual intervention
        sim = cg.simulate_intervention("increase_cache_size", "doubled_to_1gb")
        assert sim["impacted_nodes_count"] == 2
        assert "lower_latency" in sim["downstream_impacts"]
        assert "higher_user_conversion" in sim["downstream_impacts"]

    def test_action_affordance_model(self):
        model = ActionAffordanceModel()
        affordances = model.all_affordances()
        assert len(affordances) >= 4

        py_aff = model.get_affordance("execute_python")
        assert py_aff is not None
        assert py_aff.tool_name == "python_tool"
        assert py_aff.risk_level == "low"

        avail = model.evaluate_available_actions({"sandbox_isolated": True})
        assert len(avail) == len(affordances)

    def test_world_model_observation_and_snapshot(self):
        wm = WorldModel()
        wm.update_from_observation({
            "entity": "redis_cluster",
            "type": EntityType.SERVICE,
            "fact": "redis_latency_is_under_5ms",
            "source": "monitoring_probe",
        })

        assert wm.entities.find_by_name("redis_cluster") is not None
        assert wm.beliefs.get_belief("redis_latency_is_under_5ms") is not None

        snap = wm.snapshot()
        assert "timestamp" in snap
        assert "entities" in snap
        assert "beliefs" in snap
        assert snap["available_affordances_count"] >= 4


# =============================================================================
# 2. 8-System Memory Architecture & Trajectory Archive Tests
# =============================================================================

class TestMemoryOS:
    def test_semantic_memory_store_and_search(self):
        sem = SemanticMemory()
        sem.store("Astra features a 1.05M-token context window", category="model_spec", tags=["astra", "gpt6"])
        sem.store("Hermes runs an 8-subsystem memory operating system", category="hermes_arch", tags=["hermes", "memory"])

        assert sem.count() == 2
        results = sem.search("Astra token window")
        assert len(results) >= 1
        assert "1.05M-token" in results[0].fact

    def test_episodic_memory_chronology(self):
        epi = EpisodicMemory()
        epi.record("step_executed", "Executed python compiler verification", actor="agent-01")
        epi.record("step_verified", "Verified syntax and anti-goodhart invariants", actor="verifier")

        assert epi.count() == 2
        recent = epi.get_recent(5)
        assert len(recent) == 2
        assert recent[0].actor == "agent-01"
        assert recent[1].actor == "verifier"

    def test_procedural_memory_recipes(self):
        proc = ProceduralMemory()
        p = proc.store_procedure(
            name="safe_file_mutation",
            steps=["check_git_status", "create_isolated_branch", "apply_patch", "run_pytest"],
            preconditions=["git_installed", "pytest_available"],
        )
        assert proc.count() == 1
        retrieved = proc.get_procedure("safe_file_mutation")
        assert retrieved is not None
        assert retrieved.steps[0] == "check_git_status"

    def test_working_memory_registers_and_scratchpad(self):
        wm = WorkingMemory()
        wm.set_register("active_task_id", "task-99")
        wm.append_scratchpad("Investigating causal branch for cache failure")

        assert wm.get_register("active_task_id") == "task-99"
        assert len(wm.read_scratchpad()) == 1

        wm.clear()
        assert wm.get_register("active_task_id") is None
        assert len(wm.read_scratchpad()) == 0

    def test_failure_memory_signatures_and_countermeasures(self):
        fm = FailureMemory()
        fm.record_failure(
            error_type="SyntaxError",
            component="rlm_repl",
            root_cause="Unexpected indent in generated code",
            countermeasures=["reformat_with_black", "re_parse_ast"],
        )
        # Duplicate error accumulates occurrences and countermeasures
        fm.record_failure(
            error_type="SyntaxError",
            component="rlm_repl",
            root_cause="Missing closing paren",
            countermeasures=["lint_before_exec"],
        )

        cms = fm.get_countermeasures("SyntaxError", "rlm_repl")
        assert len(cms) == 3
        assert "reformat_with_black" in cms
        assert "lint_before_exec" in cms

    def test_decision_memory_and_rationale(self):
        dm = DecisionMemory()
        d = dm.record_decision(
            context="Selecting agent topology for mission",
            chosen="hierarchical_swarm",
            rejected=["solo_reactive", "linear_chain"],
            rationale="Subtask requires parallel research and isolated verification",
        )
        assert len(dm.all_decisions()) == 1
        assert d.chosen_strategy == "hierarchical_swarm"
        assert len(d.rejected_alternatives) == 2

    def test_capability_memory_empirical_tracking(self):
        cm = CapabilityMemory()
        # Initial success -> 1.0
        cm.update_capability(name="code_refactoring", domain="software_engineering", success=True)
        cap = cm.get_capability("code_refactoring")
        assert cap.invocations == 1
        assert cap.success_rate == 1.0

        # Subsequent failure -> updates weighted rate
        cm.update_capability(name="code_refactoring", domain="software_engineering", success=False)
        cap = cm.get_capability("code_refactoring")
        assert cap.invocations == 2
        assert cap.success_rate == 0.5

    def test_trajectory_archive_persistence_and_search(self, tmp_path):
        archive = TrajectoryArchive(workspace_root=str(tmp_path))
        step1 = TrajectoryStep(
            step_id="s1",
            state_summary="ready",
            decision_rationale="run unit tests",
            action_type="execute_python",
            action_args={"cmd": "pytest"},
            observation="3 passed",
            outcome="success",
        )
        traj = Trajectory(
            trajectory_id="traj-101",
            mission_id="m-01",
            task_description="Verify all quantum crypto algorithms",
            steps=[step1],
            success=True,
        )

        archive.record_trajectory(traj)
        assert archive.count() == 1

        # File exists on disk
        saved_file = tmp_path / ".hermes" / "trajectories" / "traj-101.json"
        assert saved_file.exists()

        # Keyword search
        matches = archive.search_similar("quantum crypto")
        assert len(matches) == 1
        assert matches[0].trajectory_id == "traj-101"

        # Reload in new instance
        archive_reloaded = TrajectoryArchive(workspace_root=str(tmp_path))
        assert archive_reloaded.count() == 1
        assert archive_reloaded.get_trajectory("traj-101") is not None or len(archive_reloaded.search_similar("quantum")) == 1

    def test_memory_os_unified_stats(self, tmp_path):
        mos = MemoryOS(workspace_root=str(tmp_path))
        stats = mos.stats()
        assert "semantic_entries" in stats
        assert "episodic_events" in stats
        assert "procedures" in stats
        assert "failures_indexed" in stats
        assert "capabilities_tracked" in stats
        assert "archived_trajectories" in stats


# =============================================================================
# 3. Context OS Tests
# =============================================================================

class TestContextOS:
    def test_context_budget_profiles_and_validation(self):
        b_std = ContextBudget.standard_128k()
        assert b_std.validate() is True
        assert b_std.total_tokens == 128000

        b_deep = ContextBudget.deep_reason_200k()
        assert b_deep.validate() is True
        assert b_deep.total_tokens == 200000

        b_astra = ContextBudget.astra_frontier_1m()
        assert b_astra.validate() is True
        assert b_astra.total_tokens == 1050000

        # Invalid budget exceeding ceiling
        b_overflow = ContextBudget(total_tokens=1000, core=800, retrieved=500, working=200, historical=100, reserve=100)
        assert b_overflow.validate() is False

    def test_goal_contract_and_immutable_invariants(self):
        contract = GoalContract(
            contract_id="c-1",
            objective="Refactor caching layer",
            desired_world_state={"caching_operational": True},
            invariants=[
                GoalInvariant(name="existing_code_must_not_be_deleted", description="No deletion", severity="critical"),
                GoalInvariant(name="budget_must_remain_within_limit", description="Cost limit", severity="high"),
            ],
            success_conditions=["tests_pass"],
            failure_conditions=["exception"],
        )

        # Clean state has 0 violations
        clean_state = {"deleted_existing_files": False, "cost_exceeded": False}
        assert contract.check_invariants(clean_state) == []

        # Attempt to delete files triggers critical violation
        violating_state = {"deleted_existing_files": True, "cost_exceeded": False}
        violations = contract.check_invariants(violating_state)
        assert len(violations) == 1
        assert "existing_code_must_not_be_deleted" in violations[0]

    def test_context_compiler_envelope_generation(self):
        compiler = ContextCompiler(budget=ContextBudget.standard_128k())
        contract = GoalContract(
            contract_id="c-2",
            objective="Build microservice",
            desired_world_state={},
            invariants=[GoalInvariant(name="existing_code_must_not_be_deleted", description="Keep files")],
        )

        packet = compiler.compile(
            goal_contract=contract,
            world_state_summary="All services running",
            retrieved_knowledge=["Doc 1: API specs", "Doc 2: Schema"],
            working_tasks=[{"id": "t1", "description": "Write controller", "status": "pending"}],
            historical_notes=["Started sprint"],
        )

        assert "MISSION OBJECTIVE: Build microservice" in packet["core_context"]
        assert "existing_code_must_not_be_deleted" in packet["core_context"]
        assert "Doc 1: API specs" in packet["retrieved_context"]
        assert "Write controller" in packet["working_context"]
        assert packet["reserve_buffer_tokens"] == 8000


# =============================================================================
# 4. Multi-Level Reality Verification Engine Tests
# =============================================================================

class TestVerificationVNext:
    def test_verification_tiers(self):
        assert VerificationTier.L0_NONE.value == "L0"
        assert VerificationTier.L1_SELF_CHECK.value == "L1"
        assert VerificationTier.L5_DETERMINISTIC_ORACLE.value == "L5"
        assert VerificationTier.L6_EXTERNAL_SIGN_OFF.value == "L6"

    def test_reality_verification_clean_code(self):
        engine = RealityVerificationEngine()
        clean_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        proof = engine.verify_deliverable(
            mission_id="m-test-01",
            deliverable_name="math_ops.py",
            content=clean_code,
            tier=VerificationTier.L5_DETERMINISTIC_ORACLE,
            acceptance_criteria=["deliverable_non_empty"],
        )

        assert proof.verified is True
        assert proof.correctness.passed is True
        assert proof.completeness.passed is True
        assert proof.safety.passed is True
        assert proof.proof_hash is not None
        assert len(proof.proof_hash) == 64  # SHA-256

    def test_reality_verification_syntax_error_rejection(self):
        engine = RealityVerificationEngine()
        broken_code = "def broken(\n    return 42"
        proof = engine.verify_deliverable(
            mission_id="m-test-02",
            deliverable_name="broken.py",
            content=broken_code,
            tier=VerificationTier.L5_DETERMINISTIC_ORACLE,
        )

        assert proof.verified is False
        assert proof.correctness.passed is False
        assert any("syntax_error" in ev for ev in proof.correctness.evidence)

    def test_reality_verification_empty_content_rejection(self):
        engine = RealityVerificationEngine()
        proof = engine.verify_deliverable(
            mission_id="m-test-03",
            deliverable_name="empty.py",
            content="",
            tier=VerificationTier.L5_DETERMINISTIC_ORACLE,
            acceptance_criteria=["deliverable_non_empty"],
        )

        assert proof.verified is False
        assert proof.completeness.passed is False

    def test_reality_verification_anti_goodhart_gaming_rejection(self):
        engine = RealityVerificationEngine()
        # Code that attempts to game tests with unconditional assertion passes
        gaming_code = "def test_bypass():\n    assert True\n    return True\n"
        proof = engine.verify_deliverable(
            mission_id="m-test-04",
            deliverable_name="test_gaming.py",
            content=gaming_code,
            tier=VerificationTier.L5_DETERMINISTIC_ORACLE,
        )

        # Anti-Goodhart analyzer flags assertion tautology
        assert proof.safety.passed is False
        assert proof.verified is False


# =============================================================================
# 5. Hermes Intelligence OS Master Kernel & 6 Control Loops Tests
# =============================================================================

class TestHermesIntelligenceOS:
    def test_os_boot_initialization(self, tmp_path):
        os_kernel = HermesIntelligenceOS(workspace_root=str(tmp_path))
        assert os_kernel.executive.state.current_state == "READY"
        assert os_kernel.world_model is not None
        assert os_kernel.memory is not None
        assert os_kernel.meta_planner is not None
        assert os_kernel.context_compiler is not None
        assert os_kernel.verifier is not None
        assert os_kernel.loops is not None

    def test_meta_planner_architecture_selection(self):
        mp = MetaPlanner()

        # Simple task
        arch_simple = mp.select_architecture("Format text file to json")
        assert arch_simple.model_tier == "reactive"
        assert arch_simple.agent_topology == "solo_specialist"
        assert arch_simple.verification_tier == VerificationTier.L1_SELF_CHECK
        assert arch_simple.context_budget.total_tokens == 128000

        # Deep reasoning task
        arch_deep = mp.select_architecture("Prove consensus algorithm safety and refactor architecture")
        assert arch_deep.model_tier == "deep_reason"
        assert arch_deep.agent_topology == "hierarchical_swarm"
        assert arch_deep.verification_tier == VerificationTier.L5_DETERMINISTIC_ORACLE
        assert arch_deep.context_budget.total_tokens == 200000

        # Critical security task
        arch_sec = mp.select_architecture("Modify authentication crypto sandbox", risk_level="critical")
        assert arch_sec.model_tier == "frontier_astra"
        assert arch_sec.agent_topology == "dialectical_debate"
        assert arch_sec.verification_tier == VerificationTier.L5_DETERMINISTIC_ORACLE

    def test_executive_kernel_controllers(self):
        exec_k = ExecutiveKernel()

        # Goal Controller
        contract = exec_k.goals.compile_goal("Optimize queries", invariants=["no_data_loss"])
        assert contract.objective == "Optimize queries"
        inv_names = {i.name for i in contract.invariants}
        assert "existing_code_must_not_be_deleted" in inv_names
        assert "no_data_loss" in inv_names

        # State Controller
        exec_k.state.transition_to("PLANNING", "Compiling plan")
        assert exec_k.state.current_state == "PLANNING"
        assert len(exec_k.state.state_history) == 1

        # Resource Controller
        assert exec_k.resources.consume_tokens(50000) is True
        assert exec_k.resources.tokens_used == 50000
        assert exec_k.resources.is_time_exhausted() is False

        # Safety Controller
        safe, msg = exec_k.safety.authorize_action("shell", {"cmd": "echo 'safe'"}, contract)
        assert safe is True

        unsafe, msg = exec_k.safety.authorize_action("shell", {"cmd": "rm -rf /"}, contract)
        assert unsafe is False
        assert "Dangerous command" in msg

        violating, msg = exec_k.safety.authorize_action("code", {"deleted_existing_files": True}, contract)
        assert violating is False
        assert "existing_code_must_not_be_deleted" in msg

    @pytest.mark.asyncio
    async def test_action_loop_execution(self, tmp_path):
        os_kernel = HermesIntelligenceOS(workspace_root=str(tmp_path))
        result = await os_kernel.loops.execute_action_loop(
            action_type="execute_python",
            action_args={"code": "computed_val = 10 * 42\ncomputed_val"},
            context_summary="Test action calculation",
        )

        assert result["success"] is True
        assert result["output"] == 420
        assert "420" in result["observation"]

        # World model ingested observation
        fact_belief = os_kernel.world_model.beliefs.get_belief("execute_python_succeeded")
        assert fact_belief is not None

    @pytest.mark.asyncio
    async def test_end_to_end_mission_execution(self, tmp_path):
        os_kernel = HermesIntelligenceOS(workspace_root=str(tmp_path))
        mission = await os_kernel.execute_mission(
            request="Synthesize high performance memory allocator",
            risk_level="medium",
        )

        assert mission["status"] == "completed"
        assert mission["mission_id"].startswith("m-")
        assert mission["os_state"] == "COMPLETED"
        assert mission["proof"]["verified"] is True
        assert mission["trajectory_id"].startswith("traj-")

        # Verify trajectory persisted in TrajectoryArchive
        traj_file = tmp_path / ".hermes" / "trajectories" / f"{mission['trajectory_id']}.json"
        assert traj_file.exists()

        # Verify procedural memory learned workflow
        assert os_kernel.memory.procedural.count() >= 1

    def test_daily_cycle_loops(self, tmp_path):
        os_kernel = HermesIntelligenceOS(workspace_root=str(tmp_path))
        cycle = os_kernel.run_daily_cycle()

        assert "capability_loop" in cycle
        assert "evolution_loop" in cycle
        assert "meta_evolution_loop" in cycle
        assert cycle["meta_evolution_loop"]["status"] == "nominal"
