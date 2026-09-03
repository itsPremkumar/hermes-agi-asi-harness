"""GraphGate — knowledge graph management."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    CONCEPT = "concept"
    ENTITY = "entity"
    EVENT = "event"
    RULE = "rule"


@dataclass
class GraphNode:
    id: str
    name: str
    node_type: NodeType
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    relation: str
    metadata: dict[str, Any] = field(default_factory=dict)


class GraphGate:
    """Manage knowledge graphs."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []

    def add_node(self, name: str, node_type: NodeType, metadata: dict[str, Any] | None = None) -> GraphNode:
        node = GraphNode(id=str(uuid.uuid4()), name=name, node_type=node_type, metadata=metadata or {})
        self._nodes[node.id] = node
        return node

    def add_edge(self, source: str, target: str, relation: str) -> GraphEdge:
        edge = GraphEdge(id=str(uuid.uuid4()), source=source, target=target, relation=relation)
        self._edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def list_nodes(self) -> list[GraphNode]:
        return list(self._nodes.values())

    def list_edges(self) -> list[GraphEdge]:
        return list(self._edges)

    def search(self, query: str) -> list[GraphNode]:
        q = query.lower()
        return [n for n in self._nodes.values() if q in n.name.lower()]

    def count_nodes(self) -> int:
        return len(self._nodes)

    def count_edges(self) -> int:
        return len(self._edges)
