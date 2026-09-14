"""Agent Coordination Protocols for the AI/ML Knowledge Graph.

Defines how AI agents interact with the KG, register capabilities,
and coordinate work across verticals.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from kg import KGNode, KGEdge, Vertical, NodeType, EdgeType, add_node_to_graph, add_edge_to_graph, nx


class AgentRole(str, Enum):
    """Roles agents can take in the multi-agent system."""

    GRAPH_BUILDER = "graph_builder"
    VALIDATOR = "validator"
    QUERY_ENGINE = "query_engine"
    ORCHESTRATOR = "orchestrator"
    LEARNER = "learner"
    CURATOR = "curator"


class AgentCapability(str, Enum):
    """Capabilities an agent can register."""

    NODE_CREATION = "node_creation"
    NODE_VALIDATION = "node_validation"
    EDGE_CREATION = "edge_creation"
    GRAPH_QUERY = "graph_query"
    VERTICAL_EXPERTISE = "vertical_expertise"
    CONFLICT_RESOLUTION = "conflict_resolution"
    SCHEMA_EVOLUTION = "schema_evolution"


class CoordinationMessage(BaseModel):
    """A message passed between agents."""

    sender: str = Field(..., description="Sending agent id")
    recipient: str = Field(..., description="Recipient agent id, or 'broadcast'")
    action: str = Field(..., description="Action requested")
    payload: dict[str, Any] = Field(default_factory=dict)
    trace_id: str = Field(default="", description="Distributed tracing id")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class AgentRegistration(BaseModel):
    """An agent registering with the coordination system."""

    agent_id: str = Field(..., description="Unique agent identifier")
    role: AgentRole = Field(..., description="Agent's primary role")
    capabilities: list[AgentCapability] = Field(default_factory=list)
    assigned_verticals: list[Vertical] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConflictResolutionStrategy(str, Enum):
    """How to resolve conflicts between agent edits."""

    LAST_WRITER_WINS = "last_writer_wins"
    VOTE_BASED = "vote_based"
    HUMAN_REVIEW = "human_review"
    SEMANTIC_MERGE = "semantic_merge"


# Protocol interfaces

class AgentInterface(Protocol):
    """Protocol that all KG agents must implement."""

    @property
    def agent_id(self) -> str: ...
    @property
    def role(self) -> AgentRole: ...
    def can_handle(self, action: str) -> bool: ...
    def handle(self, message: CoordinationMessage) -> dict[str, Any]: ...


class GraphOperations(Protocol):
    """Protocol for graph CRUD operations."""

    def add_node(self, node: KGNode) -> list[str]: ...
    def add_edge(self, edge: KGEdge) -> list[str]: ...
    def query(self, query: str) -> list[dict[str, Any]]: ...
    def validate(self) -> list[str]: ...


# Built-in agent implementations

class GraphBuilderAgent:
    """Agent responsible for constructing and extending the knowledge graph."""

    def __init__(self, agent_id: str, graph: nx.DiGraph):
        self._agent_id = agent_id
        self._graph = graph
        self._role = AgentRole.GRAPH_BUILDER

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def role(self) -> AgentRole:
        return self._role

    def can_handle(self, action: str) -> bool:
        return action in {"add_node", "add_edge", "bulk_import"}

    def handle(self, message: CoordinationMessage) -> dict[str, Any]:
        if message.action == "add_node":
            node = KGNode(**message.payload.get("node", {}))
            errors = add_node_to_graph(self._graph, node)
            return {"status": "ok" if not errors else "error", "errors": errors}
        if message.action == "add_edge":
            edge = KGEdge(**message.payload.get("edge", {}))
            errors = add_edge_to_graph(self._graph, edge)
            return {"status": "ok" if not errors else "error", "errors": errors}
        return {"status": "error", "errors": [f"Unknown action: {message.action}"]}


class ValidatorAgent:
    """Agent responsible for validating graph integrity."""

    def __init__(self, agent_id: str, graph: nx.DiGraph):
        self._agent_id = agent_id
        self._graph = graph
        self._role = AgentRole.VALIDATOR

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def role(self) -> AgentRole:
        return self._role

    def can_handle(self, action: str) -> bool:
        return action in {"validate_graph", "check_vertical", "find_cycles"}

    def handle(self, message: CoordinationMessage) -> dict[str, Any]:
        if message.action == "validate_graph":
            errors = self._validate_graph()
            return {"status": "ok" if not errors else "error", "errors": errors}
        if message.action == "check_vertical":
            vertical = Vertical(message.payload.get("vertical", ""))
            count = sum(
                1 for _, d in self._graph.nodes(data=True)
                if d.get("vertical") == vertical.value
            )
            return {"status": "ok", "vertical": vertical.value, "node_count": count}
        if message.action == "find_cycles":
            try:
                cycles = list(nx.simple_cycles(self._graph))
                return {"status": "ok", "cycle_count": len(cycles), "cycles": cycles[:10]}
            except Exception as e:
                return {"status": "error", "errors": [str(e)]}
        return {"status": "error", "errors": [f"Unknown action: {message.action}"]}

    def _validate_graph(self) -> list[str]:
        errors: list[str] = []
        for node_id, data in self._graph.nodes(data=True):
            if "vertical" not in data:
                errors.append(f"Node '{node_id}' missing 'vertical'")
            if "node_type" not in data:
                errors.append(f"Node '{node_id}' missing 'node_type'")
        for src, tgt, data in self._graph.edges(data=True):
            if "edge_type" not in data:
                errors.append(f"Edge '{src}' -> '{tgt}' missing 'edge_type'")
        return errors


class QueryEngineAgent:
    """Agent responsible for answering questions about the knowledge graph."""

    def __init__(self, agent_id: str, graph: nx.DiGraph):
        self._agent_id = agent_id
        self._graph = graph
        self._role = AgentRole.QUERY_ENGINE

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def role(self) -> AgentRole:
        return self._role

    def can_handle(self, action: str) -> bool:
        return action in {"query_nodes", "query_edges", "shortest_path", "get_verticals"}

    def handle(self, message: CoordinationMessage) -> dict[str, Any]:
        if message.action == "query_nodes":
            vertical = message.payload.get("vertical", "")
            node_type = message.payload.get("node_type", "")
            results = []
            for nid, data in self._graph.nodes(data=True):
                if vertical and data.get("vertical") != vertical:
                    continue
                if node_type and data.get("node_type") != node_type:
                    continue
                results.append(data)
            return {"status": "ok", "count": len(results), "nodes": results}

        if message.action == "query_edges":
            edge_type = message.payload.get("edge_type", "")
            results = []
            for src, tgt, data in self._graph.edges(data=True):
                if edge_type and data.get("edge_type") != edge_type:
                    continue
                results.append({"source": src, "target": tgt, **data})
            return {"status": "ok", "count": len(results), "edges": results}

        if message.action == "shortest_path":
            source = message.payload.get("source", "")
            target = message.payload.get("target", "")
            try:
                path = nx.shortest_path(self._graph, source=source, target=target)
                return {"status": "ok", "path": path, "length": len(path) - 1}
            except nx.NetworkXNoPath:
                return {"status": "error", "errors": [f"No path from '{source}' to '{target}'"]}
            except nx.NodeNotFound as e:
                return {"status": "error", "errors": [str(e)]}

        if message.action == "get_verticals":
            from kg import get_vertical_summary
            return {"status": "ok", "verticals": get_vertical_summary(self._graph)}

        return {"status": "error", "errors": [f"Unknown action: {message.action}"]}


# Protocol factory

def create_agent_registry() -> dict[str, AgentInterface]:
    """Create an empty agent registry."""
    return {}


def register_agent(
    registry: dict[str, AgentInterface],
    agent: AgentInterface,
) -> bool:
    """Register an agent. Returns False if agent_id already registered."""
    if agent.agent_id in registry:
        return False
    registry[agent.agent_id] = agent
    return True


def dispatch_message(
    registry: dict[str, AgentInterface],
    message: CoordinationMessage,
) -> dict[str, Any]:
    """Dispatch a message to the appropriate agent."""
    if message.recipient == "broadcast":
        results = {}
        for agent_id, agent in registry.items():
            if agent.can_handle(message.action):
                results[agent_id] = agent.handle(message)
        return {"status": "broadcast", "results": results}

    if message.recipient not in registry:
        return {"status": "error", "errors": [f"Unknown recipient: '{message.recipient}'"]}

    agent = registry[message.recipient]
    if not agent.can_handle(message.action):
        return {"status": "error", "errors": [f"Agent '{agent.agent_id}' cannot handle '{message.action}'"]}

    return agent.handle(message)
