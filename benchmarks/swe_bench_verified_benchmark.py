"""
t_40d52c72 — SWE-bench Verified Benchmark

Cleaner, curated subset of SWE-bench with verified test patches.
"""

from __future__ import annotations

import json
import os
import random
import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SWETask:
    instance_id: str
    repo: str
    base_commit: str
    issue_title: str
    issue_description: str
    patch: str
    test_patch: str
    difficulty: str = "medium"
    language: str = "python"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SWETask":
        return cls(**d)


@dataclass
class SWEResult:
    id: str
    instance_id: str
    success: bool
    score: float
    patch_submitted: str = ""
    test_results: dict[str, bool] = field(default_factory=dict)
    duration: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SWEBenchmarkReport:
    id: str
    total_tasks: int
    resolved: int
    unresolved: int
    resolution_rate: float
    results: list[SWESummary] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "total_tasks": self.total_tasks,
            "resolved": self.resolved,
            "unresolved": self.unresolved,
            "resolution_rate": self.resolution_rate,
            "results": [r.to_dict() for r in self.results],
        }


@dataclass
class SWESummary:
    instance_id: str
    repo: str
    success: bool
    score: float
    difficulty: str

    def to_dict(self) -> dict:
        return asdict(self)


class SWEBenchVerifiedLoader:
    """Load SWE-bench Verified tasks."""

    def __init__(self, data_path: str | None = None) -> None:
        self.data_path = data_path
        self.tasks: dict[str, SWETask] = {}

    def load(self, path: str | None = None) -> list[SWETask]:
        target = path or self.data_path
        if not target or not os.path.exists(target):
            return []
        with open(target) as f:
            data = json.load(f)
        tasks = []
        for item in data:
            t = SWETask(
                instance_id=item.get("instance_id", str(uuid.uuid4().hex[:8])),
                repo=item.get("repo", ""),
                base_commit=item.get("base_commit", ""),
                issue_title=item.get("issue_title", ""),
                issue_description=item.get("issue_description", ""),
                patch=item.get("patch", ""),
                test_patch=item.get("test_patch", ""),
                difficulty=item.get("difficulty", "medium"),
                language=item.get("language", "python"),
            )
            self.tasks[t.instance_id] = t
            tasks.append(t)
        return tasks

    def get(self, instance_id: str) -> SWETask | None:
        return self.tasks.get(instance_id)

    def get_all(self) -> list[SWETask]:
        return list(self.tasks.values())

    def get_by_repo(self, repo: str) -> list[SWETask]:
        return [t for t in self.tasks.values() if t.repo == repo]

    def get_by_difficulty(self, difficulty: str) -> list[SWETask]:
        return [t for t in self.tasks.values() if t.difficulty == difficulty]


class SWEBenchVerifiedBenchmark:
    """SWE-bench Verified benchmark runner."""

    VERIFIED_REPOS = [
        "django/django", "sympy/sympy", "matplotlib/matplotlib",
        "scikit-learn/scikit-learn", "pytest-dev/pytest", "sphinx-doc/sphinx",
        "pallets/flask", "psf/requests", "pyca/cryptography",
    ]

    def __init__(self, data_path: str | None = None) -> None:
        self.loader = SWEBenchVerifiedLoader(data_path)
        self.results: list[SWEResult] = []

    def load(self, path: str | None = None) -> list[SWETask]:
        return self.loader.load(path)

    def run(self, instance_id: str, patch: str, test_results: dict[str, bool]) -> SWEResult | None:
        task = self.loader.get(instance_id)
        if not task:
            return None
        passed = sum(1 for v in test_results.values() if v)
        total = len(test_results)
        score = passed / total if total > 0 else 0.0
        result = SWEResult(
            id=str(uuid.uuid4().hex[:8]),
            instance_id=instance_id,
            success=score >= 0.8,
            score=score,
            patch_submitted=patch,
            test_results=test_results,
        )
        self.results.append(result)
        return result

    def run_sample(self, n: int = 10, random_seed: int | None = None) -> list[SWEResult]:
        if random_seed is not None:
            random.seed(random_seed)
        tasks = self.loader.get_all()
        sample = random.sample(tasks, min(n, len(tasks)))
        results = []
        for task in sample:
            # Simulate running with the ground-truth patch
            simulated = {f"test_{i}": True for i in range(3)}
            result = self.run(task.instance_id, task.patch, simulated)
            if result:
                results.append(result)
        return results

    def get_resolution_rate(self) -> float:
        if not self.results:
            return 0.0
        resolved = sum(1 for r in self.results if r.success)
        return resolved / len(self.results)

    def get_report(self) -> SWEBenchmarkReport:
        results = self.results
        resolved = sum(1 for r in results if r.success)
        unresolved = len(results) - resolved
        summaries = []
        for r in results:
            task = self.loader.get(r.instance_id)
            summaries.append(SWESummary(
                instance_id=r.instance_id,
                repo=task.repo if task else "",
                success=r.success,
                score=r.score,
                difficulty=task.difficulty if task else "medium",
            ))
        return SWEBenchmarkReport(
            id=str(uuid.uuid4().hex[:8]),
            total_tasks=len(results),
            resolved=resolved,
            unresolved=unresolved,
            resolution_rate=self.get_resolution_rate(),
            results=summaries,
        )

    def get_results_by_repo(self) -> dict[str, list[SWEResult]]:
        by_repo: dict[str, list[SWEResult]] = {}
        for r in self.results:
            task = self.loader.get(r.instance_id)
            repo = task.repo if task else "unknown"
            if repo not in by_repo:
                by_repo[repo] = []
            by_repo[repo].append(r)
        return by_repo

    def get_results_by_difficulty(self) -> dict[str, list[SWEResult]]:
        by_diff: dict[str, list[SWEResult]] = {}
        for r in self.results:
            task = self.loader.get(r.instance_id)
            diff = task.difficulty if task else "medium"
            if diff not in by_diff:
                by_diff[diff] = []
            by_diff[diff].append(r)
        return by_diff

    def clear_results(self) -> None:
        self.results = []
