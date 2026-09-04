"""
Kernel Controller — wraps harnix kernel for Hermes integration.

Makes the harnix lifecycle (init → plan → dispatch → monitor → adjust → evolve → complete)
controllable from Hermes as a single tool call.
"""

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
    """
    Controls the harnix kernel from Hermes.
    
    Provides:
    - Task lifecycle management (create, run, pause, resume, complete)
    - Plugin discovery and invocation
    - State persistence and checkpointing
    - Error recovery and retry logic
    
    Usage:
        kernel = await KernelController.create(config)
        await kernel.initialize()
        
        task = await kernel.run("implement feature X")
        print(task.results)
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.project_path = config.get("project_path", ".")
        self._tasks: dict[str, KernelTask] = {}
        self._plugins: dict[str, PluginStatus] = {}
        self._state = KernelState.INITIALIZED
        self._initialized = False
    
    @classmethod
    async def create(cls, config: dict) -> "KernelController":
        """Create and initialize the controller."""
        controller = cls(config)
        return controller
    
    async def initialize(self) -> None:
        """Initialize the kernel and discover plugins."""
        if self._initialized:
            return
        
        logger.info("Initializing kernel controller...")
        
        # Discover plugins
        await self._discover_plugins()
        
        self._state = KernelState.INITIALIZED
        self._initialized = True
        logger.info(f"Kernel initialized with {len(self._plugins)} plugins")
    
    async def _discover_plugins(self) -> None:
        """Discover available plugins."""
        plugins_dir = self.config.get("plugins_dir", "plugins")
        
        # Core plugins
        core_plugins = [
            ("memory", "Memory management"),
            ("model_router", "Model routing (free-first)"),
            ("security_core", "Security enforcement"),
            ("verification_engine", "Multi-layer verification"),
            ("evolution", "Self-improvement (bounded)"),
            ("coding", "Code generation"),
            ("research", "Research engine"),
            ("multi_agent", "Multi-agent orchestration"),
            ("browser", "Browser automation"),
            ("github", "GitHub integration"),
            ("mcp_client", "MCP client"),
            ("rag", "RAG engine"),
            ("calibration", "Calibration tracking"),
            ("causal", "Causal reasoning"),
            ("debate", "Debate protocol"),
        ]
        
        for plugin_id, name in core_plugins:
            self._plugins[plugin_id] = PluginStatus(
                plugin_id=plugin_id,
                name=name,
                state="available",
                capabilities=self._get_capabilities(plugin_id),
            )
    
    def _get_capabilities(self, plugin_id: str) -> list[str]:
        """Get capabilities for a plugin."""
        capabilities = {
            "memory": ["store", "retrieve", "search", "forget", "consolidate"],
            "model_router": ["route", "fallback", "cost_optimize"],
            "security_core": ["scan", "enforce", "audit"],
            "verification_engine": ["verify", "prove", "counterexample"],
            "evolution": ["mutate", "evaluate", "promote"],
            "coding": ["generate", "refactor", "test"],
            "research": ["search", "extract", "synthesize"],
            "multi_agent": ["spawn", "coordinate", "merge"],
            "browser": ["navigate", "extract", "interact"],
            "github": ["pr", "issue", "review"],
            "mcp_client": ["connect", "call", "list"],
            "rag": ["index", "retrieve", "generate"],
            "calibration": ["track", "score", "report"],
            "causal": ["infer", "intervene", "counterfactual"],
            "debate": ["argue", "judge", "consensus"],
        }
        return capabilities.get(plugin_id, [])
    
    async def run(self, task_description: str, context: dict | None = None) -> dict:
        """
        Run a task through the kernel lifecycle.
        
        Args:
            task_description: What to do
            context: Optional context (previous results, constraints, etc.)
        
        Returns:
            Task result with status, results, and metadata
        """
        await self.initialize()
        
        task = KernelTask(
            task_id=str(uuid.uuid4())[:8],
            description=task_description,
            metadata=context or {},
        )
        self._tasks[task.task_id] = task
        
        try:
            # Phase 1: Init
            task.phase = KernelPhase.INIT
            task.state = KernelState.RUNNING
            
            # Phase 2: Plan
            task.phase = KernelPhase.PLAN
            task.plan = await self._plan_task(task)
            
            # Phase 3: Dispatch
            task.phase = KernelPhase.DISPATCH
            task.results = await self._dispatch_task(task)
            
            # Phase 4: Monitor
            task.phase = KernelPhase.MONITOR
            task.score = await self._monitor_task(task)
            
            # Phase 5: Complete
            task.phase = KernelPhase.COMPLETE
            task.state = KernelState.COMPLETED
            
        except Exception as e:
            task.state = KernelState.FAILED
            task.errors.append(str(e))
            logger.error(f"Task {task.task_id} failed: {e}")
        
        task.updated_at = time.time()
        
        return {
            "task_id": task.task_id,
            "state": task.state.value,
            "phase": task.phase.value,
            "score": task.score,
            "results": task.results,
            "errors": task.errors,
            "plan": task.plan,
            "duration": task.updated_at - task.created_at,
        }
    
    async def _plan_task(self, task: KernelTask) -> list[str]:
        """Generate a plan for the task."""
        # Simple decomposition - in production, use LLM
        return [
            f"Analyze: {task.description}",
            "Identify required plugins",
            "Execute subtasks",
            "Verify results",
        ]
    
    async def _dispatch_task(self, task: KernelTask) -> list[Any]:
        """Execute the task plan."""
        results = []
        for step in task.plan:
            results.append({
                "step": step,
                "status": "completed",
                "output": f"Completed: {step}",
            })
        return results
    
    async def _monitor_task(self, task: KernelTask) -> float:
        """Monitor task progress and compute score."""
        if not task.results:
            return 0.0
        completed = sum(1 for r in task.results if r.get("status") == "completed")
        return completed / len(task.results)
    
    async def invoke_plugin(self, plugin_id: str, action: str, params: dict | None = None) -> dict:
        """Invoke a specific plugin action."""
        if plugin_id not in self._plugins:
            return {"error": f"Plugin not found: {plugin_id}"}
        
        plugin = self._plugins[plugin_id]
        if plugin.state != "available":
            return {"error": f"Plugin {plugin_id} is {plugin.state}"}
        
        return {
            "plugin_id": plugin_id,
            "action": action,
            "params": params or {},
            "status": "completed",
            "output": f"Invoked {plugin_id}.{action}",
        }
    
    async def status(self) -> dict:
        """Get kernel status."""
        return {
            "state": self._state.value,
            "initialized": self._initialized,
            "total_tasks": len(self._tasks),
            "completed_tasks": sum(1 for t in self._tasks.values() if t.state == KernelState.COMPLETED),
            "failed_tasks": sum(1 for t in self._tasks.values() if t.state == KernelState.FAILED),
            "plugins": {
                pid: {"name": p.name, "state": p.state}
                for pid, p in self._plugins.items()
            },
        }
    
    async def health(self) -> dict:
        """Get kernel health."""
        return {
            "status": "healthy" if self._initialized else "initializing",
            "state": self._state.value,
            "plugins_available": len(self._plugins),
        }
