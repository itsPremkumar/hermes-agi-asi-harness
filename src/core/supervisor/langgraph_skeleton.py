"""LangGraph Outer Skeleton — State machine for supervisor orchestration.

Implements the structural control flow:
    Plan → Dispatch → Monitor → Adjust → (loop until done)

Each node dispatches a DeepAgent for cognitive work.
LangGraph handles: branching, looping, checkpointing, streaming.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# State definitions
# ---------------------------------------------------------------------------

class NodeName(str, Enum):
    """LangGraph node names."""
    PLAN = "plan"
    DISPATCH = "dispatch"
    MONITOR = "monitor"
    ADJUST = "adjust"
    EVOLVE = "evolve"
    COMPLETE = "complete"


class EdgeCondition(str, Enum):
    """Edge routing conditions."""
    CONTINUE = "continue"
    STALLED = "stalled"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_EVOLUTION = "needs_evolution"


@dataclass
class SupervisorState:
    """Full supervisor state (LangGraph state object)."""
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Goal
    goal_description: str = ""
    goal_status: str = "pending"

    # Planning
    plan: Dict[str, Any] = field(default_factory=dict)
    current_step: int = 0
    total_steps: int = 0

    # Execution
    current_node: str = NodeName.PLAN.value
    iterations: int = 0
    max_iterations: int = 20

    # Results
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Monitoring
    score: float = 0.0
    stall_count: int = 0
    max_stalls: int = 5

    # Evolution
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)
    strategy: str = "default"

    # Memory
    context: Dict[str, Any] = field(default_factory=dict)
    memory_snapshot: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_description": self.goal_description,
            "goal_status": self.goal_status,
            "current_node": self.current_node,
            "iterations": self.iterations,
            "score": self.score,
            "stall_count": self.stall_count,
            "strategy": self.strategy,
        }


# ---------------------------------------------------------------------------
# LangGraph Skeleton
# ---------------------------------------------------------------------------

class LangGraphSkeleton:
    """LangGraph state machine skeleton for the supervisor.

    Nodes:
        plan: DeepAgent analyzes goal and creates plan
        dispatch: DeepAgent executes current plan step
        monitor: Check progress, detect stalls
        adjust: Re-plan or change strategy
        evolve: Generate variations when stalled

    Edges:
        plan → dispatch (always)
        dispatch → monitor (always)
        monitor → dispatch (if more steps)
        monitor → adjust (if stalled)
        monitor → complete (if done)
        adjust → dispatch (retry with new plan)
        evolve → dispatch (retry with evolved strategy)
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        max_iterations: int = 20,
        max_stalls: int = 5,
    ):
        self._data_dir = data_dir or Path.home() / ".hermes" / "supervisor" / "langgraph"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._max_iterations = max_iterations
        self._max_stalls = max_stalls

        # Node handlers (registered externally)
        self._nodes: Dict[str, Callable] = {}

        # Edge routing
        self._edges: Dict[str, Dict[str, Callable]] = {}

        # State
        self._state: Optional[SupervisorState] = None

        # Execution log
        self._execution_log: List[Dict[str, Any]] = []

    # --- Node registration ---

    def register_node(self, name: str, handler: Callable) -> None:
        """Register a node handler. handler(state) -> new_state."""
        self._nodes[name] = handler

    def register_edge(self, from_node: str, condition: str, to_node: str, predicate: Callable) -> None:
        """Register a conditional edge. predicate(state) -> bool."""
        if from_node not in self._edges:
            self._edges[from_node] = {}
        self._edges[from_node][condition] = (to_node, predicate)

    # --- Graph execution ---

    def run(self, goal_description: str, context: Optional[Dict[str, Any]] = None) -> SupervisorState:
        """Run the full state machine."""
        self._state = SupervisorState(
            goal_description=goal_description,
            max_iterations=self._max_iterations,
            max_stalls=self._max_stalls,
            context=context or {},
        )

        self._log_event("start", {"goal": goal_description})

        while self._state.iterations < self._state.max_iterations:
            self._state.iterations += 1
            self._state.updated_at = time.time()

            # Get current node handler
            node_name = self._state.current_node
            handler = self._nodes.get(node_name)

            if not handler:
                self._state.goal_status = "failed"
                self._state.errors.append(f"Unknown node: {node_name}")
                break

            # Execute node
            self._log_event("node_start", {"node": node_name, "iteration": self._state.iterations})
            self._state = handler(self._state)
            self._log_event("node_end", {"node": node_name, "score": self._state.score})

            # Check for completion
            if self._state.goal_status in ("completed", "failed"):
                break

            # Route to next node
            next_node = self._route(node_name, self._state)
            self._state.current_node = next_node

        # Final status
        if self._state.iterations >= self._state.max_iterations:
            self._state.goal_status = "timeout"

        self._log_event("end", {
            "status": self._state.goal_status,
            "iterations": self._state.iterations,
            "score": self._state.score,
        })

        return self._state

    def _route(self, current_node: str, state: SupervisorState) -> str:
        """Route to next node based on edge conditions."""
        edges = self._edges.get(current_node, {})

        for condition, (to_node, predicate) in edges.items():
            try:
                if predicate(state):
                    return to_node
            except Exception:
                continue

        # Default: stay at dispatch
        return NodeName.DISPATCH.value

    # --- Execution log ---

    def _log_event(self, event: str, data: Dict[str, Any]) -> None:
        """Log an execution event."""
        self._execution_log.append({
            "event": event,
            "timestamp": time.time(),
            "data": data,
        })

    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get execution log."""
        return self._execution_log.copy()

    def save_checkpoint(self) -> None:
        """Save state checkpoint."""
        if self._state:
            path = self._data_dir / f"checkpoint_{self._state.id}.json"
            path.write_text(json.dumps(self._state.to_dict(), indent=2))


# ---------------------------------------------------------------------------
# Default edge predicates
# ---------------------------------------------------------------------------

def is_completed(state: SupervisorState) -> bool:
    """Check if goal is completed."""
    return state.score >= 1.0 or state.goal_status == "completed"


def is_stalled(state: SupervisorState) -> bool:
    """Check if progress has stalled."""
    return state.stall_count >= 2


def has_more_steps(state: SupervisorState) -> bool:
    """Check if there are more plan steps."""
    return state.current_step < state.total_steps


def needs_evolution(state: SupervisorState) -> bool:
    """Check if strategy evolution is needed."""
    return state.stall_count >= state.max_stalls


def always_continue(state: SupervisorState) -> bool:
    """Always continue."""
    return True


# ---------------------------------------------------------------------------
# Default graph builder
# ---------------------------------------------------------------------------

def build_default_graph(
    plan_handler: Callable,
    dispatch_handler: Callable,
    monitor_handler: Callable,
    adjust_handler: Callable,
    evolve_handler: Callable,
) -> LangGraphSkeleton:
    """Build the default supervisor graph with all nodes and edges."""
    graph = LangGraphSkeleton()

    # Register nodes
    graph.register_node(NodeName.PLAN.value, plan_handler)
    graph.register_node(NodeName.DISPATCH.value, dispatch_handler)
    graph.register_node(NodeName.MONITOR.value, monitor_handler)
    graph.register_node(NodeName.ADJUST.value, adjust_handler)
    graph.register_node(NodeName.EVOLVE.value, evolve_handler)

    # Register edges
    # plan → dispatch (always)
    graph.register_edge(NodeName.PLAN.value, EdgeCondition.CONTINUE.value, NodeName.DISPATCH.value, always_continue)

    # dispatch → monitor (always)
    graph.register_edge(NodeName.DISPATCH.value, EdgeCondition.CONTINUE.value, NodeName.MONITOR.value, always_continue)

    # monitor → complete (if done)
    graph.register_edge(NodeName.MONITOR.value, EdgeCondition.COMPLETED.value, NodeName.COMPLETE.value, is_completed)

    # monitor → evolve (if stalled too long)
    graph.register_edge(NodeName.MONITOR.value, EdgeCondition.NEEDS_EVOLUTION.value, NodeName.EVOLVE.value, needs_evolution)

    # monitor → adjust (if stalled)
    graph.register_edge(NodeName.MONITOR.value, EdgeCondition.STALLED.value, NodeName.ADJUST.value, is_stalled)

    # monitor → dispatch (if more steps)
    graph.register_edge(NodeName.MONITOR.value, EdgeCondition.CONTINUE.value, NodeName.DISPATCH.value, has_more_steps)

    # adjust → dispatch (always)
    graph.register_edge(NodeName.ADJUST.value, EdgeCondition.CONTINUE.value, NodeName.DISPATCH.value, always_continue)

    # evolve → dispatch (always)
    graph.register_edge(NodeName.EVOLVE.value, EdgeCondition.CONTINUE.value, NodeName.DISPATCH.value, always_continue)

    return graph
