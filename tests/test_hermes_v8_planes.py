"""
Unit and Integration Tests for Hermes Intelligence OS (v8 Final Architecture)
=============================================================================
Comprehensive test suite covering all 18 planes:
01. Universal Event Bus & Interaction Plane
02. Identity & Authority Plane
03. External Safety & Trust Kernel
04. Goal / Mission Plane
05. Executive Control Plane (14 OS Controllers)
06. Context OS (Compaction, Rebalancing, Persisted Reasoning)
07. Memory OS (9 Domains + Persistent Trajectory Archive)
08. World Model OS (Tycho Active Abstraction Gate)
09. Research & Knowledge Engine
10. Cognitive OS & Meta-Reasoning Turn
11. Planning & Meta-Planner
12. Recursive Agent Fabric (Prime Agent Model)
13. Tool Environment & Computer OS
14. Reality Verification Engine
15. Recovery OS & AVO Stagnation Detection
16. Curriculum & Co-Evolving Practice Engine
17. Population Evolution Lab & Anti-Reward-Hacking
18. External Supervisor & 24/7 Persistent Background Daemon
"""

import asyncio

import pytest

from context_os import ContextBudget, ContextCompiler
from hermes_os import (
    AgentMessage,
    AgentRole,
    AuthorityContext,
    AuthorityGate,
    AVOStagnationDetector,
    CheckpointSnapshot,
    CognitiveResearchEngine,
    ComputerOS,
    CurriculumEngine,
    ExecutiveKernel,
    ExternalSupervisor,
    FailureCategory,
    HermesEvent,
    HermesIntelligenceOS,
    MetaCognitionEngine,
    MissionPriority,
    PersistentDaemonRuntime,
    PopulationEvolutionLab,
    ReasoningMode,
    RecoveryEngine,
    RecursiveAgentFabric,
    SafetyKernel,
    SafetyVerdict,
    StagnationLevel,
    SupervisorTelemetry,
    SupervisoryIntervention,
    ToolEnvironmentOS,
    UniversalEventBus,
)
from memory import MemoryOS, Trajectory, TrajectoryStep
from world_model import (
    AbstractionMode,
    ActiveAbstractionGate,
)

# =============================================================================
# 1. Plane 01: Universal Event Bus
# =============================================================================

class TestPlane01UniversalEventBus:
    def test_sync_event_publishing_and_pattern_matching(self, tmp_path):
        bus = UniversalEventBus(workspace_root=str(tmp_path))
        received = []

        bus.subscribe("mission.*", lambda ev: received.append(ev))
        bus.subscribe("kernel.*", lambda ev: received.append(ev))

        bus.publish(HermesEvent(event_type="mission.created", payload={"id": "m1"}))
        bus.publish(HermesEvent(event_type="mission.completed", payload={"id": "m1"}))
        bus.publish(HermesEvent(event_type="tool.executed", payload={"tool": "repl"}))

        assert len(received) == 2
        assert received[0].event_type == "mission.created"
        assert received[1].event_type == "mission.completed"

    @pytest.mark.asyncio
    async def test_async_event_publishing(self, tmp_path):
        bus = UniversalEventBus(workspace_root=str(tmp_path))
        async_events = []

        async def async_handler(ev: HermesEvent):
            await asyncio.sleep(0.01)
            async_events.append(ev)

        bus.subscribe_async("system.*", async_handler)
        await bus.publish_async(HermesEvent(event_type="system.alert", payload={"severity": "high"}))

        assert len(async_events) == 1
        assert async_events[0].payload["severity"] == "high"


# =============================================================================
# 2. Plane 02: Identity & Authority Plane
# =============================================================================

