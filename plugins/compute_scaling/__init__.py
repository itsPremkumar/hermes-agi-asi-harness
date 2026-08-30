"""
Compute Scaling Controller — Section 32 of v7 spec

Explicit reasoning budget per task class.
Agent count, parallelism, tool calls, context expansion, simulation steps.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ComputeBudget:
    """Compute budget for a task."""
    max_agents: int = 1
    max_parallelism: int = 1
    max_tool_calls: int = 10
    max_context_tokens: int = 4096
    max_simulation_steps: int = 0
    reasoning_level: str = "medium"  # low, medium, high, critical
    timeout_seconds: int = 60


class ComputeScalingController:
    """Scale compute based on task value and difficulty."""

    def __init__(self):
        self._budgets: Dict[str, ComputeBudget] = {}
        self._active_usage: Dict[str, Dict[str, Any]] = {}
        
        # Default budgets per reasoning level
        self._defaults = {
            "low": ComputeBudget(max_agents=1, max_parallelism=1, max_tool_calls=5, reasoning_level="low"),
            "medium": ComputeBudget(max_agents=2, max_parallelism=2, max_tool_calls=15, reasoning_level="medium"),
            "high": ComputeBudget(max_agents=4, max_parallelism=4, max_tool_calls=30, reasoning_level="high"),
            "critical": ComputeBudget(max_agents=8, max_parallelism=8, max_tool_calls=50, reasoning_level="critical"),
        }

    def get_budget(self, task_class: str, difficulty: float = 0.5) -> ComputeBudget:
        """Get compute budget for a task class."""
        if task_class in self._budgets:
            return self._budgets[task_class]
        
        # Determine reasoning level from difficulty
        if difficulty < 0.25:
            level = "low"
        elif difficulty < 0.5:
            level = "medium"
        elif difficulty < 0.75:
            level = "high"
        else:
            level = "critical"
        
        return self._defaults[level]

    def set_budget(self, task_class: str, budget: ComputeBudget):
        """Set a custom budget for a task class."""
        self._budgets[task_class] = budget

    def start_task(self, task_id: str, budget: ComputeBudget):
        """Start tracking compute usage for a task."""
        self._active_usage[task_id] = {
            "agents_used": 0,
            "tool_calls": 0,
            "start_time": time.time(),
            "budget": budget,
        }

    def can_spawn_agent(self, task_id: str) -> bool:
        """Check if a new agent can be spawned."""
        usage = self._active_usage.get(task_id)
        if not usage:
            return False
        return usage["agents_used"] < usage["budget"].max_agents

    def can_call_tool(self, task_id: str) -> bool:
        """Check if more tool calls are allowed."""
        usage = self._active_usage.get(task_id)
        if not usage:
            return False
        return usage["tool_calls"] < usage["budget"].max_tool_calls

    def record_agent_spawn(self, task_id: str):
        """Record an agent spawn."""
        if task_id in self._active_usage:
            self._active_usage[task_id]["agents_used"] += 1

    def record_tool_call(self, task_id: str):
        """Record a tool call."""
        if task_id in self._active_usage:
            self._active_usage[task_id]["tool_calls"] += 1

    def is_within_budget(self, task_id: str) -> bool:
        """Check if task is still within budget."""
        usage = self._active_usage.get(task_id)
        if not usage:
            return True
        elapsed = time.time() - usage["start_time"]
        return (
            usage["agents_used"] <= usage["budget"].max_agents
            and usage["tool_calls"] <= usage["budget"].max_tool_calls
            and elapsed <= usage["budget"].timeout_seconds
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "custom_budgets": len(self._budgets),
            "active_tasks": len(self._active_usage),
        }


class ComputeScalingPlugin:
    def __init__(self):
        self.controller = ComputeScalingController()

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", **self.controller.get_stats()}

    async def get_budget(self, task_class: str, difficulty: float = 0.5):
        return self.controller.get_budget(task_class, difficulty)

    async def can_spawn_agent(self, task_id: str):
        return self.controller.can_spawn_agent(task_id)


async def create(kernel=None):
    plugin = ComputeScalingPlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
