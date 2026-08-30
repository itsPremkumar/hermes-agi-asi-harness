"""Mesh Visualizer — visualize the agent mesh topology."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LayoutType(str, Enum):
    CIRCULAR = "circular"
    GRID = "grid"
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"


@dataclass
class VisualNode:
    id: str
    label: str
    x: float = 0.0
    y: float = 0.0
    color: str = "#38bdf8"
    size: float = 10.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualEdge:
    id: str
    source: str
    target: str
    weight: float = 1.0
    color: str = "#64748b"
    metadata: dict[str, Any] = field(default_factory=dict)


class MeshVisualizer:
    """Visualize mesh topology."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._nodes: dict[str, VisualNode] = {}
        self._edges: list[VisualEdge] = []

    def add_node(self, label: str, x: float = 0.0, y: float = 0.0, color: str = "#38bdf8", size: float = 10.0) -> VisualNode:
        node = VisualNode(id=str(uuid.uuid4()), label=label, x=x, y=y, color=color, size=size)
        self._nodes[node.id] = node
        return node

    def add_edge(self, source: str, target: str, weight: float = 1.0) -> VisualEdge:
        edge = VisualEdge(id=str(uuid.uuid4()), source=source, target=target, weight=weight)
        self._edges.append(edge)
        return edge

    def list_nodes(self) -> list[VisualNode]:
        return list(self._nodes.values())

    def list_edges(self) -> list[VisualEdge]:
        return list(self._edges)

    def layout_circular(self, radius: float = 100.0) -> None:
        import math
        nodes = list(self._nodes.values())
        n = len(nodes)
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / n if n > 1 else 0
            node.x = radius * math.cos(angle)
            node.y = radius * math.sin(angle)

    def layout_grid(self, spacing: float = 50.0) -> None:
        import math
        nodes = list(self._nodes.values())
        cols = math.ceil(math.sqrt(len(nodes)))
        for i, node in enumerate(nodes):
            node.x = (i % cols) * spacing
            node.y = (i // cols) * spacing

    def count_nodes(self) -> int:
        return len(self._nodes)

    def count_edges(self) -> int:
        return len(self._edges)

    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()
