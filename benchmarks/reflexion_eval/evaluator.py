"""Rubric-based evaluator for Reflexion agents.

The evaluator produces a structured scoring prompt that an LLM can answer to
score an agent's attempt against a rubric, and a parser that extracts the
numeric score + verbal feedback from a (possibly free-form) LLM response.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Rubric:
    """A scoring rubric.

    Attributes:
        name: human-readable rubric name.
        criteria: list of (criterion, description) pairs that the LLM should
            consider.  Each will be rendered as a bullet in the scoring prompt.
        pass_threshold: score >= this value means the attempt passes.
    """

    name: str
    criteria: list[tuple[str, str]]
    pass_threshold: float = 0.75

    def render(self) -> str:
        bullets = []
        for criterion, desc in self.criteria:
            bullets.append(f"  - **{criterion}**: {desc}")
        return (
            f"Rubric: {self.name}\n"
            f"Score each criterion 0-1 then average. "
            f"{chr(10).join(bullets)}\n"
            f"Final score in [0,1]. Pass threshold = {self.pass_threshold}."
        )


@dataclass
class Score:
    """Result of evaluating an attempt.

    Attributes:
        score: normalized score in [0, 1].
        passed: whether ``score >= rubric.pass_threshold``.
        feedback: verbal feedback string.
        raw: the raw evaluator response (for debugging / transparency).
    """

    score: float
    passed: bool
    feedback: str
    raw: str


# ---------------------------------------------------------------------------
# prompt construction
# ---------------------------------------------------------------------------
def build_eval_prompt(
    task: str,
    attempt: str,
    rubric: Rubric,
    *,
    memory_context: str = "",
) -> str:
    """Assemble the structured prompt sent to the evaluator LLM."""
    parts = [
        "You are a meticulous evaluator. Score the attempt below against the rubric.",
        f"--- TASK ---\n{task.strip()}",
        f"--- ATTEMPT ---\n{attempt.strip()}",
        f"--- RUBRIC ---\n{rubric.render()}",
    ]
    if memory_context:
        parts.append(f"--- PRIOR REFLECTIONS ---\n{memory_context.strip()}")
    parts.append(
        "\nOutput format:\n"
        'FINAL SCORE: <number in [0,1]>\n'
        "FEEDBACK: <1-2 sentences of qualitative feedback>\n"
        "REFLECTION: <1 sentence for the agent to use as self-critique>"
    )
    parts.append("Be precise and concise. Start each field on its own line.")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# response parsing
# ---------------------------------------------------------------------------
_SCORE_RE = re.compile(r"FINAL\s+SCORE:\s*(-?[0-9]*\.?[0-9]+)", re.IGNORECASE)
_FEEDBACK_RE = re.compile(
    r"FEEDBACK:\s*(.*?)(?=\nREFLECTION:|\Z)", re.IGNORECASE | re.DOTALL
)
_REFLECTION_RE = re.compile(
    r"REFLECTION:\s*(.*)", re.IGNORECASE | re.DOTALL
)
_ANY_SCORE_RE = re.compile(r"([0-9]*\.?[0-9]+)\s*/\s*1")


def parse_score_response(response: str, rubric: Rubric) -> Score:
    """Parse a (possibly imperfect) evaluator response into a :class:`Score`.

    The parser is intentionally tolerant:
    * looks for an explicit ``FINAL SCORE:`` line first,
    * falls back to ``X / 1`` patterns,
    * clamps the score to [0, 1],
    * defaults to 0.0 if no number is found at all.
    """
    score = _extract_score(response)
    score = max(0.0, min(1.0, score))
    passed = score >= rubric.pass_threshold
    feedback = _extract_feedback(response)
    return Score(score=score, passed=passed, feedback=feedback, raw=response)


def _extract_score(text: str) -> float:
    m = _SCORE_RE.search(text)
    if m:
        return float(m.group(1))
    m = _ANY_SCORE_RE.search(text)
    if m:
        return float(m.group(1))
    # last resort: grab any standalone float in [0,1]
    m = re.search(r"\b0?\.\d+\b", text)
    if m:
        return float(m.group(0))
    return 0.0


def _extract_feedback(text: str) -> str:
    m = _FEEDBACK_RE.search(text)
    if m:
        return m.group(1).strip()
    m = _REFLECTION_RE.search(text)
    if m:
        return m.group(1).strip()
    # if nothing structured, return the whole response trimmed
    return text.strip()[:500]
