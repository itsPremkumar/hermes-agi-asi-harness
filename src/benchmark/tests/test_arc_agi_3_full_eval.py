"""Tests for arc_agi_3_full_eval.py — ARC-AGI-3 Full Evaluation."""

import pytest
from benchmark.arc_agi_3_full_eval import (
    FullEvaluationSuite, FullEvalResult, LevelInfo, LevelResult,
    NUM_ENVIRONMENTS, NUM_LEVELS,
)


class TestLevelInfo:
    def test_create(self):
        info = LevelInfo(env_id="env_000", level_id="level_0000", index=0)
        assert info.env_id == "env_000"
        assert info.completed is False


class TestLevelResult:
    def test_create(self):
        result = LevelResult(
            level_id="level_0000",
            completed=True,
            score=0.85,
            actions_used=10,
            actions_budget=50,
        )
        assert result.completed is True


class TestFullEvalResult:
    def test_create(self):
        result = FullEvalResult(
            total_levels=183,
            completed_levels=150,
            total_actions=5000,
            overall_score=0.82,
            environment_scores={"env_000": 0.9},
            level_results={},
        )
        assert result.total_levels == 183


class TestFullEvaluationSuite:
    def test_create(self):
        suite = FullEvaluationSuite()
        assert suite.get_state()["total_levels"] == 0

    def test_load_all_levels(self):
        suite = FullEvaluationSuite()
        levels = suite.load_all_levels()
        assert len(levels) == NUM_ENVIRONMENTS

    def test_run_level(self):
        suite = FullEvaluationSuite()
        suite.load_all_levels()
        result = suite.run_level("env_000", "level_0000")
        assert isinstance(result, LevelResult)

    def test_run_all_levels(self):
        suite = FullEvaluationSuite(verbose=False)
        result = suite.run_all_levels()
        assert isinstance(result, FullEvalResult)
        assert result.total_levels == NUM_LEVELS

    def test_get_environment_scores(self):
        suite = FullEvaluationSuite()
        suite.run_all_levels()
        scores = suite.get_environment_scores()
        assert len(scores) == NUM_ENVIRONMENTS

    def test_get_overall_score(self):
        suite = FullEvaluationSuite()
        suite.run_all_levels()
        score = suite.get_overall_score()
        assert 0 <= score <= 1

    def test_get_level_report(self):
        suite = FullEvaluationSuite()
        suite.run_all_levels()
        report = suite.get_level_report("env_000", "level_0000")
        assert isinstance(report, dict)

    def test_get_state(self):
        suite = FullEvaluationSuite()
        state = suite.get_state()
        assert "total_levels" in state

    def test_constants(self):
        assert NUM_ENVIRONMENTS == 25
        assert NUM_LEVELS == 183


class TestMockEnvironment:
    def test_create(self):
        from benchmark.arc_agi_3_full_eval import _MockEnvironment
        env = _MockEnvironment("env_test")
        assert env.env_id == "env_test"

    def test_reset(self):
        from benchmark.arc_agi_3_full_eval import _MockEnvironment
        env = _MockEnvironment("env_test")
        obs = env.reset()
        assert obs is not None

    def test_step(self):
        from benchmark.arc_agi_3_full_eval import _MockEnvironment
        env = _MockEnvironment("env_test")
        result = env.step("action")
        assert result is not None
