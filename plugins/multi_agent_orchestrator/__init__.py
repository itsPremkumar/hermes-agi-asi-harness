#!/usr/bin/env python3
"""
Multi-Agent Orchestrator Plugin — Task delegation and coordination
=================================================================
Features:
- Spawn and manage sub-agents
- Task queue with priority
- Result aggregation
- Parallel and sequential execution
- Agent pool management
- Timeout and error handling
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_multi_agent_orchestrator")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum as _Enum
    
    class PluginState(str, _Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: List[str] = field(default_factory=list)
        shell_commands: List[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: List[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: List[str] = field(default_factory=list)
        path: Optional[Path] = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentTask:
    """A task for an agent."""
    id: str
    name: str
    func: Callable
    args: Tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    timeout: float = 30.0
    dependencies: List[str] = field(default_factory=list)
    result: Any = None
    error: Optional[str] = None
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class Agent:
    """A single agent worker."""
    
    def __init__(self, agent_id: str, name: str, capabilities: List[str] = None):
        self.agent_id = agent_id
        self.name = name
        self.capabilities = capabilities or []
        self.busy = False
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.last_active = datetime.utcnow().isoformat()


class MultiAgentOrchestrator:
    """Orchestrates multiple agents for task execution."""
    
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, AgentTask] = {}
        self.task_queue: List[str] = []
        self._lock = asyncio.Lock()
        self._running = False
    
    def register_agent(self, name: str, capabilities: List[str] = None) -> str:
        """Register an agent."""
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        self.agents[agent_id] = Agent(agent_id, name, capabilities)
        logger.info(f"Registered agent {name} ({agent_id})")
        return agent_id
    
    def submit_task(
        self,
        name: str,
        func: Callable,
        args: Tuple = (),
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        timeout: float = 30.0,
        dependencies: List[str] = None,
    ) -> str:
        """Submit a task."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = AgentTask(
            id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            timeout=timeout,
            dependencies=dependencies or [],
        )
        self.tasks[task_id] = task
        self.task_queue.append(task_id)
        
        # Sort queue by priority
        priority_order = {TaskPriority.CRITICAL: 0, TaskPriority.HIGH: 1, TaskPriority.MEDIUM: 2, TaskPriority.LOW: 3}
        self.task_queue.sort(key=lambda tid: priority_order.get(self.tasks[tid].priority, 2))
        
        return task_id
    
    async def _execute_task(self, task: AgentTask, agent: Agent):
        """Execute a single task."""
        task.status = "running"
        task.started_at = datetime.utcnow().isoformat()
        agent.busy = True
        agent.last_active = datetime.utcnow().isoformat()
        
        try:
            if asyncio.iscoroutinefunction(task.func):
                result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=task.timeout,
                )
            else:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: task.func(*task.args, **task.kwargs)),
                    timeout=task.timeout,
                )
            
            task.result = result
            task.status = "completed"
            agent.tasks_completed += 1
            
        except asyncio.TimeoutError:
            task.error = f"Task timed out after {task.timeout}s"
            task.status = "failed"
            agent.tasks_failed += 1
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            agent.tasks_failed += 1
        finally:
            task.completed_at = datetime.utcnow().isoformat()
            agent.busy = False
    
    def _dependencies_met(self, task: AgentTask) -> bool:
        """Check if task dependencies are met."""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != "completed":
                return False
        return True
    
    async def run(self) -> Dict[str, Any]:
        """Run the orchestrator until all tasks complete."""
        self._running = True
        start_time = time.time()
        
        completed = 0
        failed = 0
        
        while self._running:
            # Find available agent
            available_agent = None
            for agent in self.agents.values():
                if not agent.busy:
                    available_agent = agent
                    break
            
            if not available_agent:
                # Wait for an agent to free up
                await asyncio.sleep(0.1)
                continue
            
            # Find next runnable task
            runnable_task = None
            for task_id in self.task_queue:
                task = self.tasks[task_id]
                if task.status == "pending" and self._dependencies_met(task):
                    runnable_task = task
                    break
            
            if not runnable_task:
                # Check if all tasks done
                pending = [t for t in self.tasks.values() if t.status in ("pending", "running")]
                if not pending:
                    break
                # Wait for dependencies
                await asyncio.sleep(0.1)
                continue
            
            # Remove from queue and execute
            self.task_queue.remove(runnable_task.id)
            asyncio.create_task(self._execute_task(runnable_task, available_agent))
        
        # Wait for all tasks to complete
        while any(t.status == "running" for t in self.tasks.values()):
            await asyncio.sleep(0.1)
        
        duration = time.time() - start_time
        
        for task in self.tasks.values():
            if task.status == "completed":
                completed += 1
            elif task.status == "failed":
                failed += 1
        
        return {
            "success": True,
            "total_tasks": len(self.tasks),
            "completed": completed,
            "failed": failed,
            "duration": duration,
            "agents": len(self.agents),
        }
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Get task result."""
        task = self.tasks.get(task_id)
        if task:
            return {
                "id": task.id,
                "name": task.name,
                "status": task.status,
                "result": task.result,
                "error": task.error,
            }
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator stats."""
        return {
            "agents": len(self.agents),
            "tasks": len(self.tasks),
            "queue": len(self.task_queue),
            "running": self._running,
        }


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Multi-Agent Orchestrator Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="multi_agent_orchestrator",
            version="1.0.0",
            description="Task delegation, agent pool management, parallel/sequential execution with priority and dependencies",
            license="MIT",
            source="internal",
            capabilities=["task_delegation", "agent_management", "parallel_execution", "result_aggregation"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=30,
            ),
        )
        self.orchestrator: Optional[MultiAgentOrchestrator] = None
    
    async def load(self) -> bool:
        self.orchestrator = MultiAgentOrchestrator()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.orchestrator:
            self.orchestrator = MultiAgentOrchestrator()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> Dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.orchestrator is not None,
            "agents": len(self.orchestrator.agents) if self.orchestrator else 0,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def register_agent(self, name: str, capabilities: List[str] = None) -> str:
        return self.orchestrator.register_agent(name, capabilities)
    
    def submit_task(self, name: str, func: Callable, *args, **kwargs) -> str:
        """Submit a task."""
        priority = kwargs.pop("priority", TaskPriority.MEDIUM)
        timeout = kwargs.pop("timeout", 30.0)
        dependencies = kwargs.pop("dependencies", None)
        return self.orchestrator.submit_task(
            name, func, args, kwargs, priority, timeout, dependencies
        )
    
    async def run(self) -> Dict[str, Any]:
        return await self.orchestrator.run()
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        return self.orchestrator.get_task_result(task_id)
    
    def get_stats(self) -> Dict[str, Any]:
        return self.orchestrator.get_stats()
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
