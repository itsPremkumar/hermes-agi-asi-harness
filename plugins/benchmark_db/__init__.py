"""
Benchmark DB Plugin — Performance Tracking & Trend Analysis

Records: benchmark runs, scores, timestamps, configurations, environments.
Tracks: score trends, regression detection, performance distribution.
"""

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkRun:
    run_id: str
    benchmark_name: str
    score: float
    max_score: float = 1.0
    duration_seconds: float = 0.0
    configuration: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def normalized_score(self) -> float:
        return self.score / self.max_score if self.max_score > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "benchmark_name": self.benchmark_name,
            "score": self.score,
            "max_score": self.max_score,
            "normalized_score": self.normalized_score,
            "duration_seconds": self.duration_seconds,
            "configuration": self.configuration,
            "environment": self.environment,
            "notes": self.notes,
            "timestamp": self.timestamp,
        }


class BenchmarkDB:
    """Performance benchmark database."""

    def __init__(self, storage_path: Path | None = None):
        self._runs: list[BenchmarkRun] = []
        self._storage_path = storage_path
        if storage_path and storage_path.exists():
            self._load()

    def _load(self):
        try:
            with open(self._storage_path, "r") as f:
                data = json.load(f)
                for r in data.get("runs", []):
                    self._runs.append(BenchmarkRun(**r))
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    def _save(self):
        if not self._storage_path:
            return
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "w") as f:
                json.dump(
                    {"runs": [r.to_dict() for r in self._runs[-1000:]]},
                    f, indent=2
                )
        except Exception:
            pass

    def record_run(self, benchmark_name: str, score: float,
                   max_score: float = 1.0, duration_seconds: float = 0.0,
                   configuration: dict[str, Any] | None = None,
                   environment: dict[str, Any] | None = None,
                   notes: str = "") -> BenchmarkRun:
        import uuid
        run = BenchmarkRun(
            run_id=f"RUN-{uuid.uuid4().hex[:8]}",
            benchmark_name=benchmark_name,
            score=score,
            max_score=max_score,
            duration_seconds=duration_seconds,
            configuration=configuration or {},
            environment=environment or {},
            notes=notes,
        )
        self._runs.append(run)
        self._save()
        return run

    def get_trend(self, benchmark_name: str, limit: int = 10) -> list[float]:
        """Get recent score trend for a benchmark."""
        runs = [r for r in self._runs if r.benchmark_name == benchmark_name]
        return [r.normalized_score for r in runs[-limit:]]

    def detect_regression(self, benchmark_name: str,
                          threshold: float = 0.1) -> dict[str, Any] | None:
        """Detect if recent score has regressed."""
        runs = [r for r in self._runs if r.benchmark_name == benchmark_name]
        if len(runs) < 3:
            return None
        recent_avg = sum(r.normalized_score for r in runs[-3:]) / 3
        baseline_avg = sum(r.normalized_score for r in runs[:-3][-10:]) / max(1, min(10, len(runs) - 3))
        if recent_avg < baseline_avg - threshold:
            return {
                "benchmark": benchmark_name,
                "recent_avg": recent_avg,
                "baseline_avg": baseline_avg,
                "delta": recent_avg - baseline_avg,
                "regression_detected": True,
            }
        return None

    def get_leaderboard(self) -> list[dict[str, Any]]:
        """Get top benchmarks by best score."""
        best_by_name: dict[str, BenchmarkRun] = {}
        for run in self._runs:
            current = best_by_name.get(run.benchmark_name)
            if not current or run.normalized_score > current.normalized_score:
                best_by_name[run.benchmark_name] = run
        return [
            {"benchmark": name, "best_score": run.normalized_score, "run_id": run.run_id}
            for name, run in sorted(best_by_name.items(), key=lambda x: -x[1].normalized_score)
        ]

    def get_stats(self) -> dict[str, Any]:
        by_name: dict[str, list[BenchmarkRun]] = defaultdict(list)
        for run in self._runs:
            by_name[run.benchmark_name].append(run)
        return {
            "total_runs": len(self._runs),
            "unique_benchmarks": len(by_name),
            "avg_score": sum(r.normalized_score for r in self._runs) / max(1, len(self._runs)),
            "leaderboard": self.get_leaderboard()[:5],
        }


class BenchmarkDBPlugin:
    def __init__(self, storage_path: Path | None = None):
        self.engine = BenchmarkDB(storage_path=storage_path)

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "stats": self.engine.get_stats(),
        }


async def create(kernel=None):
    plugin = BenchmarkDBPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