class TestPlane02IdentityAndAuthority:
    def test_authority_evaluation_and_scoping(self):
        gate = AuthorityGate()
        # Admin is authorized for everything
        auth_admin, _ = gate.evaluate_authorization("system:master", "arbitrary_tool", "*")
        assert auth_admin is True

        # Custom limited worker
        worker_grant = AuthorityContext(
            principal="agent:intern",
            scope=["read", "write:workspace"],
            capabilities=["read_file", "python_repl"],
            resource_limits={"max_tokens": 1000},
        )
        gate.register_grant(worker_grant)

        # Allowed tool & scope
        ok, msg = gate.evaluate_authorization("agent:intern", "python_repl", "write:workspace")
        assert ok is True

        # Disallowed tool
        denied_tool, msg = gate.evaluate_authorization("agent:intern", "bash_tool", "write:workspace")
        assert denied_tool is False
        assert "not in allowed capabilities" in msg

        # Quota breach
        quota_fail, msg = gate.evaluate_authorization(
            "agent:intern", "read_file", "read", resource_usage={"tokens_used": 1500}
        )
        assert quota_fail is False
        assert "quota" in msg.lower()

    def test_subagent_authority_attenuation(self):
        gate = AuthorityGate()
        parent = AuthorityContext(
            principal="agent:senior",
            scope=["read", "write:code"],
            capabilities=["python_tool", "filesystem_tool"],
            resource_limits={"max_tokens": 100000, "max_execution_seconds": 200, "max_subagent_depth": 2},
        )
        gate.register_grant(parent)

        child = gate.inherit_grant_for_subagent(parent, "agent:junior", child_scope=["read"])
        assert child.scope == ["read"]
        assert child.resource_limits["max_tokens"] <= parent.resource_limits["max_tokens"] // 2
        assert child.resource_limits["max_subagent_depth"] == 1


# =============================================================================
# 3. Plane 03: Safety & Trust Kernel
# =============================================================================

class TestPlane03SafetyAndTrustKernel:
    def test_dangerous_command_blocking(self):
        kernel = SafetyKernel()
        verdict, reason, risk = kernel.evaluate_action(
            action_type="execute_shell",
            action_args={"command": "rm -rf /"},
        )
        assert verdict == SafetyVerdict.BLOCK
        assert risk == 1.0
        assert "Dangerous system command" in reason

    def test_taint_propagation_detection(self):
        kernel = SafetyKernel()
        kernel.register_taint("untrusted_user_input_payload")
        assert kernel.is_tainted("untrusted_user_input_payload") is True

        # Tainted input passed into code execution is blocked
        verdict, reason, risk = kernel.evaluate_action(
            action_type="execute_python",
            action_args={"code": "untrusted_user_input_payload"},
        )
        assert verdict == SafetyVerdict.BLOCK
        assert "Tainted data" in reason


# =============================================================================
# 4. Plane 04 & 05: Executive Kernel 14 Controllers
# =============================================================================

class TestPlane04And05ExecutiveKernel:
    def test_all_14_controllers_initialized(self):
        exec_k = ExecutiveKernel()
        assert exec_k.goals is not None
        assert exec_k.missions is not None
        assert exec_k.state is not None
        assert exec_k.decisions is not None
        assert exec_k.context is not None
        assert exec_k.planning is not None
        assert exec_k.agents is not None
        assert exec_k.tools is not None
        assert exec_k.resources is not None
        assert exec_k.verification is not None
        assert exec_k.learning is not None
        assert exec_k.evolution is not None
        assert exec_k.safety is not None
        assert exec_k.health is not None

    def test_health_heartbeat_and_stalls(self):
        exec_k = ExecutiveKernel()
        assert exec_k.health.is_alive() is True
        exec_k.health.heartbeat()
        assert exec_k.health.last_heartbeat > 0


# =============================================================================
# 5. Plane 06: Context OS Compaction & Dynamic Rebalancing
# =============================================================================

