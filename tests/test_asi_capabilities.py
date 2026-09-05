"""
Unit tests for ASI-Level Capabilities:
- MCTS Tree-of-Thoughts Search
- Anti-Goodhart Hidden Holdout Verification
- Heterogeneous Multi-Model Adversarial Debate Mesh
- Causal World Model & Counterfactual Simulation
- Closed-Loop Recursive Self-Evolution
"""

from __future__ import annotations

from core.verification.anti_goodhart import AntiGoodhartVerifier, HoldoutVerdict
from engines import EvolutionCandidate, SelfEvolutionLoop
from hermes_agi.causal import CausalImpactReport, CausalImpactSimulator
from hermes_agi.thinking import MCTSResult, MCTSSearchEngine
from mesh import DebateSynthesis, HeterogeneousDebateMesh


class TestMCTSSearch:
    """Test Monte Carlo Tree Search over Thoughts."""

    def test_mcts_tree_generation(self):
        engine = MCTSSearchEngine(max_branching=2)
        res = engine.search("implement distributed consensus", max_rollouts=12, max_depth=3)
        assert isinstance(res, MCTSResult)
        assert res.total_nodes >= 5
        assert res.confidence > 0.0
        assert len(res.best_trajectory) >= 1
        assert res.best_strategy != ""


class TestAntiGoodhart:
    """Test Anti-Goodharting and Hidden Holdout Verifier."""

    def test_detect_assert_true_gaming(self):
        verifier = AntiGoodhartVerifier()
        cheating_code = "def solve():\n    assert True\n    return 1\n"
        verdict = verifier.verify("dummy.py", cheating_code)
        assert isinstance(verdict, HoldoutVerdict)
        assert verdict.detected_gaming is True
        assert verdict.passed is False

    def test_clean_code_no_gaming(self):
        verifier = AntiGoodhartVerifier()
        clean_code = "def solve(a, b):\n    return a + b\n"
        findings = verifier.analyze_code_for_gaming(clean_code)
        assert len(findings) == 0


class TestHeterogeneousDebate:
    """Test Heterogeneous Multi-Model Adversarial Debate Mesh."""

    def test_multi_perspective_debate(self):
        mesh = HeterogeneousDebateMesh(max_rounds=2)
        res = mesh.conduct_debate("event sourcing vs relational schema")
        assert isinstance(res, DebateSynthesis)
        assert res.consensus_score >= 0.70
        assert len(res.turns) >= 2
        assert len(res.key_invariants) >= 1


class TestCausalImpact:
    """Test Causal World Model & Counterfactual Simulator."""

    def test_causal_impact_simulation(self):
        sim = CausalImpactSimulator()
        report = sim.simulate_mutation("src/harnix/kernel.py")
        assert isinstance(report, CausalImpactReport)
        assert report.risk_level in ("low", "medium", "high")
        assert len(report.counterfactual_prediction) > 0


class TestSelfEvolution:
    """Test Closed-Loop Recursive Self-Evolution."""

    def test_self_evolution_evaluation(self):
        loop = SelfEvolutionLoop(minimum_improvement_margin=0.01)
        res = loop.evaluate_and_evolve(current_latency=0.10)
        assert isinstance(res, EvolutionCandidate)
        assert res.candidate_id.startswith("evo-")
        assert res.status in ("merged", "rejected")
