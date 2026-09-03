"""Benchmark runner for the Reflexion harness.

Loads a task suite from YAML files and computes pass@k statistics, mirroring
the pass@k metric from the original Reflexion / SWE-bench literature.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence

import yaml

from .loop import Task, run_reflexion
from .memory import MemoryStore


# ---------------------------------------------------------------------------
# pass@k computation
# ---------------------------------------------------------------------------
def pass_at_k(n: int, c: int, k: int) -> float:
    """Compute pass@k given *n* total attempts, *c* correct, for k=1..n.

    Uses the standard unbiased estimator:

        pass@k = 1 - (C(n-c, k) / C(n, k))

    Returns 0.0 when there are fewer than *k* samples (undefined).
    """
    if n < k or k <= 0:
        return 0.0
    if n == c:
        # all correct → pass@k is 1
        return 1.0
    return 1.0 - _comb(n - c, k) / _comb(n, k)


def _comb(n: int, k: int) -> float:
    """Combination count as float (avoids int overflow for large n)."""
    if k < 0 or k > n:
        return 0.0
    if k == 0 or k == n:
        return 1.0
    k = min(k, n - k)
    result = 1.0
    for i in range(k):
        result = result * (n - i) / (i + 1)
    return result


# ---------------------------------------------------------------------------
# benchmark result
# ---------------------------------------------------------------------------
@dataclass
class BenchmarkResult:
    """Aggregated results across a task suite."""

    task_ids: List[str] = field(default_factory=list)
    pass_counts: List[int] = field(default_factory=list)   # number of passing attempts per task
    attempt_counts: List[int] = field(default_factory=list)  # total attempts per task
    pass_k: dict[int, float] = field(default_factory=dict)  # k -> pass@k
    per_task: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "num_tasks": len(self.task_ids),
            "pass_at_k": {str(k): v for k, v in self.pass_k.items()},
            "per_task": self.per_task,
        }


# ---------------------------------------------------------------------------
# suite loading
# ---------------------------------------------------------------------------
def load_suite(suite_dir: str | Path) -> List[Task]:
    """Load all ``*.yaml`` / ``*.yml`` task files from *suite_dir*."""
    path = Path(suite_dir)
    tasks: List[Task] = []
    for ext in ("*.yaml", "*.yml"):
        for fpath in sorted(path.glob(ext)):
            with open(fpath, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if isinstance(data, list):
                for item in data:
                    tasks.append(Task.from_dict(item))
            else:
                tasks.append(Task.from_dict(data))
    return tasks


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
def run_benchmark(
    tasks: Sequence[Task],
    agent_llm: Callable[[str], str],
    eval_llm: Callable[[str], str],
    *,
    k_values: Sequence[int] = (1, 3),
    max_iterations: Optional[int] = None,
    verbose: bool = False,
) -> BenchmarkResult:
    """Run the Reflexion loop over *tasks* and aggregate pass@k results.

    Each task is attempted with up to ``max_iterations`` retries (or the task's
    own ``max_iterations`` if *max_iterations* is None).  A task contributes one
    "pass" if **any** of its attempts passed the rubric.
    """
    result = BenchmarkResult()

    for task in tasks:
        task_obj = task
        if max_iterations is not None:
            task_obj = Task(
                id=task.id,
                description=task.description,
                rubric=task.rubric,
                max_iterations=max_iterations,
            )
        memory = MemoryStore()
        loop_result = run_reflexion(task_obj, agent_llm, eval_llm, memory)

        n = loop_result.iterations
        c = 1 if loop_result.passed else 0
        result.task_ids.append(task.id)
        result.pass_counts.append(c)
        result.attempt_counts.append(n)
        result.per_task[task.id] = {
            "passed": loop_result.passed,
            "final_score": round(loop_result.final_score, 4),
            "iterations": n,
        }
        if verbose:
            status = "PASS" if loop_result.passed else "FAIL"
            print(f"  [{status}] {task.id} — score={loop_result.final_score:.2f} iters={n}")

    # compute pass@k
    total_tasks = len(result.task_ids)
    for k in k_values:
        if k > total_tasks:
            result.pass_k[k] = 0.0
            continue
        total_pass = 0.0
        for pid, n, c in zip(
            result.task_ids, result.attempt_counts, result.pass_counts
        ):
            total_pass += pass_at_k(n, c, k)
        result.pass_k[k] = round(total_pass / total_tasks, 4) if total_tasks else 0.0

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _make_mock_llm(seed: Optional[int] = None) -> Callable[[str], str]:
    """A trivial mock LLM for the CLI smoke-test path.

    In real usage you pass your own LLM callables; this exists so ``python -m
    reflexion_eval.bench`` does not crash without one.
    """
    import random

    rng = random.Random(seed)

    def _llm(prompt: str) -> str:
        # Reflection prompt (contains both "FEEDBACK FROM EVALUATOR" and "reflection")
        if "FEEDBACK FROM EVALUATOR" in prompt:
            return "I should be more careful about the details."
        # Eval prompt (contains "FINAL SCORE" format spec)
        if "SCORE" in prompt.upper():
            score = rng.uniform(0.0, 1.0)
            return (
                f"FINAL SCORE: {score:.2f}\n"
                f"FEEDBACK: Mock feedback on the attempt.\n"
                f"REFLECTION: Needs more precision."
            )
        # agent answer
        return "ANSWER:\nThis is a mock answer generated for smoke testing."

    return _llm


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the reflexion-eval benchmark suite."
    )
    parser.add_argument(
        "--tasks",
        required=True,
        help="Directory containing task YAML files.",
    )
    parser.add_argument(
        "--k",
        default="1,3",
        help="Comma-separated k values for pass@k (default: 1,3).",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Override max iterations per task (default: 3).",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print per-task results."
    )
    parser.add_argument(
        "--output", "-o", default=None, help="Write JSON results to this file."
    )
    args = parser.parse_args(argv)

    k_values = [int(x) for x in args.k.split(",")]
    tasks = load_suite(args.tasks)

    if not tasks:
        print(f"No tasks found in {args.tasks}", file=sys.stderr)
        return 1

    print(f"Loaded {len(tasks)} tasks.")
    agent_llm = _make_mock_llm(seed=42)
    eval_llm = agent_llm

    result = run_benchmark(
        tasks,
        agent_llm,
        eval_llm,
        k_values=k_values,
        max_iterations=args.max_iterations,
        verbose=args.verbose,
    )

    print(f"\npass@k results: {json.dumps(result.pass_k, indent=2)}")
    print(f"Total tasks: {len(result.task_ids)}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(result.to_dict(), fh, indent=2)
        print(f"Results written to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
