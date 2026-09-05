"""Daily Improvement Scheduler — Multi-level feedback queue for continuous improvement tasks."""
from __future__ import annotations

import asyncio
import heapq
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class ImprovementTask:
    task_id: str
    name: str
    priority: TaskPriority
    quantum: float = 1.0
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    run_count: int = 0
    total_runtime: float = 0.0
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: ImprovementTask) -> bool:
        return self.priority.value < other.priority.value


class DailyImprovementScheduler:
    """Multi-level feedback queue scheduler for daily improvement tasks."""

    NUM_QUEUES = 5
    BOOST_INTERVAL = 300.0  # seconds between priority boosts

    def __init__(self):
        self._queues: list[list[ImprovementTask]] = [[] for _ in range(self.NUM_QUEUES)]
        self._tasks: dict[str, ImprovementTask] = {}
        self._current: ImprovementTask | None = None
        self._last_boost = time.time()
        self._completed: list[ImprovementTask] = []
        self._failed: list[ImprovementTask] = []

    def add_task(
        self,
        name: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        quantum: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        task_id = f"task-{len(self._tasks)}"
        task = ImprovementTask(
            task_id=task_id,
            name=name,
            priority=priority,
            quantum=quantum,
            metadata=metadata or {},
        )
        self._tasks[task_id] = task
        heapq.heappush(self._queues[priority.value], task)
        return task_id

    def get_next(self) -> ImprovementTask | None:
        self._boost_if_needed()
        for queue in self._queues:
            if queue:
                task = heapq.heappop(queue)
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                self._current = task
                return task
        return None

    def complete(self, task: ImprovementTask) -> None:
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        if task.started_at:
            task.total_runtime += time.time() - task.started_at
        task.run_count += 1
        self._completed.append(task)
        if self._current == task:
            self._current = None

    def fail(self, task: ImprovementTask, error: str) -> None:
        task.status = TaskStatus.FAILED
        task.last_error = error
        task.completed_at = time.time()
        if task.started_at:
            task.total_runtime += time.time() - task.started_at
        self._failed.append(task)
        if self._current == task:
            self._current = None

    def demote(self, task: ImprovementTask) -> None:
        """Demote task to lower priority queue."""
        new_priority = min(task.priority.value + 1, self.NUM_QUEUES - 1)
        task.priority = TaskPriority(new_priority)
        task.status = TaskStatus.PENDING
        heapq.heappush(self._queues[new_priority], task)
        if self._current == task:
            self._current = None

    def promote(self, task: ImprovementTask) -> None:
        """Promote task to higher priority queue."""
        new_priority = max(task.priority.value - 1, 0)
        task.priority = TaskPriority(new_priority)
        task.status = TaskStatus.PENDING
        heapq.heappush(self._queues[new_priority], task)

    def _boost_if_needed(self) -> None:
        """Periodically boost all tasks to prevent starvation."""
        now = time.time()
        if now - self._last_boost >= self.BOOST_INTERVAL:
            self._boost_all()
            self._last_boost = now

    def _boost_all(self) -> None:
        """Boost all pending tasks to highest priority."""
        for priority_level in range(1, self.NUM_QUEUES):
            while self._queues[priority_level]:
                task = heapq.heappop(self._queues[priority_level])
                task.priority = TaskPriority.CRITICAL
                heapq.heappush(self._queues[0], task)

    def get_stats(self) -> dict[str, Any]:
        pending = sum(len(q) for q in self._queues)
        return {
            "pending": pending,
            "running": 1 if self._current else 0,
            "completed": len(self._completed),
            "failed": len(self._failed),
            "total": len(self._tasks),
        }

    def get_task(self, task_id: str) -> ImprovementTask | None:
        return self._tasks.get(task_id)

    def list_pending(self) -> list[ImprovementTask]:
        return [t for q in self._queues for t in q]

    def list_completed(self) -> list[ImprovementTask]:
        return list(self._completed)

    def list_failed(self) -> list[ImprovementTask]:
        return list(self._failed)

    def clear_completed(self) -> None:
        self._completed.clear()

    def clear_failed(self) -> None:
        self._failed.clear()


class DailyImprovementLoop:
    """24/7 improvement loop with daily scheduling."""

    def __init__(self, scheduler: DailyImprovementScheduler):
        self.scheduler = scheduler
        self._running = False

    def add_daily_task(
        self,
        name: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        quantum: float = 1.0,
    ) -> str:
        return self.scheduler.add_task(name, priority, quantum)

    def run_once(self) -> list[dict[str, Any]]:
        results = []
        while True:
            task = self.scheduler.get_next()
            if not task:
                break
            try:
                # In production: execute the actual task
                time.sleep(0.001)
                self.scheduler.complete(task)
                results.append({"task": task.name, "status": "completed"})
            except Exception as e:
                self.scheduler.fail(task, str(e))
                results.append({"task": task.name, "status": "failed", "error": str(e)})
        return results

    async def run_continuous(self, interval: float = 3600.0) -> None:
        self._running = True
        while self._running:
            self.run_once()
            await asyncio.sleep(interval)

    def stop(self) -> None:
        self._running = False
