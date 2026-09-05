"""
Sleep Cycle Plugin — 13-Step Dream Cycle for Memory Consolidation

Steps:
1. Index recent work
2. Identify patterns
3. Cluster similar experiences
4. Extract successful patterns
5. Extract failure patterns
6. Update skill confidence
7. Update belief confidence
8. Prune low-value memories
9. Archive old sessions
10. Consolidate learnings into skills
11. Update curriculum
12. Self-evaluation
13. Plan next cycle
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SleepStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SleepStep:
    step_number: int
    name: str
    description: str
    handler: Callable | None = None
    status: SleepStepStatus = SleepStepStatus.PENDING
    duration_seconds: float = 0.0
    result: Any = None
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class SleepCycle:
    """13-step dream cycle for memory consolidation."""

    def __init__(self):
        self._steps: list[SleepStep] = self._build_default_steps()
        self._last_run: float = 0.0
        self._cycle_count: int = 0
        self._handlers: dict[int, Callable] = {}

    def _build_default_steps(self) -> list[SleepStep]:
        return [
            SleepStep(1, "index_recent_work", "Index all work since last sleep cycle"),
            SleepStep(2, "identify_patterns", "Identify recurring patterns in work"),
            SleepStep(3, "cluster_experiences", "Cluster similar experiences together"),
            SleepStep(4, "extract_success_patterns", "Extract successful execution patterns"),
            SleepStep(5, "extract_failure_patterns", "Extract failure patterns for learning"),
            SleepStep(6, "update_skill_confidence", "Update skill success rates (Bayesian)"),
            SleepStep(7, "update_belief_confidence", "Update belief confidences based on outcomes"),
            SleepStep(8, "prune_low_value_memories", "Prune low-value or redundant memories"),
            SleepStep(9, "archive_old_sessions", "Archive completed sessions to cold storage"),
            SleepStep(10, "consolidate_to_skills", "Consolidate learnings into reusable skills"),
            SleepStep(11, "update_curriculum", "Update learning curriculum priorities"),
            SleepStep(12, "self_evaluation", "Run self-evaluation on past performance"),
            SleepStep(13, "plan_next_cycle", "Plan objectives for next active cycle"),
        ]

    def register_handler(self, step_number: int, handler: Callable):
        """Register a custom handler for a sleep step."""
        if 1 <= step_number <= len(self._steps):
            self._handlers[step_number] = handler
            self._steps[step_number - 1].handler = handler

    async def run_cycle(self, kernel=None) -> dict[str, Any]:
        """Run a full 13-step sleep cycle."""
        self._cycle_count += 1
        cycle_start = time.time()

        for step in self._steps:
            step.started_at = time.time()
            step.status = SleepStepStatus.RUNNING
            step_start = time.time()

            try:
                if step.handler:
                    result = await step.handler(kernel)
                    step.result = result
                else:
                    # Default no-op handler
                    step.result = {"step": step.name, "status": "default"}
                step.status = SleepStepStatus.COMPLETED
            except Exception as e:
                step.status = SleepStepStatus.FAILED
                step.result = {"error": str(e)}

            step.completed_at = time.time()
            step.duration_seconds = step.completed_at - step_start

        self._last_run = time.time()
        return {
            "cycle_number": self._cycle_count,
            "total_duration": time.time() - cycle_start,
            "steps": [s.to_dict() for s in self._steps],
            "all_completed": all(s.status == SleepStepStatus.COMPLETED for s in self._steps),
        }

    def get_progress(self) -> dict[str, Any]:
        completed = sum(1 for s in self._steps if s.status == SleepStepStatus.COMPLETED)
        return {
            "cycle_count": self._cycle_count,
            "last_run": self._last_run,
            "progress": f"{completed}/{len(self._steps)}",
            "percent_complete": completed / len(self._steps) * 100,
        }


class SleepCyclePlugin:
    def __init__(self):
        self.engine = SleepCycle()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "total_steps": len(self.engine._steps),
            "cycles_run": self.engine._cycle_count,
        }


async def create(kernel=None):
    plugin = SleepCyclePlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
