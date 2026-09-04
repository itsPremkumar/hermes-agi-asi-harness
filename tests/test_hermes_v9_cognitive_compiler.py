"""
HERMES INTELLIGENCE OS (v9) — COGNITIVE COMPILER TEST SUITE
===========================================================
Comprehensive empirical tests for the v9 Cognitive Planning & Autonomous Execution Architecture:
- Mission IR & Goal Lifecycles
- Dynamic Goal Graph, Topological Sort, Cycle Detection, Execution Waves, Critical Path
- Goal Memory (Active vs Archived separation)
- Environment Reconnaissance Engine (Hardware, OS, Git, Packages)
- Capability Registry, On-Demand Skill Loader, Control-Plane Commands, Capability Selector
- Epistemic Uncertainty Analysis & Value of Information (VOI)
- Strategy Search, Multi-attribute Evaluation & Adversarial Plan Critic
- End-to-End 22-Phase Cognitive Compiler Engine (P0 to P21)
- Dynamic Runtime Bridges (LangGraph Dynamic StateGraph & Deep Agents Isolated Workspaces)
- Plan Validity Monitor (Local vs Global Replanning)
- Hermes Intelligence OS v9 End-to-End Integration
"""

from __future__ import annotations

import tempfile
import pytest

from hermes_os import (
    HermesIntelligenceOS,
    # Mission IR & Goal Graph
    GoalGraph,
    GoalInvariant,
    GoalLifecycle,
    GoalMemory,
    GoalNode,
    MissionIR,
    # Environment Recon
    EnvironmentReconEngine,
    EnvironmentState,
    HardwareProfile,
    # Capabilities
    CapabilityGraph,
    CapabilityKind,
    CapabilityManifest,
    CapabilityRegistry,
    CapabilitySelector,
    ExecutionCapabilityPlan,
    # Uncertainty
    EpistemicItem,
    EpistemicStatus,
    ResearchLaneType,
    ResearchPlan,
    UncertaintyAnalyzer,
    # Strategy & Critic
    PlanCritic,
    PlanReviewReport,
    SecondOpinionJudge,
    StrategyCandidate,
    StrategySearchEngine,
    # Cognitive Compiler
    CognitiveCompiler,
    ExecutionPlanIR,
    ExecutionWave,
    PlanningPhase,
    PlanningRecord,
    PlanValidityMonitor,
    # Dynamic Runtime Bridges
    DeepAgentsAdapter,
    DynamicStateGraph,
    IsolatedSubagentWorkspace,
    LangGraphDynamicAdapter,
)


# =====================================================================
# 1. Mission IR & Goal Lifecycle Tests
# =====================================================================

def test_goal_lifecycle_transitions():
    goal = GoalNode(
        goal_id="g1",
        title="Initialize Database",
        description="Run initial schema migration",
        status=GoalLifecycle.CREATED,
    )
    assert goal.status == GoalLifecycle.CREATED

    goal.transition_to(GoalLifecycle.PLANNED, reason="Compilation complete")
    assert goal.status == GoalLifecycle.PLANNED

    goal.transition_to(GoalLifecycle.ACTIVE, reason="Dispatched to worker")
    assert goal.status == GoalLifecycle.ACTIVE

    goal.transition_to(GoalLifecycle.COMPLETED, reason="Exit code 0 verified")
    assert goal.status == GoalLifecycle.COMPLETED


def test_goal_invariant():
    inv = GoalInvariant(
        name="no_data_loss",
        description="Do not drop production tables",
        severity="CRITICAL",
        rule_expression="DROP TABLE NOT IN query",
    )
    assert inv.is_active is True
    d = inv.to_dict()
    assert d["name"] == "no_data_loss"
    assert d["severity"] == "CRITICAL"


# =====================================================================
# 2. Dynamic Goal Graph Tests
# =====================================================================

