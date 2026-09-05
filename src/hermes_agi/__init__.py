"""
Hermes AGI/ASI Harness — Unified AI Agent Runtime.

All capabilities are plugins. The harness is the kernel that manages plugins.
Includes LLM-powered planning, real plugin execution, and Hermes integration.
"""

from __future__ import annotations

__version__ = "2.0.0"

import logging

from .config import Config, load_config
from .exceptions import BenchmarkError, HarnessError, KernelError, PluginError, SafetyError
from .llm_planning import EvaluationUtility, KnowledgeBase, LLMClient, RealPlanner
from .planning import (
    Planner,
    find_by_capability,
    get_all_capabilities,
    get_all_features,
    plan,
    search_features,
)
from .plugins.core_plugins import (
    ALL_PLUGINS,
    BenchmarkPlugin,
    CodingPlugin,
    DiscoveryPlugin,
    MemoryPlugin,
    PlanningPlugin,
    ResearchPlugin,
    SafetyPlugin,
    SelfImprovementPlugin,
    TestingPlugin,
    WorkflowPlugin,
    register_all_plugins,
)
from .plugins.hermes_integration import AutoInstaller, HermesDetector, HermesIntegrator
from .plugins.manager import PluginBase, PluginManager, PluginMetadata, PluginPriority, PluginState
from .plugins.real_plugins import (
    ALL_REAL_PLUGINS,
    RealBenchmarkPlugin,
    RealCodingPlugin,
    RealDiscoveryPlugin,
    RealPlanningPlugin,
    RealResearchPlugin,
    RealTestingPlugin,
    register_all_real_plugins,
)
from .recovery import (
    DegradationManager,
    SelfRecoverySystem,
    with_circuit_breaker,
    with_fallback,
    with_retry,
)
from .workflow import Task, WorkflowBuilder, WorkflowEngine, WorkflowLibrary

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
    "DeepResearchAgent",
    "DeepThinkingEngine",
    "HermesMissionPacket",
    "HermesWatchdogMonitor",
    "HermesIntelligenceOS",
]

from hermes_os.kernel import HermesIntelligenceOS

