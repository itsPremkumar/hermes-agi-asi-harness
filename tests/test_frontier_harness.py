"""
Unit tests for Frontier Harness Architectures:
- Prime Agent RLM REPL Runtime (environment & agent context bridge)
- DeepSeek Harness Spatiotemporal Runtime Modes (ModeController & configs)
- Prime Agent Continual Self-Refinement Engine (/refine & learned rules)
"""

from __future__ import annotations

import pytest

from hermes_agi.rlm import RLMREPLExecutor, REPLExecutionResult
from hermes_agi.modes import ModeController, RuntimeMode, ModeConfig
from hermes_agi.refine import HarnessRefiner, RefinementReport


class TestRLMREPL:
    """Test Recursive Language Model (RLM) in-memory Python execution."""

    def test_variable_persistence_and_eval(self):
        repl = RLMREPLExecutor()
        r1 = repl.execute("data_matrix = [[1, 2], [3, 4]]")
        assert r1.success is True
        assert repl.get_variable("data_matrix") == [[1, 2], [3, 4]]

        r2 = repl.execute("sum(data_matrix[0])")
        assert r2.success is True
        assert r2.returned_value == 3

    def test_agent_bridge_callable_inside_repl(self):
        repl = RLMREPLExecutor()
        code = "t = agent.think('verify caching invariant', use_mcts=True)\n"
        res = repl.execute(code)
        assert res.success is True
        t_var = repl.get_variable("t")
        assert t_var is not None
        assert "best_strategy" in t_var


class TestRuntimeModes:
    """Test DeepSeek Harness-inspired spatiotemporal runtime modes."""

    def test_mode_classification(self):
        ctrl = ModeController()
        assert ctrl.classify_task("prove distributed consensus theorem") == RuntimeMode.DEEP_REASON
        assert ctrl.classify_task("refactor test suite with high coverage") == RuntimeMode.ENDURANCE_CODE
        assert ctrl.classify_task("evolve harness with darwinian loop") == RuntimeMode.SELF_EVOLVE
        assert ctrl.classify_task("show current time") == RuntimeMode.REACTIVE

    def test_mode_configurations(self):
        ctrl = ModeController()
        cfg_reason = ctrl.configure_mode(RuntimeMode.DEEP_REASON)
        assert cfg_reason.enable_mcts is True
        assert cfg_reason.enable_adversarial_debate is True

        cfg_code = ctrl.configure_mode(RuntimeMode.ENDURANCE_CODE)
        assert cfg_code.use_branch_isolation is True
        assert cfg_code.enable_in_harness_repair is True


class TestContinualRefinement:
    """Test Prime Agent-inspired /refine continual self-improvement."""

    def test_refine_execution(self, tmp_path):
        refiner = HarnessRefiner(workspace_root=str(tmp_path))
        report = refiner.refine()
        assert isinstance(report, RefinementReport)
        assert report.status == "refined"
        assert len(report.applied_refinements) >= 1
        assert (tmp_path / ".hermes" / "refinements" / "learned_rules.md").exists()
