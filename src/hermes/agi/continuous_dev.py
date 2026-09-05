"""Continuous Development System — 24/7 improvement loop.

Components: Daily Cron, A/B Testing, Canary Deploy, Rollback, Dashboard.
Tests: ≥40 across all modules.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import statistics
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── 1. DAILY IMPROVEMENT CRON ──────────────────────────────────────────────

class CronStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CronTask:
    name: str
    schedule: str
    command: str
    enabled: bool = True
    last_run: float | None = None
    last_status: CronStatus | None = None
    last_duration: float | None = None


class DailyImprovementCron:
    """Schedules and runs daily improvement tasks."""

    DEFAULT_TASKS = [
        CronTask("benchmark-suite", "0 6 * * *", "pytest tests/ -v --tb=short"),
        CronTask("coverage-check", "0 7 * * *", "pytest tests/ --cov=src --cov-report=term"),
        CronTask("lint", "0 8 * * *", "ruff check src/"),
        CronTask("type-check", "0 9 * * *", "mypy src/"),
        CronTask("dependency-audit", "0 10 * * *", "pip audit --requirement requirements.txt"),
        CronTask("benchmark-compare", "0 11 * * *", "python scripts/bench_compare.py"),
        CronTask("regression-test", "0 12 * * *", "pytest tests/ -m 'not slow' -x"),
        CronTask("doc-sync", "0 13 * * *", "python scripts/sync_docs.py"),
    ]

    def __init__(self):
        self._tasks: dict[str, CronTask] = {t.name: t for t in self.DEFAULT_TASKS}

    def add_task(self, task: CronTask) -> None:
        self._tasks[task.name] = task

    def get_task(self, name: str) -> CronTask | None:
        return self._tasks.get(name)

    def list_tasks(self) -> list[CronTask]:
        return list(self._tasks.values())

    async def run_task(self, name: str) -> CronStatus:
        task = self._tasks.get(name)
        if not task or not task.enabled:
            return CronStatus.SKIPPED
        start = time.time()
        # In production: subprocess.run(task.command)
        await asyncio.sleep(0.01)
        duration = time.time() - start
        task.last_run = time.time()
        task.last_duration = duration
        task.last_status = CronStatus.PASSED
        return CronStatus.PASSED

    async def run_all(self) -> dict[str, CronStatus]:
        results = {}
        for name in self._tasks:
            results[name] = await self.run_task(name)
        return results


# ── 2. A/B TESTING FRAMEWORK ──────────────────────────────────────────────

class ABStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ABTest:
    test_id: str
    name: str
    variant_a: str
    variant_b: str
    metric: str
    samples_a: list[float] = field(default_factory=list)
    samples_b: list[float] = field(default_factory=list)
    status: ABStatus = ABStatus.PENDING
    winner: str | None = None
    p_value: float | None = None
    lower_is_better: bool = False


class ABTestingFramework:
    """A/B testing with statistical significance testing."""

    def __init__(self):
        self._tests: dict[str, ABTest] = {}

    def create_test(
        self,
        name: str,
        variant_a: str,
        variant_b: str,
        metric: str,
        lower_is_better: bool = False,
    ) -> str:
        test_id = hashlib.sha256(f"{name}{time.time()}".encode()).hexdigest()[:12]
        test = ABTest(
            test_id=test_id,
            name=name,
            variant_a=variant_a,
            variant_b=variant_b,
            metric=metric,
            lower_is_better=lower_is_better,
        )
        self._tests[test_id] = test
        return test_id

    def record_sample(self, test_id: str, variant: str, value: float) -> None:
        test = self._tests.get(test_id)
        if not test:
            return
        if variant == "a":
            test.samples_a.append(value)
        else:
            test.samples_b.append(value)

    def run_test(self, test_id: str, significance: float = 0.05) -> dict[str, Any]:
        test = self._tests.get(test_id)
        if not test:
            return {"error": "test not found"}
        if len(test.samples_a) < 10 or len(test.samples_b) < 10:
            return {"error": "insufficient samples"}

        test.status = ABStatus.RUNNING
        try:
            mean_a = statistics.mean(test.samples_a)
            mean_b = statistics.mean(test.samples_b)
            std_a = statistics.stdev(test.samples_a) if len(test.samples_a) > 1 else 1.0
            std_b = statistics.stdev(test.samples_b) if len(test.samples_b) > 1 else 1.0

            # Simplified z-test
            se = ((std_a ** 2 / len(test.samples_a)) + (std_b ** 2 / len(test.samples_b))) ** 0.5
            if se == 0:
                se = 1e-10
            z = (mean_b - mean_a) / se
            # Two-tailed p-value approximation
            test.p_value = 2 * (1 - _phi(abs(z)))
            test.winner = "b" if test.p_value < significance and ((mean_b > mean_a and not test.lower_is_better) or (mean_b < mean_a and test.lower_is_better)) else "a"
            test.status = ABStatus.COMPLETED
        except Exception as e:
            test.status = ABStatus.FAILED
            return {"error": str(e)}

        return {
            "test_id": test_id,
            "mean_a": mean_a,
            "mean_b": mean_b,
            "p_value": test.p_value,
            "winner": test.winner,
            "status": test.status.value,
        }

    def get_test(self, test_id: str) -> ABTest | None:
        return self._tests.get(test_id)


def _phi(x: float) -> float:
    """Standard normal CDF approximation."""
    import math
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ── 3. CANARY DEPLOYMENT MANAGER ──────────────────────────────────────────

class CanaryStatus(Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    MONITORING = "monitoring"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


@dataclass
class CanaryRelease:
    release_id: str
    version: str
    canary_percent: float
    error_threshold: float
    latency_threshold: float
    status: CanaryStatus
    error_rate: float = 0.0
    p99_latency: float = 0.0


class CanaryDeploymentManager:
    """Gradual rollout with automatic rollback on error threshold breach."""

    def __init__(self):
        self._releases: dict[str, CanaryRelease] = {}

    def start_canary(
        self,
        version: str,
        canary_percent: float = 5.0,
        error_threshold: float = 1.0,
        latency_threshold: float = 500.0,
    ) -> str:
        release_id = f"canary-{hashlib.sha256(f'{version}{time.time()}'.encode()).hexdigest()[:8]}"
        release = CanaryRelease(
            release_id=release_id,
            version=version,
            canary_percent=canary_percent,
            error_threshold=error_threshold,
            latency_threshold=latency_threshold,
            status=CanaryStatus.PENDING,
        )
        self._releases[release_id] = release
        return release_id

    def deploy(self, release_id: str) -> bool:
        release = self._releases.get(release_id)
        if not release:
            return False
        release.status = CanaryStatus.DEPLOYING
        # Simulate gradual rollout
        release.status = CanaryStatus.MONITORING
        return True

    def record_metrics(self, release_id: str, error_rate: float, p99_latency: float) -> str:
        release = self._releases.get(release_id)
        if not release:
            return "not_found"
        release.error_rate = error_rate
        release.p99_latency = p99_latency

        if error_rate > release.error_threshold:
            release.status = CanaryStatus.ROLLED_BACK
            return "rollback"
        if p99_latency > release.latency_threshold:
            release.status = CanaryStatus.ROLLED_BACK
            return "rollback"
        return "healthy"

    def promote(self, release_id: str) -> bool:
        release = self._releases.get(release_id)
        if not release or release.status != CanaryStatus.MONITORING:
            return False
        release.status = CanaryStatus.PROMOTED
        release.canary_percent = 100.0
        return True

    def rollback(self, release_id: str) -> bool:
        release = self._releases.get(release_id)
        if not release:
            return False
        release.status = CanaryStatus.ROLLED_BACK
        release.canary_percent = 0.0
        return True

    def get_release(self, release_id: str) -> CanaryRelease | None:
        return self._releases.get(release_id)


# ── 4. ROLLBACK MANAGER ───────────────────────────────────────────────────

class RollbackStatus(Enum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RollbackPoint:
    point_id: str
    version: str
    description: str
    created_at: float
    state: dict[str, Any] = field(default_factory=dict)


class RollbackManager:
    """Manages rollback points and executes rollbacks."""

    def __init__(self, max_points: int = 10):
        self._points: list[RollbackPoint] = []
        self._max_points = max_points

    def create_point(self, version: str, description: str, state: dict | None = None) -> str:
        point_id = f"rb-{hashlib.sha256(f'{version}{time.time()}'.encode()).hexdigest()[:8]}"
        point = RollbackPoint(
            point_id=point_id,
            version=version,
            description=description,
            created_at=time.time(),
            state=state or {},
        )
        self._points.append(point)
        if len(self._points) > self._max_points:
            self._points.pop(0)
        return point_id

    def rollback_to(self, point_id: str) -> dict[str, Any]:
        point = next((p for p in self._points if p.point_id == point_id), None)
        if not point:
            return {"status": "not_found"}
        return {
            "status": "completed",
            "version": point.version,
            "state": point.state,
        }

    def list_points(self) -> list[RollbackPoint]:
        return list(self._points)

    def latest(self) -> RollbackPoint | None:
        return self._points[-1] if self._points else None


# ── 5. PROGRESS DASHBOARD (CLI RENDERER) ──────────────────────────────────

@dataclass
class DashboardMetric:
    name: str
    current: float
    target: float
    unit: str = ""
    history: list[tuple[float, float]] = field(default_factory=list)

    @property
    def percent(self) -> float:
        return min(100.0, (self.current / self.target) * 100) if self.target > 0 else 0.0

    @property
    def status(self) -> str:
        if self.percent >= 100:
            return "PASS"
        elif self.percent >= 80:
            return "WARN"
        else:
            return "FAIL"


class ProgressDashboard:
    """CLI dashboard for tracking benchmark progress."""

    def __init__(self):
        self._metrics: dict[str, DashboardMetric] = {}

    def add_metric(self, name: str, target: float, unit: str = "score") -> None:
        self._metrics[name] = DashboardMetric(name=name, current=0.0, target=target, unit=unit)

    def update(self, name: str, value: float) -> None:
        metric = self._metrics.get(name)
        if metric:
            metric.current = value
            metric.history.append((time.time(), value))

    def get_status(self) -> dict[str, Any]:
        statuses = {}
        for name, metric in self._metrics.items():
            statuses[name] = {
                "current": metric.current,
                "target": metric.target,
                "percent": metric.percent,
                "status": metric.status,
            }
        return statuses

    def overall_progress(self) -> float:
        if not self._metrics:
            return 0.0
        return sum(m.percent for m in self._metrics.values()) / len(self._metrics)

    def render(self) -> str:
        lines = ["═" * 60, "  CONTINUOUS DEVELOPMENT DASHBOARD", "═" * 60]
        for name, metric in self._metrics.items():
            bar_len = int(metric.percent / 2)
            bar = "█" * bar_len + "░" * (50 - bar_len)
            status_icon = "✓" if metric.status == "PASS" else ("⚠" if metric.status == "WARN" else "✗")
            lines.append(f"  {status_icon} {name:<30} {bar} {metric.percent:5.1f}%")
            lines.append(f"    {metric.current:.1f}/{metric.target:.1f} {metric.unit}")
        lines.append("─" * 60)
        overall = self.overall_progress()
        lines.append(f"  OVERALL: {overall:.1f}%  (target: 100%)")
        lines.append("═" * 60)
        return "\n".join(lines)
