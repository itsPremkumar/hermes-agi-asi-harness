"""Tests for FullEvaluationSuite."""
try:
    from benchmarks.arc_agi_3_full_eval import (
        LEVELS_PER_ENVIRONMENT,
        NUM_ENVIRONMENTS,
        NUM_LEVELS,
        FullEvalResult,
        FullEvaluationSuite,
        LevelInfo,
    )
except ImportError:
    from src.benchmark.arc_agi_3_full_eval import (
        LEVELS_PER_ENVIRONMENT,
        NUM_ENVIRONMENTS,
        NUM_LEVELS,
        FullEvalResult,
        FullEvaluationSuite,
        LevelInfo,
    )


class TestFullEvaluationSuite:
    def test_create(self):
        suite = FullEvaluationSuite()
        assert suite._levels == {}
        assert suite._results == {}

    def test_load_all_levels(self):
        suite = FullEvaluationSuite()
        levels = suite.load_all_levels()
        assert len(levels) == NUM_ENVIRONMENTS
        assert sum(len(v) for v in levels.values()) == NUM_LEVELS

    def test_load_all_levels_total(self):
        suite = FullEvaluationSuite()
        levels = suite.load_all_levels()
        total = sum(len(v) for v in levels.values())
        assert total == NUM_LEVELS

    def test_load_all_levels_has_env_000(self):
        suite = FullEvaluationSuite()
        levels = suite.load_all_levels()
        assert "env_000" in levels

    def test_load_all_levels_has_env_024(self):
        suite = FullEvaluationSuite()
        levels = suite.load_all_levels()
        assert "env_024" in levels

    def test_run_level(self):
        suite = FullEvaluationSuite()
        suite.load_all_levels()
        result = suite.run_level("env_000", "level_0000")
        assert result.level_id == "level_0000"
        assert result.actions_used > 0

    def test_run_all_levels(self):
        suite = FullEvaluationSuite()
        result = suite.run_all_levels()
        assert isinstance(result, FullEvalResult)
        assert result.total_levels == NUM_LEVELS
        assert result.completed_levels >= 0

    def test_get_environment_scores(self):
        suite = FullEvaluationSuite()
        suite.load_all_levels()
        scores = suite.get_environment_scores()
        assert len(scores) == NUM_ENVIRONMENTS

    def test_get_overall_score(self):
        suite = FullEvaluationSuite()
        suite.load_all_levels()
        suite.run_level("env_000", "level_0000")
        score = suite.get_overall_score()
        assert isinstance(score, float)

    def test_get_overall_score_empty(self):
        suite = FullEvaluationSuite()
        assert suite.get_overall_score() == 0.0

    def test_get_level_report(self):
        suite = FullEvaluationSuite()
        suite.load_all_levels()
        suite.run_level("env_000", "level_0000")
        report = suite.get_level_report("env_000", "level_0000")
        assert "level_id" in report
        assert report["level_id"] == "level_0000"
        assert "env_id" in report
        assert report["env_id"] == "env_000"
        assert "completed" in report
        assert "score" in report
        assert "actions_used" in report

    def test_get_level_report_not_found(self):
        suite = FullEvaluationSuite()
        suite.load_all_levels()
        report = suite.get_level_report("env_000", "nonexistent")
        assert "error" in report

    def test_get_state(self):
        suite = FullEvaluationSuite()
        state = suite.get_state()
        assert state["total_levels"] == 0
        assert state["environments"] == NUM_ENVIRONMENTS

    def test_get_state_after_load(self):
        suite = FullEvaluationSuite()
        suite.load_all_levels()
        state = suite.get_state()
        assert state["total_levels"] == NUM_LEVELS

    def test_levels_per_environment(self):
        suite = FullEvaluationSuite()
        levels = suite.load_all_levels()
        for env_id, env_levels in levels.items():
            assert len(env_levels) >= LEVELS_PER_ENVIRONMENT - 1

    def test_environment_ids_format(self):
        suite = FullEvaluationSuite()
        levels = suite.load_all_levels()
        for i in range(NUM_ENVIRONMENTS):
            assert f"env_{i:03d}" in levels


class TestFullEvalResult:
    def test_create(self):
        result = FullEvalResult(
            total_levels=183,
            completed_levels=50,
            total_actions=5000,
            overall_score=0.75,
            environment_scores={"env_000": 0.8},
        )
        assert result.total_levels == 183
        assert result.completed_levels == 50
        assert result.overall_score == 0.75


class TestLevelInfo:
    def test_create(self):
        info = LevelInfo(env_id="env_000", level_id="level_0000", index=0)
        assert info.env_id == "env_000"
        assert info.level_id == "level_0000"
        assert info.index == 0
        assert info.completed is False
        assert info.score == 0.0


class TestFullEvalConstants:
    def test_num_environments(self):
        assert NUM_ENVIRONMENTS == 25

    def test_num_levels(self):
        assert NUM_LEVELS == 183

    def test_levels_per_environment(self):
        assert LEVELS_PER_ENVIRONMENT == 7  # 183 // 25

    def test_env_result_has_level_results(self):
        result = FullEvalResult(
            total_levels=183,
            completed_levels=0,
            total_actions=0,
            overall_score=0.0,
            environment_scores={},
            level_results={"level_0000": None},
        )
        assert "level_0000" in result.level_results
