"""Tests for src/reflexion_eval/loop.py."""
from __future__ import annotations

import pytest

from reflexion_eval.evaluator import Rubric
from reflexion_eval.loop import (
    LoopResult,
    Task,
    _extract_answer,
    build_agent_prompt,
    build_reflection_prompt,
    run_reflexion,
)
from reflexion_eval.memory import MemoryStore, Reflection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def simple_task() -> Task:
    return Task(
        id="t_simple",
        description="What is 2+2?",
        rubric=Rubric(
            name="Accuracy",
            criteria=[("value", "must output 4")],
            pass_threshold=0.5,
        ),
        max_iterations=3,
    )


@pytest.fixture
def good_eval_response():
    return (
        "FINAL SCORE: 0.9\n"
        "FEEDBACK: Correct answer.\n"
        "REFLECTION: Nothing to improve."
    )


@pytest.fixture
def bad_eval_response():
    return (
        "FINAL SCORE: 0.2\n"
        "FEEDBACK: Wrong answer.\n"
        "REFLECTION: Need more care."
    )


# ---------------------------------------------------------------------------
# Mock LLMs
# ---------------------------------------------------------------------------
def make_good_agent():
    """Agent that always gives a correct answer."""
    def agent(prompt: str) -> str:
        if "FEEDBACK FROM EVALUATOR" in prompt or "FEEDBACK:" in prompt:
            return "I double-checked my math and it's correct."
        if "ANSWER:" in prompt:
            return "ANSWER:\n4"
        # reflection prompt (contains 'reflection' in lowercase)
        return "I will be more careful."
    return agent


def make_bad_agent():
    """Agent that always gives a wrong answer."""
    def agent(prompt: str) -> str:
        if "FEEDBACK FROM EVALUATOR" in prompt or "FEEDBACK:" in prompt:
            return "I was wrong, I'll try again."
        if "ANSWER:" in prompt:
            return "ANSWER:\n5"
        return "I will be more careful."
    return agent


def make_eval_llm(response: str):
    def eval_llm(prompt: str) -> str:
        return response
    return eval_llm


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------
class TestBuildAgentPrompt:
    def test_prompt_includes_task(self, simple_task):
        prompt = build_agent_prompt(simple_task, "")
        assert "What is 2+2?" in prompt
        assert "ANSWER:" in prompt

    def test_prompt_includes_memory(self, simple_task):
        mem = MemoryStore()
        mem.add(Reflection("t_simple", "4", 0.2, "wrong", "bad math"))
        prompt = build_agent_prompt(simple_task, mem.format_history("t_simple"))
        assert "wrong" in prompt
        assert "bad math" in prompt

    def test_prompt_includes_instructions(self, simple_task):
        prompt = build_agent_prompt(simple_task, "", instructions="Be thorough.")
        assert "Be thorough" in prompt

    def test_default_instructions_when_empty(self, simple_task):
        prompt = build_agent_prompt(simple_task, "")
        assert "Solve the task" in prompt


class TestBuildReflectionPrompt:
    def test_prompt_includes_task_attempt_feedback(self, simple_task):
        prompt = build_reflection_prompt(simple_task, "my answer", "needs work")
        assert "What is 2+2?" in prompt
        assert "my answer" in prompt
        assert "needs work" in prompt

    def test_prompt_ends_with_guidance(self, simple_task):
        prompt = build_reflection_prompt(simple_task, "ans", "fb")
        assert "reflection" in prompt.lower()


# ---------------------------------------------------------------------------
# _extract_answer
# ---------------------------------------------------------------------------
class TestExtractAnswer:
    def test_extracts_after_answer_marker(self):
        raw = "Some preamble. ANSWER:\nThe real answer is 42."
        result = _extract_answer(raw)
        assert "The real answer is 42" in result

    def test_no_marker_returns_stripped(self):
        raw = "  just the answer  "
        result = _extract_answer(raw)
        assert result == "just the answer"

    def test_case_insensitive_marker(self):
        raw = "ANSWER: hello"
        result = _extract_answer(raw)
        assert "hello" in result


