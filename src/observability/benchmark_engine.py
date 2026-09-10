"""Benchmark Engine — Model comparison and evaluation framework."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkTask:
    """A single benchmark task."""
    task_id: str
    name: str
    description: str = ""
    category: str = "general"
    difficulty: str = "medium"  # easy, medium, hard
    timeout_s: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResult:
    """Result from a single model on a benchmark task."""
    model_id: str
    task_id: str
    output: str = ""
    score: float = 0.0
    latency_ms: float = 0.0
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkScore:
    """Aggregated score for a model across tasks."""
    model_id: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_score: float = 0.0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    task_results: List[ModelResult] = field(default_factory=list)

    @property
    def avg_score(self) -> float:
        return self.total_score / self.completed_tasks if self.completed_tasks > 0 else 0.0

    @property
    def success_rate(self) -> float:
        return self.completed_tasks / self.total_tasks if self.total_tasks > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "avg_score": self.avg_score,
            "total_score": self.total_score,
            "avg_latency_ms": self.avg_latency_ms,
            "total_tokens": self.total_tokens,
            "success_rate": self.success_rate,
        }


class BenchmarkEngine:
    """
    Benchmark framework for model comparison.
    Runs tasks across multiple models and aggregates results.
    """

    def __init__(self):
        self._tasks: Dict[str, BenchmarkTask] = {}
        self._models: Dict[str, Callable] = {}
        self._results: List[ModelResult] = []
        self._scores: Dict[str, BenchmarkScore] = {}

    def register_task(self, task: BenchmarkTask):
        """Register a benchmark task."""
        self._tasks[task.task_id] = task

    def register_model(self, model_id: str, executor: Callable[[BenchmarkTask], ModelResult]):
        """Register a model executor function."""
        self._models[model_id] = executor

    def add_task(
        self,
        task_id: str,
        name: str,
        description: str = "",
        category: str = "general",
        difficulty: str = "medium",
        timeout_s: float = 30.0,
    ) -> BenchmarkTask:
        """Create and register a benchmark task."""
        task = BenchmarkTask(
            task_id=task_id,
            name=name,
            description=description,
            category=category,
            difficulty=difficulty,
            timeout_s=timeout_s,
        )
        self.register_task(task)
        return task

    def run_task(self, task_id: str, model_id: str) -> Optional[ModelResult]:
        """Run a single task against a single model."""
        task = self._tasks.get(task_id)
        executor = self._models.get(model_id)
        if not task or not executor:
            return None

        start = time.time()
        try:
            result = executor(task)
            result.latency_ms = (time.time() - start) * 1000
        except Exception as e:
            result = ModelResult(
                model_id=model_id,
                task_id=task_id,
                success=False,
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )

        self._results.append(result)
        return result

    def run_benchmark(
        self,
        task_ids: Optional[List[str]] = None,
        model_ids: Optional[List[str]] = None,
    ) -> Dict[str, BenchmarkScore]:
        """Run benchmark tasks across models."""
        tasks = task_ids or list(self._tasks.keys())
        models = model_ids or list(self._models.keys())

        for model_id in models:
            score = BenchmarkScore(model_id=model_id, total_tasks=len(tasks))
            for task_id in tasks:
                result = self.run_task(task_id, model_id)
                if result:
                    score.task_results.append(result)
                    if result.success:
                        score.completed_tasks += 1
                        score.total_score += result.score
                        score.total_tokens += result.tokens_used
                    else:
                        score.failed_tasks += 1

            if score.completed_tasks > 0:
                score.avg_latency_ms = sum(
                    r.latency_ms for r in score.task_results if r.success
                ) / score.completed_tasks

            self._scores[model_id] = score

        return dict(self._scores)

    def compare_models(self, model_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Compare models by average score, ranked highest first."""
        ids = model_ids or list(self._scores.keys())
        scores = [self._scores[mid] for mid in ids if mid in self._scores]
        scores.sort(key=lambda s: s.avg_score, reverse=True)
        return [s.to_dict() for s in scores]

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Get the model leaderboard."""
        return self.compare_models()

    def get_task_results(self, task_id: str) -> List[ModelResult]:
        """Get all results for a specific task."""
        return [r for r in self._results if r.task_id == task_id]

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive benchmark report."""
        return {
            "benchmark_id": str(uuid.uuid4())[:8],
            "timestamp": time.time(),
            "total_tasks": len(self._tasks),
            "total_models": len(self._models),
            "total_results": len(self._results),
            "leaderboard": self.get_leaderboard(),
            "scores": {mid: score.to_dict() for mid, score in self._scores.items()},
        }

    def clear_results(self):
        """Clear all results and scores."""
        self._results.clear()
        self._scores.clear()
