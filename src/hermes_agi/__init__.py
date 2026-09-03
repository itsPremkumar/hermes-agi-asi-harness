"""
Hermes AGI/ASI Harness — Unified AI Agent Runtime.

All capabilities are plugins. The harness is the kernel that manages plugins.
"""

from __future__ import annotations

__version__ = "2.0.0"

from .config import Config, load_config
from .exceptions import HarnessError, KernelError, PluginError, SafetyError, BenchmarkError
from .planning import Planner, plan, get_all_features, get_all_capabilities, search_features, find_by_capability
from .plugins.manager import PluginManager, PluginBase, PluginState, PluginPriority, PluginMetadata
from .plugins.core_plugins import ALL_PLUGINS, register_all_plugins
from .plugins.core_plugins import (
    PlanningPlugin, ResearchPlugin, CodingPlugin, TestingPlugin,
    BenchmarkPlugin, SafetyPlugin, MemoryPlugin, DiscoveryPlugin,
    WorkflowPlugin, SelfImprovementPlugin,
)
from .recovery import SelfRecoverySystem, DegradationManager, with_fallback, with_retry, with_circuit_breaker
from .workflow import WorkflowEngine, WorkflowBuilder, WorkflowLibrary, Task
from .plugins.hermes_integration import HermesDetector, HermesIntegrator, AutoInstaller

__all__ = [
    "Config",
    "load_config",
    "HarnessError",
    "KernelError",
    "PluginError",
    "SafetyError",
    "BenchmarkError",
    "Planner",
    "plan",
    "get_all_features",
    "get_all_capabilities",
    "search_features",
    "find_by_capability",
    "PluginManager",
    "PluginBase",
    "PluginState",
    "PluginPriority",
    "PluginMetadata",
    "ALL_PLUGINS",
    "register_all_plugins",
    "PlanningPlugin",
    "ResearchPlugin",
    "CodingPlugin",
    "TestingPlugin",
    "BenchmarkPlugin",
    "SafetyPlugin",
    "MemoryPlugin",
    "DiscoveryPlugin",
    "WorkflowPlugin",
    "SelfImprovementPlugin",
    "SelfRecoverySystem",
    "DegradationManager",
    "with_fallback",
    "with_retry",
    "with_circuit_breaker",
    "WorkflowEngine",
    "WorkflowBuilder",
    "WorkflowLibrary",
    "Task",
    "HermesDetector",
    "HermesIntegrator",
    "AutoInstaller",
]


class Harness:
    """
    Main Harness class — the kernel that manages everything.
    
    Usage:
        harness = await Harness.create()
        result = await harness.run("implement feature X")
        status = await harness.status()
    """
    
    def __init__(self, config: Config = None):
        self.config = config or load_config()
        self.plugin_manager = PluginManager()
        self.recovery = SelfRecoverySystem(self.config.state_dir)
        self.workflow_engine = WorkflowEngine()
        self._initialized = False
    
    @classmethod
    async def create(cls, config: Config = None) -> "Harness":
        """Create and initialize a harness instance."""
        harness = cls(config)
        await harness.initialize()
        return harness
    
    async def initialize(self):
        """Initialize the harness."""
        if self._initialized:
            return
        
        # Register all plugins
        register_all_plugins(self.plugin_manager)
        
        # Load all plugins
        load_results = await self.plugin_manager.load_all()
        loaded = sum(1 for v in load_results.values() if v)
        total = len(load_results)
        
        # Start all plugins
        start_results = await self.plugin_manager.start_all()
        started = sum(1 for v in start_results.values() if v)
        
        # Start recovery monitoring
        await self.recovery.start_monitoring()
        
        self._initialized = True
    
    async def run(self, task: str, **kwargs) -> dict:
        """Run a task through the harness."""
        try:
            # Use planning plugin to create a plan
            plan_result = await self.plugin_manager.execute("planning", "plan", goal=task)
            
            # Execute workflow if available
            if plan_result and "steps" in plan_result:
                workflow_tasks = [
                    {
                        "id": s["step_id"],
                        "name": s["name"],
                    }
                    for s in plan_result["steps"]
                ]
                workflow_result = await self.plugin_manager.execute("workflow", "execute", tasks=workflow_tasks)
                plan_result["workflow"] = workflow_result
            
            return {
                "status": "completed",
                "task": task,
                "plan": plan_result,
            }
        except Exception as e:
            # Attempt recovery
            await self.recovery.report_failure("harness", str(e))
            return {
                "status": "failed",
                "task": task,
                "error": str(e),
            }
    
    async def status(self) -> dict:
        """Get full harness status."""
        return {
            "initialized": self._initialized,
            "plugins": self.plugin_manager.status(),
            "recovery": self.recovery.get_health_summary(),
        }
    
    async def health(self) -> dict:
        """Get health status."""
        plugin_health = await self.plugin_manager.health_check_all()
        recovery_health = self.recovery.get_health_summary()
        
        all_healthy = all(h.get("healthy", False) for h in plugin_health.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "plugins": plugin_health,
            "recovery": recovery_health,
        }
    
    async def shutdown(self):
        """Shutdown the harness."""
        await self.plugin_manager.stop_all()
        await self.recovery.stop_monitoring()
        self._initialized = False