# ---------------------------------------------------------------------------
# run_reflexion
# ---------------------------------------------------------------------------
class TestRunReflexion:
    def test_agent_passes_on_first_attempt(self, simple_task, good_eval_response):
        result = run_reflexion(simple_task, make_good_agent(), make_eval_llm(good_eval_response))
        assert result.passed is True
        assert result.iterations == 1
        assert result.final_score == 0.9
        assert len(result.attempts) == 1

    def test_agent_never_passes(self, simple_task, bad_eval_response):
        result = run_reflexion(simple_task, make_bad_agent(), make_eval_llm(bad_eval_response))
        assert result.passed is False
        assert result.iterations == simple_task.max_iterations
        assert len(result.attempts) == 3

    def test_short_circuits_on_pass(self, simple_task, good_eval_response):
        """Loop should stop after first passing attempt."""
        result = run_reflexion(simple_task, make_good_agent(), make_eval_llm(good_eval_response))
        assert result.iterations == 1
        assert result.passed is True

    def test_memory_populated_after_run(self, simple_task, bad_eval_response):
        mem = MemoryStore()
        result = run_reflexion(
            simple_task, make_bad_agent(), make_eval_llm(bad_eval_response), memory=mem
        )
        stored = mem.get("t_simple")
        assert len(stored) == result.iterations
        for r in stored:
            assert r.task_id == "t_simple"
            assert "Wrong" in r.feedback
            assert r.reflection != ""

    def test_memory_empty_initially(self, simple_task, good_eval_response):
        mem = MemoryStore()
        assert len(mem) == 0
        run_reflexion(simple_task, make_good_agent(), make_eval_llm(good_eval_response), memory=mem)
        assert len(mem) == 1

    def test_final_score_is_best(self, simple_task):
        """final_score should reflect the highest score across attempts."""

        def agent(prompt: str) -> str:
            if "ANSWER:" in prompt:
                return "ANSWER:\n4"
            return "reflection text"

        def eval_llm(prompt: str) -> str:
            if "prior" in prompt.lower() or "Prior" in prompt:
                # second attempt has memory context → higher score
                return "FINAL SCORE: 0.9\nFEEDBACK: Good.\nREFLECTION: ok"
            # first attempt, no memory → below threshold
            return "FINAL SCORE: 0.3\nFEEDBACK: Needs work.\nREFLECTION: ok"

        result = run_reflexion(simple_task, agent, eval_llm)
        assert result.final_score == 0.9
        assert result.iterations == 2
        assert result.passed is True

    def test_passes_second_attempt_with_memory(self, simple_task):
        """On attempt 2, memory context should be injected and can change outcome."""

        call_count = {"n": 0}

        def agent(prompt: str) -> str:
            if "ANSWER:" in prompt:
                call_count["n"] += 1
                if call_count["n"] == 1:
                    return "ANSWER:\n5"
                return "ANSWER:\n4"
            if "FEEDBACK FROM EVALUATOR" in prompt:
                return "I corrected my math."
            return "reflection"

        def eval_llm(prompt: str) -> str:
            if call_count["n"] == 1:
                return "FINAL SCORE: 0.2\nFEEDBACK: Wrong, should be 4.\nREFLECTION: fix"
            return "FINAL SCORE: 0.9\nFEEDBACK: Correct.\nREFLECTION: good"

        result = run_reflexion(simple_task, agent, eval_llm, max_iterations=None)
        assert result.passed is True
        assert result.iterations == 2
        assert result.attempts[0][1].score == 0.2
        assert result.attempts[1][1].score == 0.9

    def test_max_iterations_respected(self, simple_task, bad_eval_response):
        """Even if not passed, loop runs exactly max_iterations times."""
        result = run_reflexion(
            simple_task, make_bad_agent(), make_eval_llm(bad_eval_response)
        )
        assert result.iterations == simple_task.max_iterations

    def test_custom_memory_object_used(self, simple_task, good_eval_response):
        """Passing an existing MemoryStore should append, not replace."""
        mem = MemoryStore()
        mem.add(Reflection("t_simple", "seed", 0.1, "old fb", "old refl"))
        run_reflexion(simple_task, make_good_agent(), make_eval_llm(good_eval_response), memory=mem)
        assert len(mem) == 2

    def test_reflection_text_stored(self, simple_task, good_eval_response):
        """The reflection generated should be stored in memory."""
        mem = MemoryStore()

        def agent(prompt: str) -> str:
            if "FEEDBACK FROM EVALUATOR" in prompt:
                return "I will improve by being more careful."
            if "ANSWER:" in prompt:
                return "ANSWER:\n4"
            return "reflection"

        run_reflexion(simple_task, agent, make_eval_llm(good_eval_response), memory=mem)
        stored = mem.get("t_simple")
        assert "improve" in stored[0].reflection.lower()
