"""MCPHub — Model Context Protocol server hub."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ServerStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class MCPServer:
    id: str
    name: str
    description: str
    status: ServerStatus = ServerStatus.STOPPED
    tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MCPHub:
    """Manage MCP servers."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._servers: dict[str, MCPServer] = {}

    def register(self, name: str, description: str = "", tools: list[str] | None = None) -> MCPServer:
        server = MCPServer(id=str(uuid.uuid4()), name=name, description=description, tools=tools or [])
        self._servers[server.id] = server
        return server

    def unregister(self, server_id: str) -> bool:
        return self._servers.pop(server_id, None) is not None

    def get(self, server_id: str) -> MCPServer | None:
        return self._servers.get(server_id)

    def list_all(self) -> list[MCPServer]:
        return list(self._servers.values())

    def start(self, server_id: str) -> bool:
        if server_id in self._servers:
            self._servers[server_id].status = ServerStatus.RUNNING
            return True
        return False

    def stop(self, server_id: str) -> bool:
        if server_id in self._servers:
            self._servers[server_id].status = ServerStatus.STOPPED
            return True
        return False

    def search(self, query: str) -> list[MCPServer]:
        q = query.lower()
        return [s for s in self._servers.values() if q in s.name.lower()]

    def count(self) -> int:
        return len(self._servers)
