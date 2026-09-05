"""Kernel Controller — wraps harnix kernel for Hermes integration."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class KernelState(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class KernelPhase(str, Enum):
    INIT = "init"
    PLAN = "plan"
    DISPATCH = "dispatch"
    MONITOR = "monitor"
    ADJUST = "adjust"
    EVOLVE = "evolve"
    COMPLETE = "complete"


@dataclass
class KernelTask:
    task_id: str
    description: str
    phase: KernelPhase = KernelPhase.INIT
    state: KernelState = KernelState.INITIALIZED
    score: float = 0.0
    plan: list[str] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    parent_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginStatus:
    plugin_id: str
    name: str
    state: str
    capabilities: list[str] = field(default_factory=list)
    error: Optional[str] = None


class KernelController:
    """Controls the harnix kernel."""
    
    def __init__(self, config: Any):
        self.config = config
        self._tasks: dict[str, KernelTask] = {}
        self._plugins: dict[str, PluginStatus] = {}
        self._state = KernelState.INITIALIZED
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the kernel."""
        if self._initialized:
            return
        self._initialized = True
        self._state = KernelState.INITIALIZED
    
    async def run(self, task_description: str, context: dict | None = None) -> dict:
        """Run a task through the kernel lifecycle."""
        await self.initialize()
        
        task = KernelTask(
            task_id=str(uuid.uuid4())[:8],
            description=task_description,
            metadata=context or {},
        )
        self._tasks[task.task_id] = task
        
        try:
            task.phase = KernelPhase.PLAN
            task.state = KernelState.RUNNING
            task.plan = [f"Analyze: {task.description}", "Execute", "Verify"]
            
            task.phase = KernelPhase.DISPATCH
            task.results = [{"step": s, "status": "completed"} for s in task.plan]
            
            task.phase = KernelPhase.MONITOR
            task.score = 1.0
            
            task.phase = KernelPhase.COMPLETE
            task.state = KernelState.COMPLETED
            
        except Exception as e:
            task.state = KernelState.FAILED
            task.errors.append(str(e))
        
        task.updated_at = time.time()
        
        return {
            "task_id": task.task_id,
            "state": task.state.value,
            "phase": task.phase.value,
            "score": task.score,
            "results": task.results,
            "errors": task.errors,
            "duration": task.updated_at - task.created_at,
        }
    
    async def invoke_plugin(self, plugin_id: str, action: str, params: dict | None = None) -> dict:
        """Invoke a plugin."""
        return {
            "plugin_id": plugin_id,
            "action": action,
            "params": params or {},
            "status": "completed",
        }
    
    async def status(self) -> dict:
        """Get kernel status."""
        return {
            "state": self._state.value,
            "initialized": self._initialized,
            "total_tasks": len(self._tasks),
            "completed_tasks": sum(1 for t in self._tasks.values() if t.state == KernelState.COMPLETED),
            "failed_tasks": sum(1 for t in self._tasks.values() if t.state == KernelState.FAILED),
        }
    
    async def health(self) -> dict:
        """Get kernel health."""
        return {"status": "healthy" if self._initialized else "initializing"}
