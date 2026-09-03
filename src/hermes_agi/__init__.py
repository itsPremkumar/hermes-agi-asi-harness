"""
Hermes AGI/ASI Harness — Unified AI Agent Runtime.

All capabilities are plugins. The harness is the kernel that manages plugins.
Includes LLM-powered planning, real plugin execution, and Hermes integration.
"""

from __future__ import annotations

__version__ = "3.0.0"

from .config import Config, load_config
from .exceptions import HarnessError, KernelError, PluginError, SafetyError, BenchmarkError
from .planning import Planner, plan, get_all_features, get_all_capabilities, search_features, find_by_capability
from .llm_planning import LLMClient, KnowledgeBase, EvaluationUtility, RealPlanner
from .plugins.manager import PluginManager, PluginBase, PluginState, PluginPriority, PluginMetadata
from .plugins.core_plugins import ALL_PLUGINS, register_all_plugins
from .plugins.core_plugins import (
    PlanningPlugin, ResearchPlugin, CodingPlugin, TestingPlugin,
    BenchmarkPlugin, SafetyPlugin, MemoryPlugin, DiscoveryPlugin,
    WorkflowPlugin, SelfImprovementPlugin,
)
from .plugins.real_plugins import ALL_REAL_PLUGINS, register_all_real_plugins
from .plugins.real_plugins import (
    RealPlanningPlugin, RealResearchPlugin, RealCodingPlugin,
    RealTestingPlugin, RealBenchmarkPlugin, RealDiscoveryPlugin,
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
    "LLMClient",
    "KnowledgeBase",
    "EvaluationUtility",
    "RealPlanner",
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
    "ALL_REAL_PLUGINS",
    "register_all_real_plugins",
    "RealPlanningPlugin",
    "RealResearchPlugin",
    "RealCodingPlugin",
    "RealTestingPlugin",
    "RealBenchmarkPlugin",
    "RealDiscoveryPlugin",
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
    
    def __init__(self, config: Config = None, use_real_plugins: bool = True):
        self.config = config or load_config()
        self.plugin_manager = PluginManager()
        self.recovery = SelfRecoverySystem(self.config.state_dir)
        self.workflow_engine = WorkflowEngine()
        self.use_real_plugins = use_real_plugins
        self._initialized = False
    
    @classmethod
    async def create(cls, config: Config = None, use_real_plugins: bool = True) -> "Harness":
        """Create and initialize a harness instance."""
        harness = cls(config, use_real_plugins)
        await harness.initialize()
        return harness
    
    async def initialize(self):
        """Initialize the harness."""
        if self._initialized:
            return
        
        # Register plugins (real or mock)
        if self.use_real_plugins:
            register_all_real_plugins(self.plugin_manager)
        else:
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
        if not self._initialized:
            await self.initialize()
        try:
            # Use planning plugin to create a plan
            plan_result = await self.plugin_manager.execute("planning", "plan", goal=task)
            
            # Execute workflow if available
            if plan_result and isinstance(plan_result, dict):
                steps = plan_result.get("plan", {}).get("steps", [])
                if steps:
                    workflow_tasks = [
                        {
                            "id": s.get("id", f"s{i}"),
                            "name": s.get("name", f"step_{i}"),
                        }
                        for i, s in enumerate(steps)
                    ]
                    try:
                        workflow_result = await self.plugin_manager.execute("workflow", "execute", tasks=workflow_tasks)
                        plan_result["workflow"] = workflow_result
                    except Exception as e:
                        plan_result["workflow_error"] = str(e)
            
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
    
    async def benchmark(self, name: str = "all") -> dict:
        """Run benchmarks through the harness."""
        if not self._initialized:
            await self.initialize()
        try:
            res = await self.plugin_manager.execute("benchmark", "run", name=name)
            if isinstance(res, dict):
                if "status" not in res:
                    res["status"] = "completed"
                return res
        except Exception:
            pass
        from .benchmarks.runner import BenchmarkRunner
        runner = BenchmarkRunner()
        return await runner.run(name)
    
    async def spawn(self, bot_name: str, command: str) -> dict:
        """Spawn a specialized bot profile."""
        from .agents.swarm import BotSwarm
        swarm = BotSwarm()
        if bot_name not in swarm._profiles and f"harness-{bot_name}" in swarm._profiles:
            bot_name = f"harness-{bot_name}"
        return await swarm.spawn(bot_name, command)
    
    async def discover(self, query: str = "") -> dict:
        """Discover features and capabilities."""
        from .discovery.engine import MetaDiscovery
        engine = await MetaDiscovery.create()
        if query:
            results = engine.search(query)
            return {"query": query, "count": len(results), "features": [f.name for f in results]}
        all_features = engine.get_all_features()
        return {"categories": {k: [f.name for f in v] for k, v in all_features.items()}, "total": sum(len(v) for v in all_features.values())}
    
    async def status(self) -> dict:
        """Get full harness status across kernel, plugins, bots, benchmarks, and recovery."""
        from .agents.swarm import BotSwarm
        from .benchmarks.runner import BENCHMARK_REGISTRY
        swarm = BotSwarm()
        return {
            "initialized": self._initialized,
            "kernel": "running" if self._initialized else "stopped",
            "plugins": self.plugin_manager.status(),
            "bots": await swarm.status(),
            "benchmarks": {"available": list(BENCHMARK_REGISTRY.keys()), "count": len(BENCHMARK_REGISTRY)},
            "recovery": self.recovery.get_health_summary(),
        }
    
    async def health(self) -> dict:
        """Get health status across all subsystems."""
        plugin_health = await self.plugin_manager.health_check_all()
        recovery_health = self.recovery.get_health_summary()
        all_healthy = all(h.get("healthy", False) for h in plugin_health.values()) if plugin_health else True
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "kernel": "healthy" if self._initialized else "idle",
            "plugins": plugin_health,
            "recovery": recovery_health,
        }
    
    async def shutdown(self):
        """Shutdown the harness."""
        await self.plugin_manager.stop_all()
        await self.recovery.stop_monitoring()
        self._initialized = False
