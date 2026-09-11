"""
RuntimeKernel - Main orchestrator for the AGI/ASI harness.

The RuntimeKernel ties together all sub-modules:
- ConfigManager: dynamic configuration, hot-reload
- EventDispatcher: event-driven hooks
- MessageBus: inter-agent communication
- AgentManager: spawn, track, delegate, terminate agents
- StateGraphEngine: LangGraph-style state graph execution

The kernel is the entry point for the entire harness. It initializes
all subsystems, wires events, and provides the high-level API that
other modules (planner, executor, memory, etc.) use.
"""

from __future__ import annotations

import threading
import time
import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .agent_manager import AgentManager, AgentState
from .config_manager import ConfigManager
from .event_dispatcher import Event, EventDispatcher
from .message_bus import MessageBus, Message
from .state_graph import StateGraphEngine, GraphState


class KernelState(Enum):
    """Possible states for the kernel."""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    ERROR = "error"


class RuntimeKernel:
    """
    Main orchestrator for the harness.

    Coordinates all sub-modules and provides the primary API for
    agent lifecycle, graph execution, and inter-module communication.

    Usage:
        kernel = RuntimeKernel({"max_agents": 10})
        kernel.initialize()
        kernel.start()

        agent = kernel.spawn_agent(name="worker", task="process data")
        graph = kernel.create_graph("pipeline")
        graph.add_node("step1", func1)
        graph.add_node("step2", func2)
        graph.add_edge("step1", "step2")
        graph.set_entry_point("step1")
        result = kernel.execute_graph(graph)

        kernel.shutdown()
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.kernel_id = f"kernel-{uuid.uuid4().hex[:12]}"
        self.state = KernelState.CREATED

        # Sub-modules
        self.config = ConfigManager(config or {})
        self.events = EventDispatcher()
        self.messages = MessageBus()
        self.agents = AgentManager()

        # Graph registry
        self._graphs: Dict[str, StateGraphEngine] = {}

        # Internal state
        self._state_lock = threading.RLock()
        self._hooks_wired = False
        self._created_at = time.time()
        self._started_at: Optional[float] = None
        self._stopped_at: Optional[float] = None

    @property
    def is_running(self) -> bool:
        return self.state in (KernelState.READY, KernelState.RUNNING)

    @property
    def uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        end = self._stopped_at or time.time()
        return end - self._started_at

    def initialize(self) -> None:
        """Initialize all kernel sub-systems."""
        self._set_state(KernelState.INITIALIZING)
        self._wire_hooks()
        self.events.dispatch("kernel.initialized", {"kernel_id": self.kernel_id})
        self._set_state(KernelState.READY)

    def start(self) -> None:
        """Start the kernel and all sub-systems."""
        if self.state == KernelState.CREATED:
            self.initialize()
        elif self.state not in (KernelState.READY, KernelState.PAUSED):
            raise RuntimeError(f"Cannot start kernel in state {self.state}")

        self._started_at = time.time()
        self._set_state(KernelState.RUNNING)
        self.messages.start_async()
        self.events.dispatch("kernel.started", {"kernel_id": self.kernel_id})

    def pause(self) -> None:
        """Pause the kernel (stops processing but retains state)."""
        if self.state != KernelState.RUNNING:
            raise RuntimeError(f"Cannot pause kernel in state {self.state}")
        self._set_state(KernelState.PAUSED)
        self.events.dispatch("kernel.paused", {"kernel_id": self.kernel_id})

    def resume(self) -> None:
        """Resume from paused state."""
        if self.state != KernelState.PAUSED:
            raise RuntimeError(f"Cannot resume kernel in state {self.state}")
        self._set_state(KernelState.RUNNING)
        self.events.dispatch("kernel.resumed", {"kernel_id": self.kernel_id})

    def shutdown(self, timeout: float = 30.0) -> None:
        """Gracefully shut down the kernel."""
        self._set_state(KernelState.SHUTTING_DOWN)
        self.events.dispatch("kernel.shutting_down", {"kernel_id": self.kernel_id})

        # Stop async message bus
        self.messages.stop_async()

        # Terminate all active agents
        for agent in self.agents.get_all():
            if agent.state in (AgentState.IDLE, AgentState.RUNNING, AgentState.WAITING):
                self.agents.terminate(agent.agent_id, reason="kernel_shutdown")

        self._stopped_at = time.time()
        self._set_state(KernelState.STOPPED)
        self.events.dispatch("kernel.stopped", {"kernel_id": self.kernel_id})

    def spawn_agent(
        self,
        name: str,
        agent_type: str = "generic",
        task: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Spawn a new agent and return its ID."""
        agent = self.agents.spawn(
            name=name,
            agent_type=agent_type,
            parent_id=parent_id,
            task=task,
            metadata=metadata,
        )
        self.events.dispatch(
            "agent.spawned",
            {"agent_id": agent.agent_id, "name": name, "type": agent_type},
        )
        return agent.agent_id

    def start_agent(self, agent_id: str) -> bool:
        """Transition an agent to RUNNING state."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False
        if agent.state not in (AgentState.IDLE, AgentState.PENDING, AgentState.SPAWNING):
            return False
        return self.agents.transition(agent_id, AgentState.RUNNING)

    def complete_agent(self, agent_id: str, result: Any = None) -> bool:
        """Mark an agent as completed."""
        success = self.agents.transition(agent_id, AgentState.COMPLETED, result=result)
        if success:
            agent = self.agents.get(agent_id)
            self.events.dispatch(
                "agent.completed",
                {"agent_id": agent_id, "result": result},
            )
        return success

    def fail_agent(self, agent_id: str, error: str) -> bool:
        """Mark an agent as failed."""
        success = self.agents.transition(agent_id, AgentState.FAILED, error=error)
        if success:
            self.events.dispatch(
                "agent.failed",
                {"agent_id": agent_id, "error": error},
            )
        return success

    def terminate_agent(self, agent_id: str, reason: str = "manual") -> bool:
        """Terminate an agent."""
        return self.agents.terminate(agent_id, reason=reason)

    def delegate_task(
        self, from_agent_id: str, to_agent_id: str, task: str
    ) -> bool:
        """Delegate a task between agents."""
        success = self.agents.delegate(from_agent_id, to_agent_id, task)
        if success:
            self.events.dispatch(
                "agent.delegated",
                {"from": from_agent_id, "to": to_agent_id, "task": task},
            )
        return success

    def create_graph(
        self, name: str, graph_id: Optional[str] = None
    ) -> StateGraphEngine:
        """Create and register a new state graph."""
        if graph_id is None:
            graph_id = f"graph-{uuid.uuid4().hex[:12]}"
        graph = StateGraphEngine(name=name)
        self._graphs[graph_id] = graph
        self.events.dispatch("graph.created", {"graph_id": graph_id, "name": name})
        return graph

    def get_graph(self, graph_id: str) -> Optional[StateGraphEngine]:
        """Get a registered graph by ID."""
        return self._graphs.get(graph_id)

    def execute_graph(
        self,
        graph: Union[StateGraphEngine, str],
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a state graph. Accepts a graph object or registered ID."""
        if isinstance(graph, str):
            graph = self._graphs.get(graph)
            if graph is None:
                raise ValueError(f"Graph '{graph}' not found")

        self.events.dispatch(
            "graph.executing",
            {"graph_name": graph.name, "nodes": graph.node_count},
        )

        result = graph.execute(initial_state)

        self.events.dispatch(
            "graph.executed",
            {
                "graph_name": graph.name,
                "success": result.success,
                "execution_time": result.execution_time,
            },
        )

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get a comprehensive status report of the kernel."""
        return {
            "kernel_id": self.kernel_id,
            "state": self.state.value,
            "uptime": self.uptime,
            "agents": self.agents.get_stats(),
            "graphs": len(self._graphs),
            "topics": len(self.messages.get_topics()),
            "events_tracked": len(self.events.get_event_names()),
        }

    def on_event(self, event_name: str, handler: Optional[Callable[[Event], Any]] = None, **kwargs):
        """Decorator-friendly event registration."""
        if handler is None:
            def decorator(fn):
                return self.events.on(event_name, fn, **kwargs)
            return decorator
        return self.events.on(event_name, handler, **kwargs)

    def emit_event(self, event_name: str, data: Any = None) -> Event:
        """Dispatch an event through the kernel's event system."""
        return self.events.dispatch(event_name, data=data, source=self.kernel_id)

    def publish_message(self, topic: str, data: Any = None, **kwargs) -> Message:
        """Publish a message to the bus."""
        return self.messages.publish(topic, data=data, **kwargs)

    def subscribe_topic(self, topic: str, callback: Optional[Callable[[Message], Any]] = None, **kwargs):
        """Subscribe to a message bus topic. Supports decorator usage."""
        if callback is None:
            def decorator(fn):
                return self.messages.subscribe(topic, fn, **kwargs)
            return decorator
        return self.messages.subscribe(topic, callback, **kwargs)

    def _set_state(self, new_state: KernelState) -> None:
        """Update the kernel state."""
        with self._state_lock:
            self.state = new_state

    def _wire_hooks(self) -> None:
        """Wire inter-module event hooks."""
        if self._hooks_wired:
            return

        # Agent events -> message bus
        self.events.on("agent.spawned", self._on_agent_spawned)
        self.events.on("agent.completed", self._on_agent_completed)
        self.events.on("agent.failed", self._on_agent_failed)

        # Config changes -> events
        self.config.on_change(self._on_config_changed)

        self._hooks_wired = True

    def _on_agent_spawned(self, event: Event) -> None:
        """Handle agent spawned event."""
        data = event.data or {}
        self.messages.publish(
            f"agent.{data.get('agent_id', 'unknown')}.spawned",
            data,
            source="kernel",
        )

    def _on_agent_completed(self, event: Event) -> None:
        """Handle agent completed event."""
        data = event.data or {}
        self.messages.publish(
            f"agent.{data.get('agent_id', 'unknown')}.completed",
            data,
            source="kernel",
        )

    def _on_agent_failed(self, event: Event) -> None:
        """Handle agent failed event."""
        data = event.data or {}
        self.messages.publish(
            f"agent.{data.get('agent_id', 'unknown')}.failed",
            data,
            source="kernel",
        )

    def _on_config_changed(self, key: str, old_value: Any, new_value: Any) -> None:
        """Handle config change."""
        self.events.dispatch(
            "config.changed",
            {"key": key, "old": old_value, "new": new_value},
        )
