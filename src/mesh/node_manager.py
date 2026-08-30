"""Node Manager — manage agent nodes in the distributed mesh."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class MeshNode:
    id: str
    name: str
    address: str
    status: NodeStatus = NodeStatus.OFFLINE
    capacity: int = 1
    load: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class NodeManager:
    """Manage agent nodes in the distributed mesh."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._nodes: dict[str, MeshNode] = {}

    def register(self, name: str, address: str, capacity: int = 1) -> MeshNode:
        node = MeshNode(id=str(uuid.uuid4()), name=name, address=address, capacity=capacity)
        self._nodes[node.id] = node
        return node

    def unregister(self, node_id: str) -> bool:
        return self._nodes.pop(node_id, None) is not None

    def get(self, node_id: str) -> MeshNode | None:
        return self._nodes.get(node_id)

    def list_all(self) -> list[MeshNode]:
        return list(self._nodes.values())

    def list_online(self) -> list[MeshNode]:
        return [n for n in self._nodes.values() if n.status == NodeStatus.ONLINE]

    def set_status(self, node_id: str, status: NodeStatus) -> bool:
        if node_id in self._nodes:
            self._nodes[node_id].status = status
            return True
        return False

    def assign_task(self, node_id: str) -> bool:
        if node_id in self._nodes and self._nodes[node_id].load < self._nodes[node_id].capacity:
            self._nodes[node_id].load += 1
            return True
        return False

    def complete_task(self, node_id: str) -> bool:
        if node_id in self._nodes and self._nodes[node_id].load > 0:
            self._nodes[node_id].load -= 1
            return True
        return False

    def count(self) -> int:
        return len(self._nodes)
