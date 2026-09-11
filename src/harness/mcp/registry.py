"""MCPRegistry — server registration, health tracking, capability discovery.

The registry maintains a catalog of MCP servers and their capabilities.
It tracks server status, exposes tool discovery, and provides health metrics.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class ServerStatus(Enum):
    """Possible states for a registered MCP server."""
    UNKNOWN = "unknown"
    CONNECTING = "connecting"
    READY = "ready"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    DISABLED = "disabled"


@dataclass
class MCPServerInfo:
    """Information about a registered MCP server."""
    server_id: str
    name: str
    transport: str  # "stdio" | "http"
    endpoint: str  # command for stdio, URL for http
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    status: ServerStatus = ServerStatus.UNKNOWN
    registered_at: float = field(default_factory=time.time)
    last_health_check: Optional[float] = None
    health_check_failures: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)

    @property
    def is_available(self) -> bool:
        return self.status in (ServerStatus.READY, ServerStatus.DEGRADED)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.registered_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server_id": self.server_id,
            "name": self.name,
            "transport": self.transport,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
            "tools": self.tools,
            "status": self.status.value,
            "registered_at": self.registered_at,
            "last_health_check": self.last_health_check,
            "health_check_failures": self.health_check_failures,
            "metadata": self.metadata,
            "tags": list(self.tags),
        }


class MCPRegistry:
    """Central registry for MCP servers and their capabilities.

    Thread-safe. Supports registration, deregistration, health tracking,
    capability discovery, and event callbacks.
    """

    def __init__(self):
        self._servers: Dict[str, MCPServerInfo] = {}
        self._name_index: Dict[str, str] = {}  # name -> server_id
        self._tool_index: Dict[str, Set[str]] = defaultdict(set)  # tool -> {server_id}
        self._capability_index: Dict[str, Set[str]] = defaultdict(set)  # cap -> {server_id}
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)  # tag -> {server_id}
        self._lock = threading.RLock()
        self._status_callbacks: List[Callable[[str, ServerStatus, ServerStatus], None]] = []
        self._registry_id = f"registry-{uuid.uuid4().hex[:12]}"

    @property
    def registry_id(self) -> str:
        return self._registry_id

    @property
    def server_count(self) -> int:
        return len(self._servers)

    # -- Registration -------------------------------------------------------

    def register(
        self,
        name: str,
        transport: str,
        endpoint: str,
        capabilities: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None,
        server_id: Optional[str] = None,
    ) -> MCPServerInfo:
        """Register a new MCP server."""
        with self._lock:
            if name in self._name_index:
                raise ValueError(f"Server with name '{name}' already registered")

            if server_id is None:
                server_id = f"mcp-{uuid.uuid4().hex[:12]}"

            if server_id in self._servers:
                raise ValueError(f"Server with id '{server_id}' already exists")

            info = MCPServerInfo(
                server_id=server_id,
                name=name,
                transport=transport,
                endpoint=endpoint,
                capabilities=list(capabilities or []),
                tools=list(tools or []),
                metadata=dict(metadata or {}),
                tags=set(tags or []),
            )

            self._servers[server_id] = info
            self._name_index[name] = server_id

            for tool in info.tools:
                self._tool_index[tool].add(server_id)
            for cap in info.capabilities:
                self._capability_index[cap].add(server_id)
            for tag in info.tags:
                self._tag_index[tag].add(server_id)

            return info

    def deregister(self, server_id: str) -> bool:
        """Remove a server from the registry."""
        with self._lock:
            info = self._servers.pop(server_id, None)
            if info is None:
                return False

            self._name_index.pop(info.name, None)

            for tool in info.tools:
                self._tool_index[tool].discard(server_id)
                if not self._tool_index[tool]:
                    del self._tool_index[tool]

            for cap in info.capabilities:
                self._capability_index[cap].discard(server_id)
                if not self._capability_index[cap]:
                    del self._capability_index[cap]

            for tag in info.tags:
                self._tag_index[tag].discard(server_id)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

            return True

    # -- Lookup -------------------------------------------------------------

    def get(self, server_id: str) -> Optional[MCPServerInfo]:
        """Get server info by ID."""
        return self._servers.get(server_id)

    def get_by_name(self, name: str) -> Optional[MCPServerInfo]:
        """Get server info by name."""
        sid = self._name_index.get(name)
        return self._servers.get(sid) if sid else None

    def get_all(self) -> List[MCPServerInfo]:
        """Get all registered servers."""
        return list(self._servers.values())

    def get_available(self) -> List[MCPServerInfo]:
        """Get all available (ready/degraded) servers."""
        return [s for s in self._servers.values() if s.is_available]

    def get_by_status(self, status: ServerStatus) -> List[MCPServerInfo]:
        """Get all servers with a specific status."""
        return [s for s in self._servers.values() if s.status == status]

    def get_by_tag(self, tag: str) -> List[MCPServerInfo]:
        """Get all servers with a specific tag."""
        ids = self._tag_index.get(tag, set())
        return [self._servers[sid] for sid in ids if sid in self._servers]

    def get_by_capability(self, capability: str) -> List[MCPServerInfo]:
        """Get all servers that advertise a specific capability."""
        ids = self._capability_index.get(capability, set())
        return [self._servers[sid] for sid in ids if sid in self._servers]

    # -- Tool Discovery -----------------------------------------------------

    def find_servers_for_tool(self, tool_name: str) -> List[MCPServerInfo]:
        """Find all servers that provide a specific tool."""
        ids = self._tool_index.get(tool_name, set())
        return [self._servers[sid] for sid in ids if sid in self._servers]

    def find_available_servers_for_tool(self, tool_name: str) -> List[MCPServerInfo]:
        """Find available servers that provide a specific tool."""
        return [s for s in self.find_servers_for_tool(tool_name) if s.is_available]

    def list_all_tools(self) -> Dict[str, List[str]]:
        """Return a mapping of tool_name -> list of server names."""
        result: Dict[str, List[str]] = {}
        for tool, sids in self._tool_index.items():
            result[tool] = [self._servers[sid].name for sid in sids if sid in self._servers]
        return result

    def list_all_capabilities(self) -> Dict[str, List[str]]:
        """Return a mapping of capability -> list of server names."""
        result: Dict[str, List[str]] = {}
        for cap, sids in self._capability_index.items():
            result[cap] = [self._servers[sid].name for sid in sids if sid in self._servers]
        return result

    # -- Health Tracking ----------------------------------------------------

    def update_status(
        self,
        server_id: str,
        new_status: ServerStatus,
        record_check: bool = True,
    ) -> bool:
        """Update the status of a server."""
        with self._lock:
            info = self._servers.get(server_id)
            if info is None:
                return False

            old_status = info.status
            info.status = new_status

            if record_check:
                info.last_health_check = time.time()
                if new_status in (ServerStatus.UNREACHABLE,):
                    info.health_check_failures += 1
                elif new_status == ServerStatus.READY:
                    info.health_check_failures = 0

        # Fire callbacks outside lock
        if old_status != new_status:
            for cb in self._status_callbacks:
                try:
                    cb(server_id, old_status, new_status)
                except Exception:
                    pass

        return True

    def record_health_check(self, server_id: str, success: bool) -> bool:
        """Record a health check result."""
        status = ServerStatus.READY if success else ServerStatus.UNREACHABLE
        return self.update_status(server_id, status, record_check=True)

    def on_status_change(
        self, callback: Callable[[str, ServerStatus, ServerStatus], None]
    ) -> None:
        """Register a callback for status changes: fn(server_id, old, new)."""
        self._status_callbacks.append(callback)

    # -- Capability Updates -------------------------------------------------

    def update_tools(self, server_id: str, tools: List[str]) -> bool:
        """Update the tool list for a server."""
        with self._lock:
            info = self._servers.get(server_id)
            if info is None:
                return False

            # Remove old tool mappings
            for tool in info.tools:
                self._tool_index[tool].discard(server_id)
                if not self._tool_index[tool]:
                    del self._tool_index[tool]

            info.tools = list(tools)

            # Add new tool mappings
            for tool in info.tools:
                self._tool_index[tool].add(server_id)

            return True

    def update_capabilities(self, server_id: str, capabilities: List[str]) -> bool:
        """Update the capability list for a server."""
        with self._lock:
            info = self._servers.get(server_id)
            if info is None:
                return False

            for cap in info.capabilities:
                self._capability_index[cap].discard(server_id)
                if not self._capability_index[cap]:
                    del self._capability_index[cap]

            info.capabilities = list(capabilities)

            for cap in info.capabilities:
                self._capability_index[cap].add(server_id)

            return True

    # -- Stats & Reporting --------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            status_counts: Dict[str, int] = defaultdict(int)
            for s in self._servers.values():
                status_counts[s.status.value] += 1

            return {
                "registry_id": self._registry_id,
                "total_servers": len(self._servers),
                "status_breakdown": dict(status_counts),
                "total_tools": len(self._tool_index),
                "total_capabilities": len(self._capability_index),
                "total_tags": len(self._tag_index),
            }

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a health summary of all registered servers."""
        with self._lock:
            summary: Dict[str, Any] = {
                "healthy": [],
                "degraded": [],
                "unreachable": [],
                "unknown": [],
                "disabled": [],
            }
            for s in self._servers.values():
                if s.status == ServerStatus.READY:
                    summary["healthy"].append(s.name)
                elif s.status == ServerStatus.DEGRADED:
                    summary["degraded"].append(s.name)
                elif s.status == ServerStatus.UNREACHABLE:
                    summary["unreachable"].append(s.name)
                elif s.status == ServerStatus.DISABLED:
                    summary["disabled"].append(s.name)
                else:
                    summary["unknown"].append(s.name)

            summary["total"] = len(self._servers)
            summary["available_count"] = len(self.get_available())
            return summary

    def clear(self) -> None:
        """Remove all servers from the registry."""
        with self._lock:
            self._servers.clear()
            self._name_index.clear()
            self._tool_index.clear()
            self._capability_index.clear()
            self._tag_index.clear()
