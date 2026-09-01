"""
Executive Agent — Coordinates all benchmark solving across the harness.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentTask:
    id: str
    benchmark: str
    task_type: str
    priority: int = 0
    status: str = "pending"
    result: Any = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def complete(self, result: Any) -> None:
        self.result = result
        self.status = "completed"
        self.completed_at = time.time()

    def fail(self, error: str) -> None:
        self.result = {"error": error}
        self.status = "failed"
        self.completed_at = time.time()


@dataclass
class AgentPlan:
    id: str
    tasks: list[AgentTask]
    strategy: str = "parallel"
    created_at: float = field(default_factory=time.time)

    @property
    def completed(self) -> int:
        return sum(1 for t in self.tasks if t.status == "completed")

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tasks if t.status == "failed")

    @property
    def pending(self) -> int:
        return sum(1 for t in self.tasks if t.status == "pending")

    @property
    def total(self) -> int:
        return len(self.tasks)

    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0
        return (self.completed + self.failed) / len(self.tasks)


class ExecutiveAgent:
    """Coordinates benchmark solving across all registered benchmarks."""

    def __init__(self) -> None:
        self.benchmarks: dict[str, Any] = {}
        self.plans: list[AgentPlan] = []
        self.results: dict[str, Any] = {}

    def register_benchmark(self, name: str, benchmark: Any) -> None:
        self.benchmarks[name] = benchmark

    def get_benchmark(self, name: str) -> Any:
        return self.benchmarks.get(name)

    def list_benchmarks(self) -> list[str]:
        return list(self.benchmarks.keys())

    def create_plan(self, benchmark_names: list[str] | None = None, strategy: str = "parallel") -> AgentPlan:
        if benchmark_names is None:
            benchmark_names = list(self.benchmarks.keys())
        tasks = []
        for name in benchmark_names:
            task = AgentTask(
                id=str(uuid.uuid4().hex[:8]),
                benchmark=name,
                task_type="evaluate",
                priority=0,
            )
            tasks.append(task)
        plan = AgentPlan(id=str(uuid.uuid4().hex[:8]), tasks=tasks, strategy=strategy)
        self.plans.append(plan)
        return plan

    def execute_plan(self, plan_id: str) -> dict[str, Any]:
        plan = self._get_plan(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        results = {}
        for task in plan.tasks:
            benchmark = self.benchmarks.get(task.benchmark)
            if not benchmark:
                task.fail("Benchmark not found")
                results[task.benchmark] = {"error": "Benchmark not found"}
                continue
            try:
                if hasattr(benchmark, 'load_problems'):
                    benchmark.load_problems()
                if hasattr(benchmark, 'run_all'):
                    benchmark.run_all()
                elif hasattr(benchmark, 'run_sample'):
                    benchmark.run_sample()
                if hasattr(benchmark, 'get_pass_rate'):
                    result = benchmark.get_pass_rate()
                elif hasattr(benchmark, 'get_accuracy'):
                    result = benchmark.get_accuracy()
                else:
                    result = {"status": "executed"}
                task.complete(result)
                results[task.benchmark] = result
            except Exception as e:
                task.fail(str(e))
                results[task.benchmark] = {"error": str(e)}
        self.results[plan_id] = results
        return results

    def _get_plan(self, plan_id: str) -> Optional[AgentPlan]:
        for plan in self.plans:
            if plan.id == plan_id:
                return plan
        return None

    def get_plan(self, plan_id: str) -> Optional[AgentPlan]:
        return self._get_plan(plan_id)

    def get_all_plans(self) -> list[AgentPlan]:
        return list(self.plans)

    def get_plan_results(self, plan_id: str) -> dict[str, Any]:
        return self.results.get(plan_id, {})

    def get_overall_progress(self, plan_id: str) -> float:
        plan = self._get_plan(plan_id)
        if not plan:
            return 0.0
        return plan.progress

    def get_plan_summary(self, plan_id: str) -> dict[str, Any]:
        plan = self._get_plan(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        return {
            "plan_id": plan.id,
            "strategy": plan.strategy,
            "total_tasks": plan.total,
            "completed": plan.completed,
            "failed": plan.failed,
            "pending": plan.pending,
            "progress": plan.progress,
        }

    def clear_plans(self) -> None:
        self.plans.clear()
        self.results.clear()