class TestPlane06ContextOSCompaction:
    def test_compaction_and_partition_rebalancing(self):
        compiler = ContextCompiler(budget=ContextBudget.standard_128k())
        long_scratchpad = "\n".join(f"Line {i}: exploring subtask details..." for i in range(50))
        compacted = compiler.compact(long_scratchpad, max_chars=200)
        assert len(compacted) <= 400
        assert len(compacted) < len(long_scratchpad)
        assert "compacted" in compacted

        # Test rebalancing: spare tokens from sparse retrieval move to working
        rebalanced = compiler.rebalance_budget(retrieved_items_count=1, working_tasks_count=10)
        assert rebalanced["working"] > ContextBudget.standard_128k().working


# =============================================================================
# 6. Plane 07: Memory OS 9 Domains
# =============================================================================

class TestPlane07MemoryOS9Domains:
    def test_9_memory_domains_and_trajectory_memory(self, tmp_path):
        mos = MemoryOS(workspace_root=str(tmp_path))
        traj = Trajectory(
            trajectory_id="tr-fast-01",
            mission_id="m-01",
            task_description="Quick cache flush",
            steps=[TrajectoryStep("s1", "ready", "flush", "exec", {}, "done", "success")],
        )

        mos.trajectory.store(traj)
        assert mos.trajectory.count() == 1
        assert mos.trajectory.get("tr-fast-01") == traj

        stats = mos.stats()
        assert "in_memory_trajectories" in stats
        assert stats["in_memory_trajectories"] == 1


# =============================================================================
# 7. Plane 08: World Model & Tycho Active Abstraction
# =============================================================================

class TestPlane08TychoActiveAbstraction:
    def test_tycho_active_abstraction_gate(self):
        gate = ActiveAbstractionGate()

        # Simple read task -> bypass world model
        dec_simple = gate.evaluate("view file content", risk_level="low")
        assert dec_simple.mode == AbstractionMode.DIRECT_INTERACTION
        assert dec_simple.estimated_cost_ratio < 0.2

        # Complex architectural task -> full grounded model
        dec_complex = gate.evaluate("Refactor distributed consensus and allocator", risk_level="critical")
        assert dec_complex.mode == AbstractionMode.WORLD_MODEL_GROUNDED
        assert dec_complex.requires_causal_graph is True


# =============================================================================
# 8. Plane 09: Cognitive Research Engine
# =============================================================================

class TestPlane09CognitiveResearchEngine:
    @pytest.mark.asyncio
    async def test_unknown_detection_and_claim_verification(self, tmp_path):
        engine = CognitiveResearchEngine(workspace_root=str(tmp_path))
        unknowns = engine.detect_unknowns(
            task_description="Synthesize novel cryptographic accumulator",
            existing_knowledge=["standard hash", "basic arrays"],
        )
        assert len(unknowns) >= 1

        claims = await engine.conduct_research(query="cryptographic accumulator")
        assert len(claims) >= 1
        assert claims[0].verification_status == "verified"
        assert claims[0].confidence > 0.8


# =============================================================================
# 9. Plane 10: Cognitive OS & Meta-Reasoning
# =============================================================================

class TestPlane10CognitiveAndMetaReasoning:
    def test_pre_action_meta_reasoning_turn(self):
        meta_cog = MetaCognitionEngine()
        assessment = meta_cog.evaluate_intent(
            task_description="Diagnose cause of memory leak and race condition",
            risk_level="high",
        )
        assert assessment.recommended_reasoning_mode == ReasoningMode.CAUSAL
        assert assessment.requires_simulation is True
        assert len(assessment.key_assumptions) >= 1
        assert len(assessment.falsification_criteria) >= 1


# =============================================================================
# 10. Plane 12: Recursive Agent Fabric
# =============================================================================

