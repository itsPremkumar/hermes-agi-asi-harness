"""The core Reflexion act → evaluate → reflect → retry loop."""

from __future__ import annotations

import re as _re
from dataclasses import dataclass, field
from typing import Optional, Protocol

from .evaluator import Rubric, Score, build_eval_prompt, parse_score_response
from .memory import MemoryStore, Reflection


class LLM(Protocol):
    """Minimal LLM interface used by the loop.

    An LLM is any callable that takes a string prompt and returns a string.
    Mock implementations in tests replace this with a simple callable.
    """

    def __call__(self, prompt: str) -> str: ...


# ---------------------------------------------------------------------------
# task model
# ---------------------------------------------------------------------------
@dataclass
class Task:
    """A single benchmark task.

    Attributes:
        id: unique task identifier.
        description: the task prompt given to the agent.
        rubric: rubric used to score attempts.
        max_iterations: hard cap on retry attempts.
    """

    id: str
    description: str
    rubric: Rubric
    max_iterations: int = 3

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "rubric": {
                "name": self.rubric.name,
                "criteria": self.rubric.criteria,
                "pass_threshold": self.rubric.pass_threshold,
            },
            "max_iterations": self.max_iterations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        r = data["rubric"]
        return cls(
            id=data["id"],
            description=data["description"],
            rubric=Rubric(
                name=r["name"],
                criteria=[tuple(c) for c in r["criteria"]],
                pass_threshold=r.get("pass_threshold", 0.75),
            ),
            max_iterations=data.get("max_iterations", 3),
        )


# ---------------------------------------------------------------------------
# result model
# ---------------------------------------------------------------------------
@dataclass
class LoopResult:
    """Outcome of running the Reflexion loop on a single task.

    Attributes:
        task_id: the task that was run.
        attempts: list of (attempt_text, Score) pairs in chronological order.
        passed: whether any attempt passed the rubric.
        final_score: the score of the best attempt.
        iterations: number of attempts made.
    """

    task_id: str
    attempts: list[tuple[str, Score]] = field(default_factory=list)
    passed: bool = False
    final_score: float = 0.0
    iterations: int = 0


# ---------------------------------------------------------------------------
# prompt construction helpers
# ---------------------------------------------------------------------------
_ACT_PROMPT = (
    "You are a helpful agent. Solve the following task. "
    "Be thoughtful and precise.\n\n"
    "--- PRIOR REFLECTIONS (use these to improve) ---\n{mem}\n\n"
    "--- TASK ---\n{task}\n\n"
    "--- INSTRUCTIONS ---\n"
    "{instructions}\n\n"
    "Write your answer after the line below.\n"
    "ANSWER:"
)

_REFLECT_PROMPT = (
    "You are introspecting on your previous attempt at a task.\n\n"
    "--- TASK ---\n{task}\n\n"
    "--- YOUR ATTEMPT ---\n{attempt}\n\n"
    "--- FEEDBACK FROM EVALUATOR ---\n{feedback}\n\n"
    "Write a concise reflection (1-3 sentences) explaining what went wrong "
    "and how you will improve on the next attempt."
)

_INSTRUCTIONS_DEFAULT = "Solve the task to the best of your ability."


def build_agent_prompt(task: Task, memory_context: str, instructions: str = "") -> str:
    """Build the prompt sent to the agent LLM on a given iteration."""
    return _ACT_PROMPT.format(
        mem=memory_context or "(no prior reflections)",
        task=task.description.strip(),
        instructions=instructions or _INSTRUCTIONS_DEFAULT,
    )


def build_reflection_prompt(task: Task, attempt: str, feedback: str) -> str:
    """Build the prompt sent to the agent LLM to produce a self-reflection."""
    return _REFLECT_PROMPT.format(
        task=task.description.strip(),
        attempt=attempt.strip(),
        feedback=feedback.strip(),
    )


# ---------------------------------------------------------------------------
# the loop
# ---------------------------------------------------------------------------
def run_reflexion(
    task: Task,
    agent_llm: LLM,
    eval_llm: LLM,
    memory: Optional[MemoryStore] = None,
    instructions: str = "",
    max_iterations: Optional[int] = None,
) -> LoopResult:
    """Execute one full Reflexion loop for *task*.

    Steps per iteration:
      1. **act**: build a prompt (task + episodic memory + feedback) and call the agent LLM.
      2. **evaluate**: build the scoring prompt and call the evaluator LLM, then parse the score.
      3. **reflect**: ask the agent LLM to write a self-reflection on the feedback.
      4. **retry**: store the reflection + loop again (up to ``task.max_iterations``).

    The loop short-circuits as soon as an attempt passes the rubric.
    """
    if memory is None:
        memory = MemoryStore()
    iterations = max_iterations if max_iterations is not None else task.max_iterations
    result = LoopResult(task_id=task.id)
    passed = False

    for iteration in range(iterations):
        # 1. act -----------------------------------------------------------
        mem_context = memory.format_history(task.id, limit=5)
        agent_prompt = build_agent_prompt(task, mem_context, instructions)
        attempt = agent_llm(agent_prompt)
        attempt = _extract_answer(attempt)

        # 2. evaluate ------------------------------------------------------
        eval_prompt = build_eval_prompt(
            task=task.description,
            attempt=attempt,
            rubric=task.rubric,
            memory_context=mem_context,
        )
        eval_response = eval_llm(eval_prompt)
        score = parse_score_response(eval_response, task.rubric)
        result.attempts.append((attempt, score))

        if score.score > result.final_score:
            result.final_score = score.score
        if score.passed:
            passed = True

        # 3. reflect -------------------------------------------------------
        reflect_prompt = build_reflection_prompt(task, attempt, score.feedback)
        reflection_text = agent_llm(reflect_prompt).strip()

        memory.add(
            Reflection(
                task_id=task.id,
                attempt=attempt,
                score=score.score,
                feedback=score.feedback,
                reflection=reflection_text,
            )
        )

        if passed:
            break

    result.passed = passed
    result.iterations = len(result.attempts)
    return result


# ---------------------------------------------------------------------------
# utilities
# ---------------------------------------------------------------------------
_ANSWER_RE = _re.compile(r"ANSWER:\s*(.*)", _re.DOTALL | _re.IGNORECASE)


def _extract_answer(raw: str) -> str:
    """Extract the text following the ``ANSWER:`` marker if present."""
    m = _ANSWER_RE.search(raw)
    if m:
        return m.group(1).strip()
    return raw.strip()