def test_goal_graph_topological_sort_and_waves():
    graph = GoalGraph()

    g1 = GoalNode(goal_id="g1_recon", title="Reconnaissance", description="Inspect repo")
    g2 = GoalNode(goal_id="g2_backend", title="Backend Code", description="Write API", depends_on=["g1_recon"])
    g3 = GoalNode(goal_id="g3_frontend", title="Frontend Code", description="Write UI", depends_on=["g1_recon"])
    g4 = GoalNode(goal_id="g4_tests", title="Integration Tests", description="Run tests", depends_on=["g2_backend", "g3_frontend"])

    graph.add_goal(g1)
    graph.add_goal(g2)
    graph.add_goal(g3)
    graph.add_goal(g4)

    # 1. Cycle detection
    assert graph.detect_cycles() is False

    # 2. Topological sort
    order = graph.topological_sort()
    assert order.index("g1_recon") < order.index("g2_backend")
    assert order.index("g1_recon") < order.index("g3_frontend")
    assert order.index("g2_backend") < order.index("g4_tests")
    assert order.index("g3_frontend") < order.index("g4_tests")

    # 3. Execution waves
    waves = graph.compute_execution_waves()
    assert len(waves) == 3
    assert waves[0] == ["g1_recon"]
    assert set(waves[1]) == {"g2_backend", "g3_frontend"}  # Parallel wave!
    assert waves[2] == ["g4_tests"]

    # 4. Critical path
    crit_path = graph.extract_critical_path()
    assert len(crit_path) >= 3
    assert crit_path[0] == "g1_recon"
    assert crit_path[-1] == "g4_tests"


def test_goal_graph_cycle_detection():
    graph = GoalGraph()
    g1 = GoalNode(goal_id="a", title="A", description="A", depends_on=["b"])
    g2 = GoalNode(goal_id="b", title="B", description="B", depends_on=["a"])
    graph.add_goal(g1)
    graph.add_goal(g2)

    assert graph.detect_cycles() is True
    with pytest.raises(ValueError, match="Cycle detected"):
        graph.topological_sort()


# =====================================================================
# 3. Goal Memory Tests
# =====================================================================

def test_goal_memory_active_vs_archived():
    mem = GoalMemory()
    g_active = GoalNode(goal_id="act-1", title="Build Auth Service", description="OAuth2 backend")
    g_past = GoalNode(goal_id="past-1", title="Legacy Auth Service", description="Old basic auth")

    mem.register_goal(g_active, is_active=True)
    mem.register_goal(g_past, is_active=False)

    # Active goals query
    active = mem.get_active_goals()
    assert len(active) == 1
    assert active[0].goal_id == "act-1"

    # Archive active goal
    mem.archive_goal("act-1", final_status=GoalLifecycle.COMPLETED)
    assert len(mem.get_active_goals()) == 0

    # Search previous goals
    similar = mem.search_similar_goals("Auth Service")
    assert len(similar) >= 1
    assert "Auth" in similar[0].title


# =====================================================================
# 4. Environment Reconnaissance Engine Tests
# =====================================================================

def test_environment_recon_engine():
    with tempfile.TemporaryDirectory() as tmp_dir:
        recon = EnvironmentReconEngine(workspace_root=tmp_dir)
        state = recon.inspect()

        assert isinstance(state, EnvironmentState)
        assert state.hardware.cpu_cores >= 1
        assert state.python_version != ""
        assert len(state.available_shells) >= 1

        summary = state.to_prompt_summary()
        assert "Environment State Reconnaissance" in summary
        assert "Python" in summary


# =====================================================================
# 5. Capability Awareness Registry & On-Demand Skills Tests
# =====================================================================

def test_capability_registry_and_selector():
    registry = CapabilityRegistry()

    # Models, Tools, Skills, Commands registered
    all_caps = registry.list_capabilities()
    assert len(all_caps) >= 10

    # Test on-demand skill loading
    skill = registry.get("skill.deep_research")
    assert skill is not None
    assert skill.is_loaded is False  # Compact metadata initially

    body = registry.load_skill_body("skill.deep_research")
    assert body is not None
    assert skill.is_loaded is True  # Loaded on-demand

    # Test capability selection deliberation
    selector = CapabilitySelector(registry=registry)
    plan = selector.select_for_task(
        task_id="t1",
        task_description="Research current competitor libraries and write Python calculation script",
        risk_level="medium",
    )

    assert isinstance(plan, ExecutionCapabilityPlan)
    assert "tool.python_repl" in plan.selected_tools
    assert "skill.deep_research" in plan.selected_skills
    assert len(plan.selected_models) >= 1


