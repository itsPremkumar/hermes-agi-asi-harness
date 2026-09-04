"""
Unit tests for the 4 Advanced Deep Agent Frontiers:
1. Full Cognitive Deep Agent Implementations (src/agents/implementations.py)
2. Autonomous Meta-Agent Factory (src/agents/meta_factory.py)
3. 24/7 Darwinian Continuous Improvement Cycle (src/daily_improvement/continuous_cycle.py)
4. Dialectical Consensus Swarm in Multi-Agent Mesh (src/mesh/advanced_orchestrator.py)
"""

from __future__ import annotations

import pytest

from agents.implementations import (
    CoderAgent,
    ExecutorAgent,
    PlannerAgent,
    ResearcherAgent,
    ReviewerAgent,
    VerifierAgent,
)
from agents import MetaAgentFactory
from daily_improvement.continuous_cycle import ContinuousCycle, CycleStatus
from mesh.advanced_orchestrator import MultiAgentOrchestrator


class TestCognitiveAgentRoles:
    """Test the upgraded cognitive capabilities of the 6 core agent roles."""

    @pytest.mark.asyncio
    async def test_coder_agent_generation_and_review(self):
        coder = CoderAgent()
        code_res = await coder.generate_code("calculate matrix determinant")
        assert code_res["verified"] is True
        assert "def calculate_matrix_determinant" in code_res["code"]
        assert len(code_res["tests"]) > 0

        # Review clean code
        review_clean = await coder.review_code(code_res["code"])
        assert review_clean["clean"] is True
        assert review_clean["score"] >= 0.9

        # Review tautological/gaming code
        gaming_code = "def test_fake():\n    assert True\n"
        review_gaming = await coder.review_code(gaming_code)
        assert review_gaming["score"] < 0.5 or len(review_gaming["issues"]) > 0

    @pytest.mark.asyncio
    async def test_planner_agent_mcts_plan(self):
        planner = PlannerAgent()
        plan_res = await planner.create_plan("scale redis pubsub clustering")
        assert len(plan_res["steps"]) >= 3
        assert "strategy" in plan_res
        assert plan_res["estimated_time"] > 0

    @pytest.mark.asyncio
    async def test_reviewer_agent_adversarial_critique(self):
        reviewer = ReviewerAgent()
        critique = await reviewer.review(
            "global_cache = {}\ndef get(k): return global_cache[k]",
            ["thread_safety", "bounds_checking"],
        )
        assert critique["score"] > 0.0
        assert len(critique["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_verifier_agent_quality_gates(self):
        verifier = VerifierAgent()
        res = await verifier.verify("verified_module.py contents", ["syntax_valid", "unit_tested"])
        assert res["passed"] is True
        assert len(res["test_results"]) == 2

    @pytest.mark.asyncio
    async def test_executor_agent_rlm_execution(self):
        executor = ExecutorAgent()
        res = await executor.execute_task({
            "id": "t-exec-1",
            "code": "a = [x * 2 for x in range(4)]; sum(a)",
        })
        assert res["success"] is True
        assert res["output"] == 12


class TestMetaAgentFactory:
    """Test autonomous dynamic synthesis of specialized Deep Agents."""

    def test_synthesize_triton_optimizer(self):
        factory = MetaAgentFactory()
        agent = factory.synthesize("Synthesize Triton GPU flash attention kernel")
        assert agent.spec.domain == "accelerated_computing"
        assert "memory_coalescing" in agent.spec.verification_invariants
        assert "rlm_repl" in agent.spec.tool_whitelist

    @pytest.mark.asyncio
    async def test_meta_agent_execution_in_rlm(self):
        factory = MetaAgentFactory()
        agent = factory.synthesize("Analyze SQL database query execution plan index scan")
        assert agent.spec.domain == "data_engineering"
        res = await agent.execute("Analyze SELECT * FROM users query")
        assert res["success"] is True
        assert "role" in res["output"]


class TestDarwinianContinuousImprovement:
    """Test 24/7 continuous cycle connection to real self-evolution."""

    def test_darwinian_cycle_execution(self):
        cycle = ContinuousCycle()
        result = cycle.run_darwinian_cycle()
        assert result["status"] in (CycleStatus.PASSED, CycleStatus.FAILED)
        assert len(cycle._scores) >= 1
        assert len(cycle._progress) >= 1


class TestDialecticalMeshConsensus:
    """Test multi-agent dialectical debate in the orchestrator mesh."""

    @pytest.mark.asyncio
    async def test_orchestrator_debate_consensus(self):
        orchestrator = MultiAgentOrchestrator()
        result = await orchestrator.orchestrate_with_dialectical_debate(
            task_id="mesh-task-1",
            proposal="Implement multi-leader Raft consensus replication",
            rounds=2,
        )
        assert result.agreed is True
        assert result.confidence >= 0.6
        assert len(result.votes) >= 2
        assert result.result is not None
