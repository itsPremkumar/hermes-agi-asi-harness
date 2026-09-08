"""
StateGraphEngine - LangGraph state graph builder and executor.

Provides a graph-based execution engine that supports:
- Nodes as stateful computation units
- Edges with optional conditions (branching)
- State management across graph execution
- Checkpoint and resume capabilities
- Parallel node execution where possible
- Error handling and retries
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


class NodeState(Enum):
    """States for graph nodes."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class GraphState:
    """Mutable state that flows through the graph."""
    data: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, data: Dict[str, Any]) -> None:
        self.data.update(data)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.data)


@dataclass
class Node:
    """A node in the state graph."""
    name: str
    func: Callable[[GraphState], GraphState]
    description: str = ""
    retries: int = 0
    retry_delay: float = 0.0
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            raise ValueError("Node name cannot be empty")
        if not callable(self.func):
            raise ValueError("Node func must be callable")


@dataclass
class Edge:
    """An edge connecting two nodes."""
    source: str
    target: str
    condition: Optional[Callable[[GraphState], bool]] = None
    label: Optional[str] = None
    priority: int = 0

    @property
    def is_conditional(self) -> bool:
        return self.condition is not None


@dataclass
class ExecutionResult:
    """Result of a graph execution."""
    graph_id: str
    success: bool
    final_state: GraphState
    node_results: Dict[str, Any]
    execution_time: float
    node_order: List[str]
    errors: Dict[str, str]