# =====================================================================
# 6. Uncertainty Analysis & Value of Information Tests
# =====================================================================

def test_uncertainty_analysis_and_voi():
    analyzer = UncertaintyAnalyzer()

    items = analyzer.analyze(
        request="Connect to production Postgres database API and optimize query throughput",
        explicit_assumptions=["Database credentials exist in .env"],
    )

    statuses = [i.status for i in items]
    assert EpistemicStatus.KNOWN in statuses
    assert EpistemicStatus.UNKNOWN in statuses
    assert EpistemicStatus.ASSUMED in statuses

    # Value of information
    voi = analyzer.compute_value_of_information(items)
    assert 0.0 <= voi <= 1.0
    assert voi > 0.3  # Unknowns present, VOI should be significant

    # Research plan generation
    r_plan = analyzer.generate_research_plan(
        objective="Postgres optimization",
        epistemic_items=items,
    )
    assert isinstance(r_plan, ResearchPlan)
    assert len(r_plan.queries) >= 2


# =====================================================================
# 7. Strategy Search & Adversarial Plan Critic Tests
# =====================================================================

def test_strategy_search_and_plan_critic():
    search = StrategySearchEngine()
    critic = PlanCritic()

    candidates = search.generate_candidates(
        objective="Migrate cache layer to redis",
        constraints=["Zero data loss", "Preserve existing API contracts"],
        risk_level="medium",
    )
    assert len(candidates) == 3
    for c in candidates:
        assert 0.0 <= c.probability_of_success <= 1.0
        assert c.composite_score > 0.0

    best = search.select_best_strategy(candidates)
    assert isinstance(best, StrategyCandidate)

    # Clean plan review
    tasks = [
        {"id": "t1", "action": "safe_inspect_cache", "description": "Inspect cache schema"},
        {"id": "t2", "action": "deploy_redis_layer", "description": "Deploy redis cache"},
    ]
    verifiers = [
        {"id": "v1", "target": "t1"},
        {"id": "v2", "target": "t2"},
    ]
    review = critic.review_plan(
        objective="Migrate cache layer",
        invariants=["Zero data loss"],
        strategy=best,
        tasks=tasks,
        verifiers=verifiers,
    )
    assert review.approved is True
    assert review.quality_score >= 0.70

    # Flawed plan review (dangerous action + verification gap)
    flawed_tasks = [
        {"id": "t1", "action": "drop_all_tables", "description": "Delete all data without backup"},
    ]
    review_flawed = critic.review_plan(
        objective="Migrate cache layer",
        invariants=["Zero data loss"],
        strategy=best,
        tasks=flawed_tasks,
        verifiers=[],
    )
    assert review_flawed.approved is False
    assert len(review_flawed.security_risks) >= 1
    assert len(review_flawed.verification_gaps) >= 1


# =====================================================================
# 8. End-to-End 22-Phase Cognitive Compiler Tests
# =====================================================================

def test_cognitive_compiler_22_phases():
    with tempfile.TemporaryDirectory() as tmp_dir:
        compiler = CognitiveCompiler(workspace_root=tmp_dir)

        plan_ir = compiler.compile(
            request="Build high-performance in-memory cache with regression tests",
            invariants=["zero deletion", "preserve verified claims"],
            risk_level="medium",
        )

        assert isinstance(plan_ir, ExecutionPlanIR)
        assert plan_ir.status in ["PLAN_APPROVED", "PLAN_NEEDS_REVISION"]
        assert len(plan_ir.execution_waves) >= 1
        assert len(plan_ir.task_graph.list_goals()) >= 2
        assert len(plan_ir.capability_plans) >= 1
        assert len(plan_ir.verification_contracts) >= 1

        # Check structured planning record provenance
        rec = plan_ir.planning_record
        assert isinstance(rec, PlanningRecord)
        assert len(rec.knowns) >= 2
        assert len(rec.decision_provenance) >= 1
        assert rec.chosen_strategy is not None


