"""
t_d1aa22b4 — Score Aggregator

Weighted score aggregation across all benchmarks, 0-100 scale.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BenchmarkScore:
    benchmark: str
    category: str
    score: float  # 0-100
    num_problems: int
    num_correct: int
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScoreReport:
    id: str
    overall_score: float
    category_scores: dict[str, float]
    benchmark_scores: dict[str, float]
    improvements: list[str]
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "overall_score": self.overall_score,
            "category_scores": self.category_scores,
            "benchmark_scores": self.benchmark_scores,
            "improvements": self.improvements,
            "timestamp": self.timestamp,
        }


class ScoreAggregator:
    """Aggregate scores across multiple benchmarks."""

    def __init__(self) -> None:
        self.scores: list[BenchmarkScore] = []
        self.history: list[ScoreReport] = []

    def add_score(self, score: BenchmarkScore) -> None:
        self.scores.append(score)

    def compute_benchmark_score(self, name: str) -> float:
        for s in self.scores:
            if s.benchmark == name:
                return s.score
        return 0.0

    def compute_category_score(self, category: str) -> float:
        cat_scores = [s for s in self.scores if s.category == category]
        if not cat_scores:
            return 0.0
        total_weight = sum(s.weight for s in cat_scores)
        if total_weight == 0:
            return 0.0
        return sum(s.score * s.weight for s in cat_scores) / total_weight

    def compute_overall_score(self) -> float:
        if not self.scores:
            return 0.0
        total_weight = sum(s.weight for s in self.scores)
        if total_weight == 0:
            return 0.0
        return sum(s.score * s.weight for s in self.scores) / total_weight

    def rank_improvements(self) -> list[str]:
        by_benchmark: dict[str, list[float]] = {}
        for s in self.scores:
            if s.benchmark not in by_benchmark:
                by_benchmark[s.benchmark] = []
            by_benchmark[s.benchmark].append(s.score)
        improvements: list[tuple[str, float]] = []
        for name, scores in by_benchmark.items():
            if len(scores) >= 2:
                improvements.append((name, scores[-1] - scores[-2]))
        improvements.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in improvements]

    def generate_score_report(self) -> ScoreReport:
        cat_scores: dict[str, float] = {}
        for s in self.scores:
            if s.category not in cat_scores:
                cat_scores[s.category] = self.compute_category_score(s.category)
        bench_scores: dict[str, float] = {}
        for s in self.scores:
            bench_scores[s.benchmark] = s.score
        report = ScoreReport(
            id=str(uuid.uuid4().hex[:8]),
            overall_score=self.compute_overall_score(),
            category_scores=cat_scores,
            benchmark_scores=bench_scores,
            improvements=self.rank_improvements(),
            timestamp=__import__("time").time(),
        )
        self.history.append(report)
        return report

    def get_category_breakdown(self) -> dict[str, list[BenchmarkScore]]:
        cats: dict[str, list[BenchmarkScore]] = {}
        for s in self.scores:
            if s.category not in cats:
                cats[s.category] = []
            cats[s.category].append(s)
        return cats
