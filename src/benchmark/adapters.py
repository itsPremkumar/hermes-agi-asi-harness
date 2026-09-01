"""
t_da531cb1 — Benchmark Adapters

Unified adapter layer for all benchmarks:
HumanEval, MBPP, MMLU, GSM8K.
Each adapter: load, run, get_pass_rate.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


class BenchmarkAdapter(Protocol):
    """Protocol all benchmark adapters implement."""

    def load(self, path: str | None = None) -> int: ...
    def run(self, task_id: str, solution: str) -> BenchmarkTaskResult | None: ...
    def get_pass_rate(self) -> dict[str, float]: ...


@dataclass
class TaskResult:
    id: str
    task_id: str
    benchmark: str
    success: bool
    score: float
    output: Any = None
    error: str | None = None


# ─── HumanEval Adapter ───────────────────────────────────────────────────────

@dataclass
class HumanEvalTask:
    task_id: str
    description: str
    code: str
    test_cases: list[str]
    difficulty: str = "medium"
    tags: list[str] = field(default_factory=list)


class HumanEvalAdapter:
    """Adapter for HumanEval coding benchmark."""

    def __init__(self) -> None:
        self.tasks: dict[str, HumanEvalTask] = {}
        self.results: list[TaskResult] = []

    def load(self, path: str | None = None) -> int:
        if not path or not os.path.exists(path):
            return 0
        with open(path) as f:
            data = json.load(f)
        count = 0
        for item in data:
            t = HumanEvalTask(
                task_id=item.get("task_id", str(uuid.uuid4().hex[:8])),
                description=item.get("description", ""),
                code=item.get("code", ""),
                test_cases=item.get("test_cases", []),
                difficulty=item.get("difficulty", "medium"),
                tags=item.get("tags", []),
            )
            self.tasks[t.task_id] = t
            count += 1
        return count

    def run(self, task_id: str, solution: str) -> TaskResult | None:
        task = self.tasks.get(task_id)
        if not task:
            return None
        results = {}
        error = None
        for test in task.test_cases:
            try:
                namespace: dict[str, Any] = {}
                exec(solution, namespace)
                exec(test, namespace)
                results[test] = True
            except Exception as e:
                results[test] = False
                if error is None:
                    error = str(e)
        total = len(results)
        passed = sum(1 for v in results.values() if v)
        score = passed / total if total > 0 else 0.0
        result = TaskResult(
            id=str(uuid.uuid4().hex[:8]),
            task_id=task_id,
            benchmark="humaneval",
            success=score >= 0.8,
            score=score,
            output=results,
            error=error,
        )
        self.results.append(result)
        return result

    def get_pass_rate(self) -> dict[str, float]:
        if not self.results:
            return {"pass_rate": 0.0, "total": 0}
        passed = sum(1 for r in self.results if r.success)
        return {"pass_rate": passed / len(self.results), "total": len(self.results)}

    def get_all_tasks(self) -> list[HumanEvalTask]:
        return list(self.tasks.values())


# ─── MBPP Adapter ─────────────────────────────────────────────────────────────

@dataclass
class MBPPTask:
    task_id: str
    description: str
    code: str
    test_cases: list[str]
    difficulty: str = "medium"
    tags: list[str] = field(default_factory=list)


class MBPPAdapter:
    """Adapter for MBPP (Mostly Basic Python Problems) benchmark."""

    def __init__(self) -> None:
        self.tasks: dict[str, MBPPTask] = {}
        self.results: list[TaskResult] = []

    def load(self, path: str | None = None) -> int:
        if not path or not os.path.exists(path):
            return 0
        with open(path) as f:
            data = json.load(f)
        count = 0
        for item in data:
            t = MBPPTask(
                task_id=item.get("task_id", str(uuid.uuid4().hex[:8])),
                description=item.get("description", ""),
                code=item.get("code", ""),
                test_cases=item.get("test_cases", []),
                difficulty=item.get("difficulty", "medium"),
                tags=item.get("tags", []),
            )
            self.tasks[t.task_id] = t
            count += 1
        return count

    def run(self, task_id: str, solution: str) -> TaskResult | None:
        task = self.tasks.get(task_id)
        if not task:
            return None
        results = {}
        error = None
        for test in task.test_cases:
            try:
                namespace: dict[str, Any] = {}
                exec(solution, namespace)
                exec(test, namespace)
                results[test] = True
            except Exception as e:
                results[test] = False
                if error is None:
                    error = str(e)
        total = len(results)
        passed = sum(1 for v in results.values() if v)
        score = passed / total if total > 0 else 0.0
        result = TaskResult(
            id=str(uuid.uuid4().hex[:8]),
            task_id=task_id,
            benchmark="mbpp",
            success=score >= 0.8,
            score=score,
            output=results,
            error=error,
        )
        self.results.append(result)
        return result

    def get_pass_rate(self) -> dict[str, float]:
        if not self.results:
            return {"pass_rate": 0.0, "total": 0}
        passed = sum(1 for r in self.results if r.success)
        return {"pass_rate": passed / len(self.results), "total": len(self.results)}

    def get_all_tasks(self) -> list[MBPPTask]:
        return list(self.tasks.values())


# ─── MMLU Adapter ─────────────────────────────────────────────────────────────

@dataclass
class MMLUTask:
    task_id: str
    question: str
    subject: str
    choices: list[str]
    answer: int
    difficulty: str = "medium"


class MMLUAdapter:
    """Adapter for MMLU (Massive Multitask Language Understanding) benchmark."""

    def __init__(self) -> None:
        self.tasks: dict[str, MMLUTask] = {}
        self.results: list[TaskResult] = []

    def load(self, path: str | None = None) -> int:
        if not path or not os.path.exists(path):
            return 0
        with open(path) as f:
            data = json.load(f)
        count = 0
        for item in data:
            t = MMLUTask(
                task_id=item.get("task_id", str(uuid.uuid4().hex[:8])),
                question=item.get("question", ""),
                subject=item.get("subject", "unknown"),
                choices=item.get("choices", []),
                answer=int(item.get("answer", 0)),
                difficulty=item.get("difficulty", "medium"),
            )
            self.tasks[t.task_id] = t
            count += 1
        return count

    def run(self, task_id: str, predicted: int) -> TaskResult | None:
        task = self.tasks.get(task_id)
        if not task:
            return None
        correct = predicted == task.answer
        result = TaskResult(
            id=str(uuid.uuid4().hex[:8]),
            task_id=task_id,
            benchmark="mmlu",
            success=correct,
            score=1.0 if correct else 0.0,
        )
        self.results.append(result)
        return result

    def get_pass_rate(self) -> dict[str, float]:
        if not self.results:
            return {"pass_rate": 0.0, "total": 0}
        passed = sum(1 for r in self.results if r.success)
        return {"pass_rate": passed / len(self.results), "total": len(self.results)}

    def get_subject_pass_rate(self, subject: str) -> dict[str, float]:
        results = [r for r in self.results if self.tasks.get(r.task_id, MMLUTask("", "", "", [], 0)).subject == subject]
        if not results:
            return {"pass_rate": 0.0, "total": 0}
        passed = sum(1 for r in results if r.success)
        return {"pass_rate": passed / len(results), "total": len(results)}

    def get_all_tasks(self) -> list[MMLUTask]:
        return list(self.tasks.values())


# ─── GSM8K Adapter ────────────────────────────────────────────────────────────

@dataclass
class GSM8KTask:
    task_id: str
    question: str
    answer: float
    steps: list[str] = field(default_factory=list)


class GSM8KAdapter:
    """Adapter for GSM8K (Grade School Math 8K) benchmark."""

    def __init__(self, tolerance: float = 1e-6) -> None:
        self.tasks: dict[str, GSM8KTask] = {}
        self.results: list[TaskResult] = []
        self.tolerance = tolerance

    def load(self, path: str | None = None) -> int:
        if not path or not os.path.exists(path):
            return 0
        with open(path) as f:
            data = json.load(f)
        count = 0
        for item in data:
            t = GSM8KTask(
                task_id=item.get("task_id", str(uuid.uuid4().hex[:8])),
                question=item.get("question", ""),
                answer=float(item.get("answer", 0)),
                steps=item.get("steps", []),
            )
            self.tasks[t.task_id] = t
            count += 1
        return count

    def run(self, task_id: str, response: str) -> TaskResult | None:
        task = self.tasks.get(task_id)
        if not task:
            return None
        predicted = self._extract_number(response)
        if predicted is None:
            result = TaskResult(
                id=str(uuid.uuid4().hex[:8]),
                task_id=task_id,
                benchmark="gsm8k",
                success=False,
                score=0.0,
                error="No number found in response",
            )
        else:
            correct = abs(predicted - task.answer) < self.tolerance
            result = TaskResult(
                id=str(uuid.uuid4().hex[:8]),
                task_id=task_id,
                benchmark="gsm8k",
                success=correct,
                score=1.0 if correct else 0.0,
                output={"predicted": predicted, "actual": task.answer},
            )
        self.results.append(result)
        return result

    def _extract_number(self, text: str) -> float | None:
        numbers = re.findall(r"[-+]?\d*\.?\d+", text)
        if numbers:
            return float(numbers[-1])
        return None

    def get_pass_rate(self) -> dict[str, float]:
        if not self.results:
            return {"pass_rate": 0.0, "total": 0}
        passed = sum(1 for r in self.results if r.success)
        return {"pass_rate": passed / len(self.results), "total": len(self.results)}

    def get_all_tasks(self) -> list[GSM8KTask]:
        return list(self.tasks.values())


# ─── Unified Benchmark Manager ────────────────────────────────────────────────

class BenchmarkManager:
    """Unified interface for running all benchmark adapters."""

    def __init__(self) -> None:
        self.adapters: dict[str, BenchmarkAdapter] = {}

    def register(self, name: str, adapter: BenchmarkAdapter) -> None:
        self.adapters[name] = adapter

    def load(self, name: str, path: str) -> int:
        if name not in self.adapters:
            return 0
        return self.adapters[name].load(path)

    def run(self, name: str, task_id: str, solution: str) -> TaskResult | None:
        if name not in self.adapters:
            return None
        return self.adapters[name].run(task_id, solution)

    def get_pass_rate(self, name: str) -> dict[str, float]:
        if name not in self.adapters:
            return {"pass_rate": 0.0, "total": 0}
        return self.adapters[name].get_pass_rate()

    def get_all_pass_rates(self) -> dict[str, dict[str, float]]:
        return {name: adapter.get_pass_rate() for name, adapter in self.adapters.items()}

    def get_adapter(self, name: str) -> BenchmarkAdapter | None:
        return self.adapters.get(name)