# =====================================================================
# 9. Dynamic Runtime Adapters (LangGraph & Deep Agents) Tests
# =====================================================================

def test_dynamic_runtime_adapters():
    with tempfile.TemporaryDirectory() as tmp_dir:
        compiler = CognitiveCompiler(workspace_root=tmp_dir)
        plan_ir = compiler.compile("Deploy logging subsystem")

        # 1. LangGraph Dynamic Adapter
        langgraph_adapter = LangGraphDynamicAdapter()
        graph = langgraph_adapter.compile_graph(plan_ir)
        assert isinstance(graph, DynamicStateGraph)
        assert len(graph.nodes) >= 2
        assert len(graph.entry_nodes) >= 1

        # 2. Deep Agents Subagent Sandbox Adapter
        deep_agents = DeepAgentsAdapter(base_workspace_root=tmp_dir)
        first_goal = plan_ir.task_graph.list_goals()[0]
        cap_plan = plan_ir.capability_plans.get(first_goal.goal_id)

        workspace = deep_agents.spawn_isolated_worker(
            mission_id=plan_ir.mission_id,
            task_id=first_goal.goal_id,
            task_title=first_goal.title,
            capability_plan=cap_plan,
            context_slice="Isolated logging config specs",
        )
        assert isinstance(workspace, IsolatedSubagentWorkspace)
        assert workspace.worker_id in deep_agents._active_workspaces
        assert "local_workspace" in workspace.context_package


# =====================================================================
# 10. Plan Validity Monitor Tests
# =====================================================================

def test_plan_validity_monitor():
    monitor = PlanValidityMonitor(validity_threshold=0.70)
    with tempfile.TemporaryDirectory() as tmp_dir:
        compiler = CognitiveCompiler(workspace_root=tmp_dir)
        plan = compiler.compile("Test validity monitor")

        # Nominal evaluation
        score, action = monitor.evaluate_validity(plan, environment_drift_severity="none")
        assert score >= 0.70
        assert action == "NOMINAL"

        # Minor drift -> Local Replan
        score_low, action_low = monitor.evaluate_validity(
            plan,
            environment_drift_severity="low",
            failed_dependencies_count=1,
        )
        assert action_low in ["LOCAL_REPLAN", "GLOBAL_REPLAN"]

        # Critical invariant violation -> Global Replan
        score_crit, action_crit = monitor.evaluate_validity(
            plan,
            environment_drift_severity="critical",
            invariant_violations_count=1,
        )
        assert action_crit == "GLOBAL_REPLAN"
        assert score_crit < 0.40


# =====================================================================
# 11. Full Hermes Intelligence OS v9 Integration Test
# =====================================================================

@pytest.mark.asyncio
async def test_hermes_intelligence_os_v9_integration():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os_kernel = HermesIntelligenceOS(workspace_root=tmp_dir)

        # Verify v9 subsystems are loaded
        assert isinstance(os_kernel.cognitive_compiler, CognitiveCompiler)
        assert isinstance(os_kernel.capabilities, CapabilityRegistry)
        assert isinstance(os_kernel.recon, EnvironmentReconEngine)
        assert isinstance(os_kernel.goal_memory, GoalMemory)
        assert isinstance(os_kernel.langgraph_adapter, LangGraphDynamicAdapter)
        assert isinstance(os_kernel.deep_agents_adapter, DeepAgentsAdapter)

        # 1. Compile Mission explicitly
        plan_ir = os_kernel.compile_mission(
            request="Implement distributed caching with telemetry",
            invariants=["zero deletion", "preserve verified claims"],
            risk_level="low",
        )
        assert isinstance(plan_ir, ExecutionPlanIR)
        assert plan_ir.status in ["PLAN_APPROVED", "PLAN_NEEDS_REVISION"]

        # 2. Execute full mission through kernel
        result = await os_kernel.execute_mission(
            request="Implement distributed caching with telemetry",
            invariants=["zero deletion", "preserve verified claims"],
            risk_level="low",
        )

        assert result["status"] == "completed"
        assert "plan_ir" in result
        assert "planning_record" in result
        assert result["plan_ir"]["validity_score"] > 0.0
        assert result["planning_record"]["decisions_count"] >= 1
