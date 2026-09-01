"""Tests for arc_agi_3_full_eval.py — ARC-AGI-3 Full Evaluation."""
import pytest

from benchmark.arc_agi_3_full_eval import (
    ARCLevel, ARCResult, LevelReport, ARCAGI3FullEval,
)


class TestARCLevel:
    def test_create(self):
        level = ARCLevel(
            level_id="test_0", name="Test", environment="pattern_recognition",
            difficulty="easy", input_shape=(3, 3), output_shape=(3, 3), num_examples=2,
        )
        assert level.level_id == "test_0"
        assert level.environment == "pattern_recognition"

    def test_to_dict(self):
        level = ARCLevel(
            level_id="test_0", name="Test", environment="logic",
            difficulty="hard", input_shape=(5, 5), output_shape=(5, 5), num_examples=4,
        )
        d = level.to_dict()
        assert d["level_id"] == "test_0"
        assert d["environment"] == "logic"


class TestARCResult:
    def test_create(self):
        r = ARCResult(id="r1", level_id="l1", environment="math", success=True, score=0.95)
        assert r.success is True
        assert r.score == 0.95

    def test_to_dict(self):
        r = ARCResult(id="r1", level_id="l1", environment="math", success=True, score=0.95)
        d = r.to_dict()
        assert d["success"] is True


class TestLevelReport:
    def test_create(self):
        report = LevelReport(
            level_id="l1", name="Test", environment="math",
            difficulty="easy", score=0.9, attempts=1, solved=True,
        )
        assert report.solved is True
        assert report.score == 0.9

    def test_to_dict(self):
        report = LevelReport(
            level_id="l1", name="Test", environment="math",
            difficulty="easy", score=0.9, attempts=1, solved=True,
        )
        d = report.to_dict()
        assert d["solved"] is True


class TestARCAGI3FullEval:
    def test_create(self):
        eval = ARCAGI3FullEval()
        assert len(eval.levels) == 0
        assert len(eval.results) == 0

    def test_load_all_levels(self):
        eval = ARCAGI3FullEval()
        count = eval.load_all_levels()
        assert count > 0
        assert len(eval.levels) > 0

    def test_load_all_levels_count(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        # Should have levels across 25 environments
        envs = set(l.environment for l in eval.levels.values())
        assert len(envs) == 25

    def test_run_level(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        level_id = list(eval.levels.keys())[0]
        result = eval.run_level(level_id)
        assert result is not None
        assert result.level_id == level_id

    def test_run_level_missing(self):
        eval = ARCAGI3FullEval()
        assert eval.run_level("nonexistent") is None

    def test_run_all_levels(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        results = eval.run_all_levels()
        assert len(results) == len(eval.levels)

    def test_get_environment_scores(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        eval.run_all_levels()
        scores = eval.get_environment_scores()
        assert len(scores) == 25
        for env, data in scores.items():
            assert "average_score" in data
            assert "total" in data
            assert "solved" in data
            assert "solve_rate" in data

    def test_get_overall_score(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        eval.run_all_levels()
        overall = eval.get_overall_score()
        assert "overall" in overall
        assert "total_levels" in overall
        assert "solved" in overall
        assert "solve_rate" in overall

    def test_get_level_report(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        level_id = list(eval.levels.keys())[0]
        eval.run_level(level_id)
        report = eval.get_level_report(level_id)
        assert report is not None
        assert report.level_id == level_id

    def test_get_level_report_missing(self):
        eval = ARCAGI3FullEval()
        assert eval.get_level_report("nonexistent") is None

    def test_get_difficulty_breakdown(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        eval.run_all_levels()
        breakdown = eval.get_difficulty_breakdown()
        assert "easy" in breakdown
        assert "medium" in breakdown
        assert "hard" in breakdown
        assert "expert" in breakdown

    def test_get_unsolved_levels(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        eval.run_all_levels()
        unsolved = eval.get_unsolved_levels()
        assert isinstance(unsolved, list)

    def test_get_solved_levels(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        eval.run_all_levels()
        solved = eval.get_solved_levels()
        assert isinstance(solved, list)

    def test_clear_results(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        eval.run_all_levels()
        eval.clear_results()
        assert len(eval.results) == 0
        assert len(eval.level_results) == 0

    def test_get_levels_by_environment(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        levels = eval.get_levels_by_environment("pattern_recognition")
        assert len(levels) > 0
        assert all(l.environment == "pattern_recognition" for l in levels)

    def test_get_levels_by_difficulty(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        levels = eval.get_levels_by_difficulty("easy")
        assert len(levels) > 0
        assert all(l.difficulty == "easy" for l in levels)

    def test_overall_score_range(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        eval.run_all_levels()
        overall = eval.get_overall_score()
        assert 0 <= overall["overall"] <= 1

    def test_environment_scores_range(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        eval.run_all_levels()
        scores = eval.get_environment_scores()
        for env, data in scores.items():
            assert 0 <= data["average_score"] <= 1
            assert 0 <= data["solve_rate"] <= 1

    def test_run_level_with_solver(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        level_id = list(eval.levels.keys())[0]
        result = eval.run_level(level_id, solver=lambda x: x)
        assert result is not None

    def test_level_constraints(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        for level in eval.levels.values():
            assert "max_colors" in level.constraints
            assert "time_limit" in level.constraints

    def test_level_shapes(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        for level in eval.levels.values():
            assert level.input_shape[0] > 0
            assert level.input_shape[1] > 0

    def test_results_accumulate(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        level_id = list(eval.levels.keys())[0]
        eval.run_level(level_id)
        eval.run_level(level_id)
        assert len(eval.results) == 2

    def test_level_report_after_multiple_runs(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        level_id = list(eval.levels.keys())[0]
        eval.run_level(level_id)
        eval.run_level(level_id)
        report = eval.get_level_report(level_id)
        assert report.attempts == 2

    def test_empty_overall_score(self):
        eval = ARCAGI3FullEval()
        overall = eval.get_overall_score()
        assert overall["overall"] == 0.0

    def test_empty_environment_scores(self):
        eval = ARCAGI3FullEval()
        scores = eval.get_environment_scores()
        assert scores == {}

    def test_all_environments_present(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        envs = set(l.environment for l in eval.levels.values())
        assert len(envs) == 25
        for env in ARCAGI3FullEval.ENVIRONMENTS:
            assert env in envs

    def test_difficulty_breakdown_totals(self):
        eval = ARCAGI3FullEval()
        eval.load_all_levels()
        eval.run_all_levels()
        breakdown = eval.get_difficulty_breakdown()
        total = sum(d["total"] for d in breakdown.values())
        assert total == len(eval.levels)
