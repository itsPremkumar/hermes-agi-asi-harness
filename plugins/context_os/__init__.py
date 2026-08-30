"""
Context OS Plugin — Unified Context Construction System

Builds comprehensive mission context from user, mission, memory, world,
beliefs, available tools/agents, environment, constraints, history.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


@dataclass
class MissionContext:
    user: dict[str, Any] = field(default_factory=dict)
    mission: dict[str, Any] = field(default_factory=dict)
    previous_missions: list[dict[str, Any]] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    world_state: dict[str, Any] = field(default_factory=dict)
    beliefs: dict[str, Any] = field(default_factory=dict)
    available_tools: list[str] = field(default_factory=list)
    available_agents: list[str] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    historical_failures: list[dict[str, Any]] = field(default_factory=list)
    historical_successes: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "mission": self.mission,
            "previous_missions_count": len(self.previous_missions),
            "memory_keys": list(self.memory.keys()),
            "world_entities": len(self.world_state.get("entities", [])),
            "beliefs_count": len(self.beliefs),
            "available_tools": self.available_tools,
            "available_agents": self.available_agents,
            "constraints": self.constraints,
            "timestamp": self.timestamp,
        }

    def summary(self) -> str:
        parts = [
            f"Mission: {self.mission.get('objective', 'N/A')}",
            f"Tools: {len(self.available_tools)}",
            f"Agents: {len(self.available_agents)}",
            f"World entities: {len(self.world_state.get('entities', []))}",
            f"Beliefs: {len(self.beliefs)}",
        ]
        return " | ".join(parts)


class ContextBuilder:
    """Builds MissionContext from all available subsystems."""

    def __init__(self, kernel=None):
        self.kernel = kernel

    async def build(self, mission: dict[str, Any]) -> MissionContext:
        """Construct full context for a mission."""
        ctx = MissionContext()
        ctx.mission = mission

        # Add user info
        ctx.user = {"source": "cli", "timestamp": time.time()}

        # Add available tools from kernel
        if self.kernel and hasattr(self.kernel, 'execution_engine') and self.kernel.execution_engine:
            ee = self.kernel.execution_engine
            ctx.available_tools = list(ee.tools.keys()) if hasattr(ee, 'tools') else []

        # Add available agents
        ctx.available_agents = [
            "researcher", "planner", "coder", "tester",
            "reviewer", "analyzer", "critic", "executor"
        ]

        # Add world state from world_model plugin
        if self.kernel and hasattr(self.kernel, 'world_model') and self.kernel.world_model:
            try:
                wm = self.kernel.world_model
                ctx.world_state = wm.get_world_summary() if hasattr(wm, 'get_world_summary') else {}
            except Exception:
                ctx.world_state = {}

        # Add memory context
        if self.kernel and hasattr(self.kernel, 'memory_system') and self.kernel.memory_system:
            mem = self.kernel.memory_system
            ctx.memory = {"status": "available"}
            if hasattr(mem, 'get_stats'):
                ctx.memory.update(mem.get_stats())

        # Add environment info
        ctx.environment = {
            "python_version": "3.11",
            "platform": "windows",
            "hermes_version": "2.0",
        }

        # Add constraints
        ctx.constraints = mission.get("constraints", {})

        return ctx


class ContextOSPlugin:
    def __init__(self):
        self.builder = None
        self._contexts: dict[str, MissionContext] = {}

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {"status": "healthy", "contexts_built": len(self._contexts)}

    def set_kernel(self, kernel):
        self.builder = ContextBuilder(kernel)

    async def build_context(self, mission: dict[str, Any]) -> MissionContext:
        if self.builder is None:
            self.builder = ContextBuilder()
        ctx = await self.builder.build(mission)
        if "id" in mission:
            self._contexts[mission["id"]] = ctx
        return ctx

    def get_context(self, mission_id: str) -> MissionContext | None:
        return self._contexts.get(mission_id)


async def create(kernel=None):
    plugin = ContextOSPlugin()
    if kernel:
        plugin.set_kernel(kernel)
    return plugin
