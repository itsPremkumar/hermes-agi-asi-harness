"""LangGraph State Graph implementation."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.harness.errors import GraphError, NodeError, DeadLetterQueue, CircuitBreaker, make_retry_decorator

logger = logging.getLogger(__name__)


@dataclass
class State:
    """Graph state container."""

    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)
    step: int = 0

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, updates: dict[str, Any]) -> None:
        self.data.update(updates)

    def add_error(self, node_id: str, message: str) -> None:
        self.errors.append({"node_id": node_id, "message": message})

    def fork(self) -> State:
        import copy
        return copy.deepcopy(self)


NodeFunc = Callable[[State], State]
EdgeFunc = Callable[[State], str]


@dataclass
class Node:
    """A graph node."""

    id: str
    func: NodeFunc
    description: str = ""
    retry_count: int = 0
    max_retries: int = 3
    circuit_breaker: Optional[CircuitBreaker] = None

    def execute(self, state: State) -> State:
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                if self.circuit_breaker and not self.circuit_breaker.allow_request():
                    from .errors import CircuitBreakerOpenError
                    raise CircuitBreakerOpenError(f"Circuit open for node {self.id}")
                return self.func(state)
            except NodeError:
                raise
            except Exception as e:
                last_error = e
                self.retry_count += 1
                logger.warning(f"Node {self.id} attempt {attempt + 1} failed: {e}")
        raise NodeError(
            f"Node {self.id} failed after {self.max_retries + 1} attempts: {last_error}",
            node_id=self.id,
        )


@dataclass
class Edge:
    """A graph edge."""

    source: str
    target: str
    condition: Optional[EdgeFunc] = None
    description: str = ""

    def resolve(self, state: State) -> Optional[str]:
        if self.condition is None:
            return self.target
        try:
            result = self.condition(state)
            if isinstance(result, str):
                return result
            if result:
                return self.target
            return None
        except Exception as e:
            logger.error(f"Edge {self.source}->{self.target} condition error: {e}")
            return None


class Graph:
    """LangGraph-style state graph."""

    def __init__(self, name: str = "graph") -> None:
        self.name = name
        self.id = str(uuid.uuid4())[:8]
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.entry_point: Optional[str] = None
        self._dead_letter_queue = DeadLetterQueue()
        self._circuit_breaker = CircuitBreaker()

    def add_node(self, node_id: str, func: NodeFunc, description: str = "") -> Node:
        node = Node(id=node_id, func=func, description=description)
        self.nodes[node_id] = node
        if self.entry_point is None:
            self.entry_point = node_id
        return node

    def add_edge(self, source: str, target: str, condition: Optional[EdgeFunc] = None, description: str = "") -> Edge:
        edge = Edge(source=source, target=target, condition=condition, description=description)
        self.edges.append(edge)
        return edge

    def set_entry_point(self, node_id: str) -> None:
        if node_id not in self.nodes:
            raise GraphError(f"Unknown node: {node_id}", graph_id=self.id)
        self.entry_point = node_id

    def get_outgoing(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.source == node_id]

    def execute(self, initial_state: Optional[State] = None, max_steps: int = 100) -> State:
        if initial_state is None:
            state = State()
        else:
            state = initial_state.fork()

        if self.entry_point is None:
            raise GraphError("No entry point set", graph_id=self.id)

        current_node_id = self.entry_point
        visited = set()

        for step in range(max_steps):
            state.step = step
            if current_node_id is None:
                break
            if current_node_id in visited and current_node_id != "__end__":
                logger.warning(f"Cycle detected at node {current_node_id}")
            visited.add(current_node_id)

            if current_node_id == "__end__":
                break

            node = self.nodes.get(current_node_id)
            if node is None:
                raise GraphError(f"Unknown node: {current_node_id}", graph_id=self.id)

            try:
                state = node.execute(state)
            except NodeError as e:
                self._dead_letter_queue.enqueue(current_node_id, e, payload=state.data)
                state.add_error(current_node_id, str(e))
                raise GraphError(
                    f"Node {current_node_id} failed: {e}",
                    graph_id=self.id,
                ) from e

            outgoing = self.get_outgoing(current_node_id)
            next_node_id = None
            for edge in outgoing:
                resolved = edge.resolve(state)
                if resolved is not None:
                    next_node_id = resolved
                    break
            current_node_id = next_node_id

        return state

    @property
    def dead_letter_queue(self) -> DeadLetterQueue:
        return self._dead_letter_queue

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker


def create_avopisaging_graph() -> Graph:
    """Create the AVOPISAging workflow graph with cyclic edges."""
    graph = Graph(name="avopisaging")

    def assess(state: State) -> State:
        state.set("assessment", {"status": "complete", "score": 0.85})
        return state

    def validate(state: State) -> State:
        score = state.get("assessment", {}).get("score", 0)
        state.set("validation", {"passed": score >= 0.7})
        return state

    def optimize(state: State) -> State:
        state.set("optimization", {"iterations": 3, "improvement": 0.12})
        return state

    def implement(state: State) -> State:
        state.set("implementation", {"status": "deployed"})
        return state

    def protect(state: State) -> State:
        state.set("protection", {"active": True})
        return state

    def iterate(state: State) -> State:
        state.set("iteration_count", state.get("iteration_count", 0) + 1)
        return state

    graph.add_node("assess", assess, "Assess current state")
    graph.add_node("validate", validate, "Validate assessment")
    graph.add_node("optimize", optimize, "Optimize based on validation")
    graph.add_node("implement", implement, "Implement changes")
    graph.add_node("protect", protect, "Apply protection mechanisms")
    graph.add_node("iterate", iterate, "Iterate cycle")

    graph.add_edge("assess", "validate")
    graph.add_edge("validate", "optimize", condition=lambda s: s.get("validation", {}).get("passed", False))
    graph.add_edge("validate", "assess", condition=lambda s: not s.get("validation", {}).get("passed", True))
    graph.add_edge("optimize", "implement")
    graph.add_edge("implement", "protect")
    graph.add_edge("protect", "iterate")
    graph.add_edge("iterate", "assess", condition=lambda s: s.get("iteration_count", 0) < 5)
    graph.add_edge("iterate", "__end__", condition=lambda s: s.get("iteration_count", 0) >= 5)

    graph.set_entry_point("assess")
    return graph
