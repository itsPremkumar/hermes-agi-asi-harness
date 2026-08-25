"""Tests for src/reflexion_eval/evaluator.py."""
from __future__ import annotations

import pytest

from reflexion_eval.evaluator import (
    Rubric,
    Score,
    build_eval_prompt,
    parse_score_response,
)


# ---------------------------------------------------------------------------
# Rubric
# ---------------------------------------------------------------------------
class TestRubric:
    def test_render_contains_name_and_criteria(self):
        r = Rubric(
            name="Accuracy",
            criteria=[("value", "must be 42")],
            pass_threshold=0.8,
        )
        rendered = r.render()
        assert "Accuracy" in rendered
        assert "value" in rendered
        assert "must be 42" in rendered
        assert "0.8" in rendered

    def test_render_multiple_criteria(self):
        r = Rubric(
            name="Test",
            criteria=[
                ("a", "desc a"),
                ("b", "desc b"),
            ],
        )
        rendered = r.render()
        assert "desc a" in rendered
        assert "desc b" in rendered

    def test_default_pass_threshold(self):
        r = Rubric(name="T", criteria=[("c", "d")])
        assert r.pass_threshold == 0.75


# ---------------------------------------------------------------------------
# build_eval_prompt
# ---------------------------------------------------------------------------
class TestBuildEvalPrompt:
    def test_prompt_contains_task_and_attempt(self):
        rubric = Rubric(name="T", criteria=[("c", "d")])
        prompt = build_eval_prompt("do X", "result Y", rubric)
        assert "do X" in prompt
        assert "result Y" in prompt

    def test_prompt_includes_rubric(self):
        rubric = Rubric(name="MyRubric", criteria=[("crit", "desc")])
        prompt = build_eval_prompt("task", "attempt", rubric)
        assert "MyRubric" in prompt
        assert "crit" in prompt

    def test_prompt_includes_output_format(self):
        rubric = Rubric(name="T", criteria=[("c", "d")])
        prompt = build_eval_prompt("task", "attempt", rubric)
        assert "FINAL SCORE" in prompt
        assert "FEEDBACK" in prompt
        assert "REFLECTION" in prompt

    def test_prompt_with_memory_context(self):
        rubric = Rubric(name="T", criteria=[("c", "d")])
        prompt = build_eval_prompt("task", "attempt", rubric, memory_context="prior reflection")
        assert "PRIOR REFLECTIONS" in prompt
        assert "prior reflection" in prompt

    def test_prompt_without_memory_context(self):
        rubric = Rubric(name="T", criteria=[("c", "d")])
        prompt = build_eval_prompt("task", "attempt", rubric)
        assert "PRIOR REFLECTIONS" not in prompt


# ---------------------------------------------------------------------------
# parse_score_response
# ---------------------------------------------------------------------------
class TestParseScoreResponse:
    def test_parses_well_formed_response(self):
        rubric = Rubric(name="T", criteria=[("c", "d")], pass_threshold=0.5)
        resp = "FINAL SCORE: 0.8\nFEEDBACK: Good job.\nREFLECTION: Be better."
        score = parse_score_response(resp, rubric)
        assert score.score == 0.8
        assert score.passed is True
        assert "Good job" in score.feedback
        assert score.raw == resp

    def test_score_below_threshold(self):
        rubric = Rubric(name="T", criteria=[("c", "d")], pass_threshold=0.8)
        resp = "FINAL SCORE: 0.7\nFEEDBACK: Missing something.\nREFLECTION: Fix it."
        score = parse_score_response(resp, rubric)
        assert score.score == 0.7
        assert score.passed is False

    def test_score_clamped_high(self):
        rubric = Rubric(name="T", criteria=[("c", "d")])
        resp = "FINAL SCORE: 1.5\nFEEDBACK: wow\nREFLECTION: ok"
        score = parse_score_response(resp, rubric)
        assert score.score == 1.0

    def test_score_clamped_low(self):
        rubric = Rubric(name="T", criteria=[("c", "d")])
        resp = "FINAL SCORE: -0.5\nFEEDBACK: wow\nREFLECTION: ok"
        score = parse_score_response(resp, rubric)
        assert score.score == 0.0
        assert score.passed is False

    def test_parses_x_over_1_format(self):
        rubric = Rubric(name="T", criteria=[("c", "d")], pass_threshold=0.5)
        resp = "FINAL SCORE: 4/1\nFEEDBACK: great\nREFLECTION: ok"
        score = parse_score_response(resp, rubric)
        assert score.score == 1.0

    def test_parses_0_over_1_format(self):
        rubric = Rubric(name="T", criteria=[("c", "d")], pass_threshold=0.5)
        resp = "FINAL SCORE: 0/1\nFEEDBACK: poor\nREFLECTION: ok"
        score = parse_score_response(resp, rubric)
        assert score.score == 0.0
        assert score.passed is False

    def test_malformed_falls_back_to_zero(self):
        rubric = Rubric(name="T", criteria=[("c", "d")], pass_threshold=0.5)
        resp = "This response has no score at all."
        score = parse_score_response(resp, rubric)
        assert score.score == 0.0
        assert score.passed is False

    def test_extra_whitespace_tolerated(self):
        rubric = Rubric(name="T", criteria=[("c", "d")], pass_threshold=0.5)
        resp = "FINAL    SCORE:  0.9\nFEEDBACK:   Good.\nREFLECTION:   Fine."
        score = parse_score_response(resp, rubric)
        assert score.score == 0.9
        assert "Good" in score.feedback

    def test_feedback_extraction_without_reflection(self):
        rubric = Rubric(name="T", criteria=[("c", "d")])
        resp = "FINAL SCORE: 0.6\nFEEDBACK: Needs work."
        score = parse_score_response(resp, rubric)
        assert "Needs work" in score.feedback

    def test_raw_preserved(self):
        rubric = Rubric(name="T", criteria=[("c", "d")])
        resp = "FINAL SCORE: 0.9\nFEEDBACK: great\nREFLECTION: ok"
        score = parse_score_response(resp, rubric)
        assert score.raw == resp

    def test_exactly_at_threshold_passes(self):
        rubric = Rubric(name="T", criteria=[("c", "d")], pass_threshold=0.75)
        resp = "FINAL SCORE: 0.75\nFEEDBACK: ok\nREFLECTION: ok"
        score = parse_score_response(resp, rubric)
        assert score.passed is True

    def test_fallback_float_extraction(self):
        rubric = Rubric(name="T", criteria=[("c", "d")], pass_threshold=0.5)
        # The fallback regex looks for a standalone decimal like 0.85
        resp = "The attempt scored 0.85 overall."
        score = parse_score_response(resp, rubric)
        assert score.score == 0.85