class TestPlane12RecursiveAgentFabric:
    def test_recursive_subagent_spawning_and_direct_messaging(self):
        fabric = RecursiveAgentFabric(max_global_depth=3)

        # Level 1 coordinator
        coord = fabric.spawn_subagent(role=AgentRole.ARCHITECT, token_budget=80000)
        assert coord.depth == 1

        # Level 2 specialist
        worker = fabric.spawn_subagent(role=AgentRole.CODER, parent_handle=coord)
        assert worker.depth == 2
        assert worker.token_budget <= coord.token_budget // 2

        # Direct typed message passing
        msg = AgentMessage(
            task_id="t-sub-01",
            sender=coord.agent_id,
            receiver=worker.agent_id,
            content="Implement caching schema",
        )
        fabric.send_message(msg)

        inbox = fabric.receive_messages(worker.agent_id)
        assert len(inbox) == 1
        assert inbox[0].content == "Implement caching schema"


# =============================================================================
# 11. Plane 13: Tool Environment & Computer OS
# =============================================================================

class TestPlane13ToolAndComputerOS:
    @pytest.mark.asyncio
    async def test_tool_registry_and_repl_execution(self, tmp_path):
        env = ToolEnvironmentOS(workspace_root=str(tmp_path))
        tools = env.list_tools()
        assert len(tools) >= 2

        res = await env.execute_tool("python_repl", {"code": "x = 7 * 8\nx"})
        assert res["success"] is True
        assert res["output"] == 56

    def test_computer_os_screen_perception_and_actuation(self):
        computer = ComputerOS()
        snap = computer.observe_screen("browser_window")
        assert len(snap.elements) >= 2

        click_res = computer.click("Submit")
        assert click_res["success"] is True
        assert click_res["action"] == "click"

        type_res = computer.type_text("search query")
        assert type_res["success"] is True


# =============================================================================
# 12. Plane 15: Recovery OS & AVO Stagnation Detection
# =============================================================================

class TestPlane15RecoveryAndAVOStagnation:
    def test_avo_stagnation_detection_levels(self):
        detector = AVOStagnationDetector(loop_threshold=3, plateau_seconds=1.0)
        # Nominal initially
        assert detector.evaluate_stagnation().level == StagnationLevel.NOMINAL

        # Simulate repeated identical action trap
        for _ in range(3):
            detector.record_step("repeated_failing_action", success=False, error="SyntaxError: invalid token")

        stagnation = detector.evaluate_stagnation()
        assert stagnation.level in (StagnationLevel.PLATEAU, StagnationLevel.CRITICAL_LOOP)
        assert "supervisor" in stagnation.recommended_intervention or "strategy" in stagnation.recommended_intervention

    def test_failure_diagnosis_and_counterfactual_repair(self):
        recovery = RecoveryEngine()
        diag = recovery.diagnose("IndentationError in generated file", "code_generator")
        assert diag.category == FailureCategory.TOOL_EXECUTION
        assert "format" in diag.counterfactual_alternative.lower() or "reformat" in diag.recommended_action.lower()


# =============================================================================
# 13. Plane 16: Curriculum Engine
# =============================================================================

class TestPlane16CurriculumEngine:
    def test_curriculum_generation_and_evaluation(self, tmp_path):
        mos = MemoryOS(workspace_root=str(tmp_path))
        # Seed a weak capability
        mos.capability.update_capability(name="concurrency_synchronization", domain="systems", success=False)
        curriculum = CurriculumEngine(capability_memory=mos.capability)

        weaknesses = curriculum.detect_weaknesses(threshold=0.75)
        assert len(weaknesses) == 1

        batch = curriculum.generate_curriculum_batch(count_per_weakness=2)
        assert len(batch) >= 2

        # Record practice result
        curriculum.record_practice_result(batch[0].task_id, success=True, duration=0.5)
        updated = mos.capability.get_capability("concurrency_synchronization")
        assert updated.invocations == 2
        assert updated.success_rate > 0.0


# =============================================================================
# 14. Plane 17: Population Evolution Lab
# =============================================================================

