"""Benchmark framework for model comparison."""
from __future__ import annotations

import time
import json
import uuid
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol
from pathlib import Path


class Model(Protocol):
    """Protocol for a model that can be benchmarked."""

    def generate(self, prompt: str, **kwargs: Any) -> str:
        ...


@dataclass
class BenchmarkCase:
    """A single benchmark test case."""
    case_id: str
    prompt: str
    expected: str
    category: str = "general"
    difficulty: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark case."""
    case_id: str
    model_name: str
    prompt: str
    output: str
    expected: str
    score: float
    latency: float
    category: str
    difficulty: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "model_name": self.model_name,
            "prompt": self.prompt,
            "output": self.output,
            "expected": self.expected,
            "score": self.score,
            "latency": self.latency,
            "category": self.category,
            "difficulty": self.difficulty,
            "metadata": self.metadata,
        }


@dataclass
class ModelScore:
    """Aggregated score for a model."""
    model_name: str
    total_cases: int
    avg_score: float
    median_score: float
    std_score: float
    avg_latency: float
    min_score: float
    max_score: float
    category_scores: dict[str, float] = field(default_factory=dict)
    difficulty_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "total_cases": self.total_cases,
            "avg_score": self.avg_score,
            "median_score": self.median_score,
            "std_score": self.std_score,
            "avg_latency": self.avg_latency,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "category_scores": self.category_scores,
            "difficulty_scores": self.difficulty_scores,
        }


class Scorer:
    """Score model outputs against expected answers."""

    @staticmethod
    def exact_match(output: str, expected: str) -> float:
        """Exact match scoring."""
        return 1.0 if output.strip() == expected.strip() else 0.0

    @staticmethod
    def contains(output: str, expected: str) -> float:
        """Check if output contains expected answer."""
        return 1.0 if expected.strip().lower() in output.strip().lower() else 0.0

    @staticmethod
    def similarity(output: str, expected: str) -> float:
        """Simple word overlap similarity."""
        output_words = set(output.lower().split())
        expected_words = set(expected.lower().split())
        if not expected_words:
            return 0.0
        overlap = output_words & expected_words
        return len(overlap) / len(expected_words)

    @staticmethod
    def levenshtein_ratio(output: str, expected: str) -> float:
        """Levenshtein distance ratio."""
        if not expected:
            return 1.0 if not output else 0.0

        m, n = len(output), len(expected)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if output[i - 1] == expected[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + cost,
                )

        distance = dp[m][n]
        max_len = max(m, n)
        return 1.0 - (distance / max_len) if max_len > 0 else 1.0


class BenchmarkEngine:
    """Benchmark framework for model comparison."""

    def __init__(self, scorer: Callable[[str, str], float] | None = None) -> None:
        self._cases: dict[str, BenchmarkCase] = {}
        self._models: dict[str, Model] = {}
        self._results: list[BenchmarkResult] = []
        self._scorer = scorer or Scorer.exact_match

    def add_case(self, case: BenchmarkCase) -> None:
        """Add a benchmark case."""
        self._cases[case.case_id] = case

    def add_cases(self, cases: list[BenchmarkCase]) -> None:
        """Add multiple benchmark cases."""
        for case in cases:
            self.add_case(case)

    def register_model(self, name: str, model: Model) -> None:
        """Register a model for benchmarking."""
        self._models[name] = model

    def run_case(self, case_id: str, model_name: str) -> BenchmarkResult:
        """Run a single benchmark case against a model."""
        case = self._cases[case_id]
        model = self._models[model_name]

        start = time.perf_counter()
        output = model.generate(case.prompt)
        latency = time.perf_counter() - start

        score = self._scorer(output, case.expected)

        result = BenchmarkResult(
            case_id=case_id,
            model_name=model_name,
            prompt=case.prompt,
            output=output,
            expected=case.expected,
            score=score,
            latency=latency,
            category=case.category,
            difficulty=case.difficulty,
            metadata=case.metadata,
        )
        self._results.append(result)
        return result

    def run_benchmark(
        self,
        model_name: str,
        case_ids: list[str] | None = None,
    ) -> list[BenchmarkResult]:
        """Run benchmark for a model."""
        if case_ids is None:
            case_ids = list(self._cases.keys())

        results = []
        for case_id in case_ids:
            result = self.run_case(case_id, model_name)
            results.append(result)
        return results

    def run_all_models(self) -> dict[str, list[BenchmarkResult]]:
        """Run benchmark for all registered models."""
        results = {}
        for model_name in self._models:
            results[model_name] = self.run_benchmark(model_name)
        return results

    def get_model_score(self, model_name: str) -> ModelScore | None:
        """Get aggregated score for a model."""
        model_results = [r for r in self._results if r.model_name == model_name]
        if not model_results:
            return None

        scores = [r.score for r in model_results]
        latencies = [r.latency for r in model_results]

        # Category scores
        category_scores: dict[str, list[float]] = {}
        for r in model_results:
            category_scores.setdefault(r.category, []).append(r.score)

        # Difficulty scores
        difficulty_scores: dict[str, list[float]] = {}
        for r in model_results:
            difficulty_scores.setdefault(r.difficulty, []).append(r.score)

        return ModelScore(
            model_name=model_name,
            total_cases=len(model_results),
            avg_score=statistics.mean(scores),
            median_score=statistics.median(scores),
            std_score=statistics.stdev(scores) if len(scores) > 1 else 0.0,
            avg_latency=statistics.mean(latencies),
            min_score=min(scores),
            max_score=max(scores),
            category_scores={k: statistics.mean(v) for k, v in category_scores.items()},
            difficulty_scores={k: statistics.mean(v) for k, v in difficulty_scores.items()},
        )

    def compare_models(self) -> list[ModelScore]:
        """Compare all models and return ranked scores."""
        scores = []
        for model_name in self._models:
            score = self.get_model_score(model_name)
            if score:
                scores.append(score)
        return sorted(scores, key=lambda s: s.avg_score, reverse=True)

    def get_results(self, model_name: str | None = None) -> list[BenchmarkResult]:
        """Get all results, optionally filtered by model."""
        if model_name:
            return [r for r in self._results if r.model_name == model_name]
        return list(self._results)

    def export_results(self, path: str | Path) -> None:
        """Export results to JSON."""
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "models": {name: self.get_model_score(name).to_dict() for name in self._models if self.get_model_score(name)},
            "results": [r.to_dict() for r in self._results],
        }
        Path(path).write_text(json.dumps(data, indent=2))

    def clear_results(self) -> None:
        """Clear all results."""
        self._results.clear()