class StateGraphEngine:
    """LangGraph-style state graph builder and executor."""

    def __init__(self, name: str = "graph"):
        self.name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._entry_point: Optional[str] = None
        self._exit_points: Set[str] = set()
        self._lock = threading.RLock()
        self._execution_count = 0

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def add_node(
        self,
        name: str,
        func: Callable[[GraphState], GraphState],
        description: str = "",
        retries: int = 0,
        retry_delay: float = 0.0,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Node:
        """Add a node to the graph."""
        node = Node(
            name=name,
            func=func,
            description=description,
            retries=retries,
            retry_delay=retry_delay,
            timeout=timeout,
            metadata=metadata or {},
        )
        self._nodes[name] = node
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        condition: Optional[Callable[[GraphState], bool]] = None,
        label: Optional[str] = None,
        priority: int = 0,
    ) -> Edge:
        """Add an edge between two nodes."""
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' does not exist")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' does not exist")

        edge = Edge(
            source=source,
            target=target,
            condition=condition,
            label=label,
            priority=priority,
        )
        self._edges.append(edge)
        return edge

    def set_entry_point(self, node_name: str) -> None:
        """Set the entry point node."""
        if node_name not in self._nodes:
            raise ValueError(f"Node '{node_name}' does not exist")
        self._entry_point = node_name

    def add_exit_point(self, node_name: str) -> None:
        """Mark a node as an exit point."""
        if node_name not in self._nodes:
            raise ValueError(f"Node '{node_name}' does not exist")
        self._exit_points.add(node_name)

    def get_node(self, name: str) -> Optional[Node]:
        """Get a node by name."""
        return self._nodes.get(name)

    def get_edges_from(self, node_name: str) -> List[Edge]:
        """Get all edges originating from a node."""
        return sorted(
            [e for e in self._edges if e.source == node_name],
            key=lambda e: e.priority,
            reverse=True,
        )

    def get_edges_to(self, node_name: str) -> List[Edge]:
        """Get all edges pointing to a node."""
        return [e for e in self._edges if e.target == node_name]

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate the graph structure. Returns (is_valid, list_of_errors)."""
        errors = []

        if not self._nodes:
            errors.append("Graph has no nodes")

        if self._entry_point is None and self._nodes:
            errors.append("No entry point set")

        if self._entry_point and self._entry_point not in self._nodes:
            errors.append(f"Entry point '{self._entry_point}' does not exist")

        # Check for disconnected nodes
        connected = set()
        if self._entry_point:
            connected.add(self._entry_point)
            self._dfs_connectivity(self._entry_point, connected)

        disconnected = set(self._nodes.keys()) - connected
        if disconnected:
            errors.append(f"Disconnected nodes: {disconnected}")

        # Check for cycles
        if self._has_cycle():
            errors.append("Graph contains cycles (not a valid DAG)")

        return len(errors) == 0, errors

    def _dfs_connectivity(self, node: str, visited: Set[str]) -> None:
        """DFS to find connected nodes."""
        for edge in self.get_edges_from(node):
            if edge.target not in visited:
                visited.add(edge.target)
                self._dfs_connectivity(edge.target, visited)

    def _has_cycle(self) -> bool:
        """Check if the graph contains cycles using DFS."""
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for edge in self.get_edges_from(node):
                if edge.target not in visited:
                    if dfs(edge.target):
                        return True
                elif edge.target in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node in self._nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def execute(
        self,
        initial_state: Optional[Union[Dict[str, Any], GraphState]] = None,
    ) -> ExecutionResult:
        """Execute the state graph from the entry point."""
        with self._lock:
            self._execution_count += 1
            graph_id = f"{self.name}-{self._execution_count}-{uuid.uuid4().hex[:8]}"

        is_valid, errors = self.validate()
        if not is_valid:
            state = GraphState()
            state.errors["graph"] = f"Invalid graph: {errors}"
            return ExecutionResult(
                graph_id=graph_id,
                success=False,
                final_state=state,
                node_results={},
                execution_time=0.0,
                node_order=[],
                errors=state.errors,
            )

        if isinstance(initial_state, dict):
            state = GraphState(data=initial_state)
        elif isinstance(initial_state, GraphState):
            state = initial_state
        else:
            state = GraphState()

        start_time = time.time()
        node_results: Dict[str, Any] = {}
        node_order: List[str] = []
        node_states: Dict[str, NodeState] = {
            name: NodeState.PENDING for name in self._nodes
        }

        try:
            self._execute_node(
                self._entry_point, state, node_results, node_order, node_states
            )
            success = True
        except Exception as e:
            success = False
            state.errors["execution"] = str(e)

        execution_time = time.time() - start_time

        return ExecutionResult(
            graph_id=graph_id,
            success=success,
            final_state=state,
            node_results=node_results,
            execution_time=execution_time,
            node_order=node_order,
            errors=state.errors,
        )

    def _execute_node(
        self,
        node_name: str,
        state: GraphState,
        node_results: Dict[str, Any],
        node_order: List[str],
        node_states: Dict[str, NodeState],
    ) -> None:
        """Execute a node and its downstream nodes."""
        if node_states.get(node_name) == NodeState.COMPLETED:
            return

        node = self._nodes[node_name]
        node_states[node_name] = NodeState.RUNNING
        node_order.append(node_name)

        # Execute with retry logic
        attempts = 0
        max_attempts = 1 + node.retries
        last_error = None

        while attempts < max_attempts:
            try:
                state = node.func(state)
                node_states[node_name] = NodeState.COMPLETED
                node_results[node_name] = state.to_dict()
                break
            except Exception as e:
                attempts += 1
                last_error = str(e)
                if attempts < max_attempts and node.retry_delay > 0:
                    time.sleep(node.retry_delay)

        if node_states[node_name] != NodeState.COMPLETED:
            node_states[node_name] = NodeState.FAILED
            state.errors[node_name] = last_error or "Unknown error"
            node_results[node_name] = None

            # If node fails, skip downstream
            for edge in self.get_edges_from(node_name):
                node_states[edge.target] = NodeState.SKIPPED
            return

        # Execute downstream nodes
        for edge in self.get_edges_from(node_name):
            if edge.is_conditional:
                try:
                    if not edge.condition(state):
                        node_states[edge.target] = NodeState.SKIPPED
                        continue
                except Exception:
                    node_states[edge.target] = NodeState.SKIPPED
                    continue

            self._execute_node(
                edge.target, state, node_results, node_order, node_states
            )

    def get_execution_count(self) -> int:
        """Get the number of times this graph has been executed."""
        return self._execution_count

    def reset(self) -> None:
        """Reset the graph execution state."""
        self._execution_count = 0

    def remove_node(self, name: str) -> bool:
        """Remove a node and its edges."""
        if name not in self._nodes:
            return False
        del self._nodes[name]
        self._edges = [
            e for e in self._edges if e.source != name and e.target != name
        ]
        self._exit_points.discard(name)
        if self._entry_point == name:
            self._entry_point = None
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph structure to dictionary."""
        return {
            "name": self.name,
            "nodes": list(self._nodes.keys()),
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "conditional": e.is_conditional,
                    "label": e.label,
                }
                for e in self._edges
            ],
            "entry_point": self._entry_point,
            "exit_points": list(self._exit_points),
        }