from .allocation import HermesMissionPacket, HermesWatchdogMonitor
from .research import DeepResearchAgent
from .thinking import DeepThinkingEngine


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
        logging.getLogger(__name__).info(
            "harness initialized: plugins loaded %d/%d, started %d", loaded, total, started
        )
        
        # Start recovery monitoring
        await self.recovery.start_monitoring()
        
        self._initialized = True
    
    async def run(self, task: str, multi_step: bool = True, mode: str = "auto", **kwargs) -> dict:
        """Run a task through the harness."""
        if not self._initialized:
            await self.initialize()

        effective_mode = kwargs.get("mode", mode)
        if effective_mode in ("dual_substrate", "intelligence_os"):
            try:
                ws_root = kwargs.get("workspace_root", getattr(self.config, "state_dir", "."))
                intel_os = HermesIntelligenceOS(workspace_root=ws_root)
                invariants = kwargs.get("invariants", ["preserve_backwards_compatibility", "zero_downtime"])
                risk_level = kwargs.get("risk_level", "low")
                principal = kwargs.get("principal", "system:master")
                plan_ir = intel_os.compile_mission(
                    request=task,
                    invariants=invariants,
                    risk_level=risk_level,
                    principal=principal,
                )
                runtime_id = kwargs.get("runtime_id", "composite_dual_substrate" if effective_mode == "dual_substrate" else None)
                exec_res = await intel_os.execute_plan_with_runtime(plan_ir, runtime_id=runtime_id)

                return {
                    "status": "completed" if exec_res.success else "failed",
                    "task": task,
                    "mode": effective_mode,
                    "plan": plan_ir.to_dict(),
                    "execution_result": {
                        "success": exec_res.success,
                        "runtime_used": exec_res.runtime_used,
                        "waves_completed": exec_res.waves_completed,
                        "step_outputs": exec_res.step_outputs,
                        "worker_sandboxes": exec_res.worker_sandboxes,
                        "proof_hash": exec_res.proof_hash,
                        "duration_s": exec_res.duration_s,
                        "error": exec_res.error,
                    },
                    "multi_step": {
                        "run_id": plan_ir.mission_id,
                        "status": "completed" if exec_res.success else "failed",
                        "score": 1.0 if exec_res.success else 0.0,
                        "proof": {"proof_hash": exec_res.proof_hash},
                        "waves": exec_res.waves_completed,
                    },
                }
            except Exception as e:
                await self.recovery.report_failure("intelligence_os", str(e))
                return {
                    "status": "failed",
                    "task": task,
                    "mode": effective_mode,
                    "error": str(e),
                }
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

            # Multi-Step LangGraph StateGraph Execution
            multi_step_payload = {}
            if multi_step:
                try:
                    from harnix.kernel import HarnessRuntimeKernel
                    kernel = HarnessRuntimeKernel()
                    state = kernel.run(task, **kwargs)
                    multi_step_payload = {
                        "run_id": state.get("run_id"),
                        "status": state.get("status"),
                        "score": state.get("score"),
                        "plan": state.get("plan", []),
                        "results": state.get("results", []),
                        "research": state.get("research_dossier", {}),
                        "thinking": state.get("thinking_summary", {}),
                        "hermes_packet": state.get("hermes_packet", {}),
                        "proof": state.get("completion_proof", {}),
                    }
                except Exception as ex:
                    multi_step_payload = {"error": str(ex)}
            
            response = {
                "status": "completed",
                "task": task,
                "plan": plan_result,
            }
            if multi_step_payload:
                response["multi_step"] = multi_step_payload
            return response
        except Exception as e:
            # Attempt recovery
            await self.recovery.report_failure("harness", str(e))
            return {
                "status": "failed",
                "task": task,
                "error": str(e),
            }

    async def research(self, topic: str, depth: int = 3) -> dict:
        """Run deep research on a topic or task."""
        from .research import DeepResearchAgent
        agent = DeepResearchAgent()
        dossier = await agent.investigate(topic, depth=depth)
        return dossier.to_dict()

    async def think(self, goal: str, context: dict = None) -> dict:
        """Run deep thinking and Graph-of-Thought deliberation on a goal."""
        from .thinking import DeepThinkingEngine
        engine = DeepThinkingEngine()
        result = await engine.deliberate(goal, context=context)
        return result.to_dict()

    async def allocate_hermes(self, task: str, role: str = "hermes-coder", **kwargs) -> dict:
        """Allocate a formal mission packet to Hermes with active watchdog monitoring."""
        from .allocation import HermesMissionPacket, HermesWatchdogMonitor
        packet = HermesMissionPacket(
            goal=task,
            assigned_role=role,
            goal_contract={"objective": task, "status": "active"},
            tool_whitelist=["filesystem_tool", "python_tool", "shell_tool", "git_tool"],
            completion_criteria=[f"Execute steps for: {task}"],
        )
        monitor = HermesWatchdogMonitor(mission_id=packet.mission_id)
        monitor.record_heartbeat()
        return {
            "packet": packet.to_dict(),
            "telemetry": monitor.get_telemetry_summary(),
        }

    def run_overnight(
        self,
        objective: str,
        max_iterations: int = 10,
        max_consecutive_failures: int = 3,
        use_current_branch: bool = False,
        stop_when: str = "",
        **kwargs,
    ) -> dict:
        """Run an autonomous overnight endurance loop (gnhf architecture)."""
        from .overnight import OvernightConfig, OvernightLoopController
        config = OvernightConfig(
            objective=objective,
            max_iterations=max_iterations,
            max_consecutive_failures=max_consecutive_failures,
            use_current_branch=use_current_branch,
            stop_when=stop_when,
            workspace_root=kwargs.get("workspace_root", "."),
        )
        controller = OvernightLoopController(config)
        summary = controller.run()
        return summary.to_dict()
    
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

    async def asi(self, task: str, **kwargs) -> dict:
        """ASI-level handling for ANY task: deliberate, execute, verify, report.

        Pipeline: mirror live Hermes home -> think (Graph-of-Thought
        deliberation, grounded in that mirror) -> run in dual_substrate mode
        (22-phase compile + isolated-sandbox execution with proof hash) ->
        health check -> single consolidated dossier.
        Every stage executes for real; failures are reported, never masked.
        """
        import time

        started = time.time()
        dossier: dict = {"task": task, "stages": {}}

        # Stage 0 (not a pipeline stage): read-only mirror of the live Hermes
        # installation. Never raises; absent home yields an empty context.
        try:
            from harness.core.hermes_integration import HermesAgentIntegration

            _mirror = HermesAgentIntegration()
            hermes_context = _mirror.mirror_hermes_home()
            hermes_context["skills_list"] = _mirror.list_mirrored_skills()
            hermes_context["boards_list"] = _mirror.list_mirrored_boards()
        except Exception as exc:  # noqa: BLE001 - recorded in dossier
            hermes_context = {
                "home": "", "profiles": 0, "cron_jobs": 0,
                "skills": 0, "boards": 0, "skills_list": [],
                "boards_list": [], "error": str(exc),
            }
        dossier["hermes_context"] = hermes_context

        try:
            thinking = await self.think(task, context={"hermes": hermes_context})
        except Exception as exc:  # noqa: BLE001 - recorded in dossier
            thinking = {"status": "failed", "error": str(exc)}
        dossier["stages"]["deliberation"] = thinking

        try:
            execution = await self.run(task, mode="dual_substrate", **kwargs)
        except Exception as exc:  # noqa: BLE001 - recorded in dossier
            execution = {"status": "failed", "task": task, "error": str(exc)}
        dossier["stages"]["execution"] = execution

        try:
            verification = await self.health()
        except Exception as exc:  # noqa: BLE001 - recorded in dossier
            verification = {"status": "unknown", "error": str(exc)}
        dossier["stages"]["verification"] = verification

        exec_ok = execution.get("status") == "completed"
        verify_ok = verification.get("status") == "healthy"
        multi = execution.get("multi_step", {}) if isinstance(execution, dict) else {}
        dossier["status"] = "completed" if (exec_ok and verify_ok) else "failed"
        dossier["proof"] = multi.get("proof", {})
        dossier["duration_s"] = round(time.time() - started, 2)
        return dossier