class TestPlane17PopulationEvolutionLab:
    def test_population_diversity_and_anti_reward_hacking(self, tmp_path):
        lab = PopulationEvolutionLab(population_size=3, workspace_root=str(tmp_path))
        assert len(lab.all_variants()) >= 1

        candidates = lab.spawn_generation()
        assert len(candidates) >= 1

        # Evaluate candidate with anti-reward-hacking analysis
        result = lab.evaluate_and_select(candidates[0].variant_id, candidate_code_diff="# legitimate optimization")
        assert result["success"] is True

        # Malicious diff with tautological assertion gaming is rejected
        gaming_result = lab.evaluate_and_select(candidates[0].variant_id, candidate_code_diff="assert True\npass")
        assert gaming_result["success"] is False
        assert gaming_result["status"] == "rejected"


# =============================================================================
# 15. Plane 18: External Supervisor & 24/7 Daemon
# =============================================================================

class TestPlane18SupervisorAndPersistentDaemon:
    def test_external_supervisor_telemetry_interventions(self):
        sup = ExternalSupervisor()
        telemetry_stalled = SupervisorTelemetry(
            mission_id="m-stall-01",
            active_agent_id="coder-1",
            elapsed_seconds=120.0,
            tokens_consumed=400000,
            tool_calls_count=50,
            stagnation_detected=True,
            stagnation_reason="identical_error_loop",
        )
        action = sup.ingest_telemetry(telemetry_stalled)
        assert action.intervention == SupervisoryIntervention.CHANGE_STRATEGY

    def test_persistent_daemon_queue_and_checkpoints(self, tmp_path):
        daemon = PersistentDaemonRuntime(workspace_root=str(tmp_path))
        mid = daemon.enqueue_mission("Perform daily automated backup", priority=MissionPriority.HIGH)
        assert daemon.pending_count() == 1

        ckpt = CheckpointSnapshot(
            checkpoint_id="chk-01",
            mission_id=mid,
            objective="Backup",
            completed_steps=["step-1"],
            pending_steps=["step-2"],
            state_registers={"db": "dumped"},
            world_state_summary="Partial",
            tokens_consumed=500,
            status="in_progress",
        )
        daemon.save_checkpoint(ckpt)

        # File persisted to disk
        saved = tmp_path / ".hermes" / "checkpoints" / f"{mid}.json"
        assert saved.exists()

        # Crash reconstruction finds interrupted mission
        interrupted = daemon.reconstruct_from_crash()
        assert len(interrupted) == 1
        assert interrupted[0].mission_id == mid


# =============================================================================
# 16. Hermes Intelligence OS v8 Master Kernel End-to-End Test
# =============================================================================

class TestHermesIntelligenceOSv8EndToEnd:
    @pytest.mark.asyncio
    async def test_full_18_plane_mission_execution(self, tmp_path):
        os_kernel = HermesIntelligenceOS(workspace_root=str(tmp_path))
        result = await os_kernel.execute_mission(
            request="Synthesize high-performance distributed cache allocator",
            risk_level="medium",
        )

        assert result["status"] == "completed"
        assert result["os_state"] == "COMPLETED"
        assert result["proof"]["verified"] is True
        assert result["abstraction"] in (AbstractionMode.WORLD_MODEL_GROUNDED.value, AbstractionMode.DIRECT_INTERACTION.value)
        assert result["meta_reasoning"]["confidence"] > 0.5
        assert result["supervisor_action"] == "continue"

        # Verify event was published
        events = os_kernel.events.get_history("mission.*")
        assert len(events) >= 2

        # Verify checkpoint is recorded
        assert os_kernel.daemon.active_checkpoints_count() >= 1

    def test_full_daily_cycle(self, tmp_path):
        os_kernel = HermesIntelligenceOS(workspace_root=str(tmp_path))
        cycle = os_kernel.run_daily_cycle()

        assert "capability_loop" in cycle
        assert "curriculum_generated" in cycle
        assert "evolution_loop" in cycle
        assert "meta_evolution_loop" in cycle
        assert "population_audit" in cycle
        assert cycle["population_audit"]["population_size"] >= 1
