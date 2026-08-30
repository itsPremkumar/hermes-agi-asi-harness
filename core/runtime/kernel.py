"""
Hermes Kernel — the minimal execution core.

This is the ONLY code that runs in the trusted inner ring.
Everything else is a plugin loaded by the kernel.

Extracted & enhanced from:
- hermes-agent: agent_init.py, conversation_loop.py
- agi-hermes-advanced-master: agent_loop.py, plugin_manager.py
- hermes-free-harness: model_router.py, plugin base
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class KernelState(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"


@dataclass
class KernelConfig:
    """Kernel configuration."""
    profile: str = "default"
    zero_cost: bool = True  # free-first mode
    offline: bool = False
    max_parallel_tasks: int = 4
    max_subagents: int = 8
    max_retries: int = 3
    max_iterations: int = 25
    checkpoint_interval: int = 30  # seconds
    plugins_root: Path = Path("plugins")
    state_path: Path = Path("state")
    log_level: str = "INFO"
    hermes_home: Path = Path.home() / ".hermes-agi"


class HermesKernel:
    """
    The Hermes Kernel — minimal trusted core.
    
    Responsibilities:
    1. Load and manage plugins
    2. Route events
    3. Manage state lifecycle
    4. Enforce security boundaries
    5. Coordinate execution
    
    Everything else is delegated to plugins.
    """

    def __init__(self, config: Optional[KernelConfig] = None):
        self.config = config or KernelConfig()
        self.state = KernelState.INITIALIZED
        self.kernel_id = str(uuid.uuid4())
        self.started_at = datetime.utcnow()
        
        # Core components (loaded from plugins)
        self.plugin_manager: Optional[Any] = None
        self.event_bus: Optional[Any] = None
        self.state_manager: Optional[Any] = None
        self.model_router: Optional[Any] = None
        self.security_core: Optional[Any] = None
        self.memory_system: Optional[Any] = None
        self.execution_engine: Optional[Any] = None
        self.verification_engine: Optional[Any] = None
        self.recovery_engine: Optional[Any] = None
        self.evolution_engine: Optional[Any] = None
        self.ecosystem_intel: Optional[Any] = None
        self.supervisor: Optional[Any] = None
        self.world_model: Optional[Any] = None
        self.jit_harness: Optional[Any] = None
        self.self_healing: Optional[Any] = None
        
        # Phase 1: Executive Foundation
        self.goal_contract: Optional[Any] = None
        self.context_os: Optional[Any] = None
        self.safety_gates: Optional[Any] = None
        self.completion_proof: Optional[Any] = None

        # Phase 2: Persistent Intelligence
        self.persistent_state: Optional[Any] = None
        self.mission_queue: Optional[Any] = None
        self.belief_engine: Optional[Any] = None
        self.capability_registry: Optional[Any] = None
        
        # v9: Universal Environment Intelligence & Action Plane
        self.environment_model: Optional[Any] = None
        self.affordance_model: Optional[Any] = None
        self.state_estimator: Optional[Any] = None
        self.consequence_simulator: Optional[Any] = None
        self.universal_action_protocol: Optional[Any] = None
        self.universal_observation_protocol: Optional[Any] = None
        self.event_bus_v9: Optional[Any] = None
        self.transaction_model: Optional[Any] = None
        self.safety_envelope_manager: Optional[Any] = None
        self.master_orchestrator: Optional[Any] = None
        
        # v10: Closed-Loop Self-Improving System
        self.closed_loop_orchestrator: Optional[Any] = None
        self.policy_bridge: Optional[Any] = None
        self.rsi_engine: Optional[Any] = None
        self.action_explainer: Optional[Any] = None
        self.audit_trail: Optional[Any] = None
        self.continuous_benchmark: Optional[Any] = None
        self.collaboration_protocol: Optional[Any] = None
        
        # v9: Learning Plane
        self.trajectory_store: Optional[Any] = None
        self.trajectory_replay: Optional[Any] = None
        self.policy_learner: Optional[Any] = None
        self.counterfactual_evaluator: Optional[Any] = None
        self.skill_transfer: Optional[Any] = None
        
        # v9: Computer Use v2
        self.ui_state_memory: Optional[Any] = None
        self.environment_discovery: Optional[Any] = None
        self.digital_twins: Optional[Any] = None
        
        # Store HERMES_HOME for state directory
        self._state_dir = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
        
        # Runtime state
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._plugins: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        
        logger.info("Hermes Kernel initialized (id=%s)", self.kernel_id)

    async def boot(self):
        """Boot the kernel — load core plugins and start event loop."""
        logger.info("Booting Hermes Kernel...")
        
        # Load core plugins in order
        await self._load_core_plugins()
        
        # Start event bus
        if self.event_bus:
            await self.event_bus.start()
        
        # Start state manager
        if self.state_manager:
            await self.state_manager.start()
        
        # Discover and load additional plugins (tools + cognitive)
        await self._load_tool_plugins()
        
        # Wire cognitive plugins to kernel attributes
        self.supervisor = self._plugins.get("supervisor")
        self.world_model = self._plugins.get("world_model")
        if self.world_model and hasattr(self.world_model, 'world_model'):
            self.world_model = self.world_model.world_model
        self.jit_harness = self._plugins.get("jit_harness")
        if self.jit_harness and hasattr(self.jit_harness, 'generator'):
            self.jit_harness = self.jit_harness.generator
        self.self_healing = self._plugins.get("self_healing")
        if self.self_healing and hasattr(self.self_healing, 'engine'):
            self.self_healing = self.self_healing.engine
        
        # Phase 1: Executive Foundation
        self.goal_contract = self._plugins.get("goal_contract")
        self.context_os = self._plugins.get("context_os")
        if self.context_os and hasattr(self.context_os, 'set_kernel'):
            self.context_os.set_kernel(self)
        self.safety_gates = self._plugins.get("safety_gates")
        self.completion_proof = self._plugins.get("completion_proof")

        # Phase 2: Persistent Intelligence
        self.persistent_state = self._plugins.get("persistent_state")
        self.mission_queue = self._plugins.get("mission_queue")
        if self.mission_queue and hasattr(self.mission_queue, 'queue'):
            self.mission_queue = self.mission_queue.queue
        self.belief_engine = self._plugins.get("belief_engine")
        if self.belief_engine and hasattr(self.belief_engine, 'engine'):
            self.belief_engine = self.belief_engine.engine
        self.capability_registry = self._plugins.get("capability_registry")
        if self.capability_registry and hasattr(self.capability_registry, 'registry'):
            self.capability_registry = self.capability_registry.registry
        
        # v9: Initialize Universal Environment Intelligence & Action Plane
        await self._init_v9_environment_plane()
        await self._init_v9_learning_plane()
        await self._init_v9_computer_use_v2()
        
        # v10: Initialize Closed-Loop Self-Improving System
        await self._init_v10_closed_loop()
        
        # Register plugin capabilities as tools on the execution engine
        await self._register_plugin_tools()
        
        # Start health monitor
        asyncio.create_task(self._health_monitor_loop())
        
        self.state = KernelState.RUNNING
        logger.info("Hermes Kernel RUNNING (plugins=%d)", len(self._plugins))
        
        # Emit boot event
        await self.emit("kernel.booted", {"kernel_id": self.kernel_id})

    async def _init_v9_learning_plane(self):
        """Initialize the v9 Learning Plane."""
        try:
            from core.learning.trajectory_store import TrajectoryStore
            from core.learning.trajectory_replay import TrajectoryReplay
            from core.learning.policy_learning import PolicyLearner
            from core.learning.counterfactual import CounterfactualEvaluator
            from core.learning.skill_transfer import SkillTransfer

            self.trajectory_store = TrajectoryStore()
            self.trajectory_replay = TrajectoryReplay()
            self.policy_learner = PolicyLearner()
            self.counterfactual_evaluator = CounterfactualEvaluator()
            self.skill_transfer = SkillTransfer()

            logger.info("v9 Learning Plane initialized")
        except Exception as e:
            logger.warning("v9 Learning Plane initialization failed: %s", e)

    async def _init_v9_computer_use_v2(self):
        """Initialize the v9 Computer Use v2."""
        try:
            from core.computer_use_v2.ui_memory import UIStateMemory
            from core.computer_use_v2.discovery import EnvironmentDiscovery

            self.ui_state_memory = UIStateMemory()
            self.environment_discovery = EnvironmentDiscovery()
            self.digital_twins = {}

            logger.info("v9 Computer Use v2 initialized")
        except Exception as e:
            logger.warning("v9 Computer Use v2 initialization failed: %s", e)

    async def _init_v10_closed_loop(self):
        """Initialize the v10 Closed-Loop Self-Improving System."""
        try:
            from core.learning.policy_learning import PolicyLearner
            from core.orchestrator.policy_bridge import PolicyBridge
            from core.orchestrator.closed_loop import ClosedLoopOrchestrator
            from core.rsi.integration import RSIIntegrationEngine
            from core.explanation.explainer import ActionExplainer, AuditTrail
            from core.benchmark.continuous import ContinuousBenchmark
            from core.collaboration.protocol import AgentCollaborationProtocol

            # Policy learner should already be initialized from v9
            if not hasattr(self, 'policy_learner') or self.policy_learner is None:
                self.policy_learner = PolicyLearner()
            
            self.policy_bridge = PolicyBridge(self.policy_learner)
            self.closed_loop_orchestrator = ClosedLoopOrchestrator(
                self.policy_bridge,
                self.trajectory_store,
                self.policy_learner,
                self.safety_envelope_manager,
                self.consequence_simulator,
                self.environment_model,
            )
            self.rsi_engine = RSIIntegrationEngine(
                self.policy_learner,
                self.policy_bridge,
                self.trajectory_store,
                self.trajectory_replay,
            )
            self.action_explainer = ActionExplainer()
            self.audit_trail = AuditTrail()
            self.continuous_benchmark = ContinuousBenchmark()
            self.collaboration_protocol = AgentCollaborationProtocol()

            logger.info("v10 Closed-Loop Self-Improving System initialized")
        except Exception as e:
            logger.warning("v10 Closed-Loop initialization failed: %s", e)

    async def _init_v9_environment_plane(self):
        """Initialize the v9 Universal Environment Intelligence & Action Plane."""
        try:
            from core.environment.model import EnvironmentModel
            from core.environment.affordances import AffordanceModel
            from core.environment.state_estimation import StateEstimator
            from core.environment.consequence import ConsequenceSimulator
            from core.protocols.uap import UniversalActionProtocol
            from core.protocols.uop import PerceptionFusion
            from core.protocols.event_algebra import EventBus
            from core.action.transaction import TransactionModel
            from core.action.safety_envelope import SafetyEnvelopeManager
            from core.orchestrator.master_loop import MasterOrchestrator

            self.environment_model = EnvironmentModel()
            self.affordance_model = AffordanceModel()
            self.state_estimator = StateEstimator()
            self.consequence_simulator = ConsequenceSimulator()
            self.consequence_simulator.load_default_rules()
            self.universal_action_protocol = UniversalActionProtocol()
            self.universal_observation_protocol = PerceptionFusion()
            self.event_bus_v9 = EventBus()
            self.transaction_model = TransactionModel()
            self.safety_envelope_manager = SafetyEnvelopeManager()
            self.master_orchestrator = MasterOrchestrator()

            logger.info("v9 Environment Intelligence Plane initialized")
        except Exception as e:
            logger.warning("v9 Environment Plane initialization failed: %s", e)

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down Hermes Kernel...")
        self.state = KernelState.SHUTTING_DOWN
        
        # Cancel active tasks
        for task_id, task in self._active_tasks.items():
            task.cancel()
            logger.debug("Cancelled task: %s", task_id)
        
        # Shutdown plugins in reverse order
        for name, plugin in reversed(list(self._plugins.items())):
            try:
                if hasattr(plugin, 'shutdown'):
                    await plugin.shutdown()
                    logger.debug("Plugin shutdown: %s", name)
            except Exception as e:
                logger.error("Plugin shutdown error (%s): %s", name, e)
        
        self.state = KernelState.STOPPED
        logger.info("Hermes Kernel STOPPED")

    async def _load_core_plugins(self):
        """Load core plugins in dependency order."""
        core_plugins = [
            ("security_core", "plugins.security_core"),
            ("event_bus", "plugins.event_bus"),
            ("state_manager", "plugins.state_manager"),
            ("model_router", "plugins.model_router"),
            ("memory_system", "plugins.memory_system"),
            ("plugin_manager", "plugins.plugin_manager"),
            ("execution_engine", "plugins.execution_engine"),
            ("verification_engine", "plugins.verification_engine"),
            ("recovery_engine", "plugins.recovery_engine"),
            ("evolution_engine", "plugins.evolution_engine"),
            ("ecosystem_intel", "plugins.ecosystem_intelligence"),
            ("persistent_state", "core.persistent_state"),
            ("verification", "core.verification"),
            ("supervisor", "core.runtime.supervisor"),
            ("daily_dev", "core.runtime.daily_dev"),
        ]
        
        for attr_name, module_path in core_plugins:
            try:
                module = __import__(module_path, fromlist=["create"])
                plugin = await module.create(self)
                setattr(self, attr_name, plugin)
                self._plugins[attr_name] = plugin
                logger.info("Loaded core plugin: %s", attr_name)
            except ImportError:
                logger.warning("Core plugin not available: %s", module_path)
            except Exception as e:
                logger.error("Failed to load plugin %s: %s", attr_name, e)

    async def _load_tool_plugins(self):
        """Discover and load tool/utility plugins from the plugins/ directory.

        These are plugins that follow the simpler PluginBase contract
        (Plugin class in __init__.py with load/start/health) rather than
        the kernel create() factory pattern.
        """
        import importlib
        import importlib.util
        from pathlib import Path

        tools_root = self.config.plugins_root
        if not tools_root.exists():
            return

        tool_plugin_names = [
            "python_tool", "filesystem_tool", "shell_tool", "http_tool",
            "git_tool", "rag_engine", "vision_engine", "document_intel",
            "memory_curator", "permission_sandbox", "audit_logger",
            "streaming_output", "config_manager", "permission_system",
            "skill_learner", "swarm_intelligence", "debate_engine",
            "multi_agent_orchestrator", "mcp_client",
            # Advanced cognitive plugins
            "world_model", "jit_harness", "self_healing", "knowledge_graph",
            "benchmarks", "sandbox_plugin", "metacognition", "goal_engine",
            "supervisor",
            # Phase 1: Executive Foundation
            "goal_contract", "context_os", "safety_gates", "completion_proof",
            # Phase 2: Persistent Intelligence
            "belief_engine", "mission_queue", "capability_registry",
            # Phase 3: Autonomous Execution
            "watchdog", "economic_ledger",
            # Phase 4: Multi-Agent
            "independent_critic", "debate_protocol",
            # Phase 5: Learning
            "self_evaluation", "skill_forge", "curriculum_engine", "sleep_cycle",
            # Phase 6: Evolution
            "evolution_safety_loop", "benchmark_db", "self_improvement_boundary", "world_sync",
            # Phase 7: Advanced
            "computer_use", "engineering_factory", "operating_modes",
            # Phase 8: Deployment
            "observability_dashboard",
            # Phase 9: Cognitive Extensions
            "causal_model", "capability_graph", "self_model",
            # Phase 10: Infrastructure & Safety
            "event_sourced_state", "rollback", "scenario_harness",
            "agent_communication", "research_engine_v2", "sandbox_architecture",
            # Phase 11: Intelligence Scaling
            "model_router_v2", "compute_scaling", "agent_fabric",
            "failure_intelligence", "calibration", "anti_goodhart",
            "bottleneck_detector", "evolution_archive",
        ]

        loaded_count = 0
        for name in tool_plugin_names:
            if name in self._plugins:
                continue  # already loaded as core
            try:
                import importlib
                module = importlib.import_module(f"plugins.{name}")
                # Try create() factory first (kernel-managed plugins)
                if hasattr(module, "create"):
                    plugin = await module.create(self)
                    self._plugins[name] = plugin
                    loaded_count += 1
                    logger.info("Loaded plugin (create): %s", name)
                # Fall back to Plugin class (legacy pattern)
                elif hasattr(module, "Plugin"):
                    plugin = module.Plugin()
                    await plugin.load()
                    await plugin.start()
                    self._plugins[name] = plugin
                    loaded_count += 1
                    logger.info("Loaded tool plugin: %s", name)
            except Exception as e:
                logger.warning("Failed to load tool plugin %s: %s", name, e)

        if loaded_count:
            logger.info("Loaded %d tool plugins", loaded_count)

    async def _register_plugin_tools(self):
        """Register plugin capabilities as tools on the execution engine."""
        if not self.execution_engine:
            return
        
        # Map plugin capabilities to tool names + method names
        capability_tool_map = {
            "python_execute": ("python_exec", "run"),
            "shell_execution": ("shell", "run"),
            "file_write": ("file_write", "write"),
            "file_read": ("file_read", "read"),
            "http_get": ("http_get", "get"),
            "semantic_search": ("memory_search", "search"),
            "state_persistence": ("state_get", "get_state"),
            "checkpoint": ("checkpoint", "create_checkpoint"),
            "evolution": ("evolve", "evolve"),
            "rag_search": ("rag_search", "search"),
            "vision_analyze": ("vision", "analyze"),
            "world_model": ("world_query", "get_world_summary"),
            "knowledge_graph": ("kg_search", "search_entities"),
            "benchmark": ("benchmark_run", "run_suite"),
            "task_profiling": ("task_profile", "analyze_task"),
        }
        
        registered = 0
        for plugin_name, plugin in self._plugins.items():
            if not hasattr(plugin, 'get_capabilities'):
                continue
            try:
                caps = plugin.get_capabilities()
                for cap in caps:
                    if cap in capability_tool_map:
                        tool_name, method_name = capability_tool_map[cap]
                        if hasattr(plugin, method_name):
                            func = getattr(plugin, method_name)
                            # Wrap to accept action_input dict and unpack to kwargs
                            async def wrapped_tool(action_input=None, _func=func, _plugin=plugin):
                                kwargs = action_input or {}
                                try:
                                    result = _func(**kwargs)
                                    if asyncio.iscoroutine(result):
                                        result = await result
                                    return result
                                except TypeError:
                                    # Method may take a single positional arg
                                    if isinstance(kwargs, dict) and len(kwargs) == 1:
                                        val = list(kwargs.values())[0]
                                        result = _func(val)
                                        if asyncio.iscoroutine(result):
                                            result = await result
                                        return result
                                    raise
                            self.execution_engine.register_tool(tool_name, wrapped_tool)
                            registered += 1
                            logger.debug("Registered tool %s from %s.%s", tool_name, plugin_name, method_name)
            except Exception as e:
                logger.warning("Failed to register tools from %s: %s", plugin_name, e)
        
        logger.info("Registered %d tools from plugins", registered)

    async def submit_task(self, task: "Task") -> str:
        """Submit a task for execution."""
        
        # Persist task to state_manager if available, use its ID
        if self.state_manager and self.state_manager.manager:
            try:
                session_id = getattr(self.state_manager.manager, 'session_id', None)
                sm_task_id = self.state_manager.manager.create_task(
                    title=task.goal,
                    description=getattr(task, 'description', ''),
                    session_id=session_id or None,
                )
                task.task_id = sm_task_id
            except Exception as e:
                logger.debug("Failed to create task in state_manager: %s", e)
        
        task_id = task.task_id
        
        # Update task status to running
        if self.state_manager and self.state_manager.manager:
            try:
                self.state_manager.manager.update_task(task_id, status="running")
            except Exception:
                pass
        
        if self.execution_engine:
            asyncio_task = asyncio.create_task(
                self.execution_engine.execute(task)
            )
            self._active_tasks[task_id] = asyncio_task
            await self.emit("task.submitted", {"task_id": task_id, "goal": task.goal})
        
        return task_id

    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Emit an event on the event bus."""
        if self.event_bus:
            await self.event_bus.emit_async(event_type, data)

    async def plan_and_execute(self, goal: str, **kwargs) -> Dict[str, Any]:
        """Plan a task from a natural-language goal and execute it.
        
        Uses the planning engine (if available) or a simple fallback
        to break the goal into steps, then executes them via the
        execution_engine. Returns a result dict with outcome details.
        """
        task = Task(goal=goal, task_id=f"auto-{int(time.time())}")
        task_id = await self.submit_task(task)
        
        # Wait for completion (with timeout)
        try:
            await asyncio.wait_for(
                asyncio.create_task(self._wait_for_task(task_id)),
                timeout=kwargs.get("timeout", 60)
            )
        except asyncio.TimeoutError:
            logger.warning(f"Task {task_id} timed out")
        
        return {
            "task_id": task_id,
            "goal": goal,
            "status": "completed" if task_id not in self._active_tasks else "timeout",
        }

    async def _wait_for_task(self, task_id: str):
        """Wait for a task to complete."""
        while task_id in self._active_tasks:
            await asyncio.sleep(0.5)

    async def _health_monitor_loop(self):
        """Continuous health monitoring."""
        while self.state == KernelState.RUNNING:
            try:
                health = await self.health_check()
                if health["status"] != "healthy":
                    logger.warning("Health check: %s", health)
                await asyncio.sleep(self.config.checkpoint_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health monitor error: %s", e)

    async def health_check(self) -> Dict[str, Any]:
        """Run health checks on all plugins."""
        results = {}
        for name, plugin in self._plugins.items():
            try:
                if hasattr(plugin, 'health'):
                    raw = await plugin.health()
                    # Normalize: some plugins use 'healthy' + 'state' instead of 'status'
                    if 'status' not in raw:
                        healthy = raw.get('healthy', False)
                        state = raw.get('state', '')
                        if healthy and state in ('running', 'loaded'):
                            raw['status'] = 'healthy'
                        elif state and state not in ('unregistered', 'registered'):
                            raw['status'] = 'degraded'
                        else:
                            raw['status'] = 'unknown'
                    results[name] = raw
                else:
                    results[name] = {"status": "unknown"}
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        
        all_healthy = all(
            r.get("status") in ("healthy", "unknown", "not_started") for r in results.values()
        )
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "kernel_id": self.kernel_id,
            "state": self.state.value,
            "plugins": results,
            "active_tasks": len(self._active_tasks),
        }


@dataclass
class Task:
    """A task submitted to the kernel."""
    goal: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    budget: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
