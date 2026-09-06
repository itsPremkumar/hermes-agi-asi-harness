"""Tool Bridge — live bridge connecting registered MCP servers to the harness.

The bridge connects to MCP servers from the :class:`MCPServerRegistry`,
discovers their tools, and registers them as virtual tools in the harness's
native :class:`~src.harness.tools.ToolRegistry`.  Agents then call MCP tools
exactly like local Python tools — the bridge handles the MCP protocol
transparently.

Usage::

    registry = MCPServerRegistry()
    registry.load()
    bridge = MCPToolBridge(registry, native_registry)
    await bridge.connect_all()
    # MCP tools are now available in native_registry
    await bridge.call_tool("filesystem.read_file", {"path": "/tmp/x.txt"})
    await bridge.disconnect_all()
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Mapping

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, ListToolsResult, Tool

from .server_registry import MCPServerRecord, MCPServerRegistry

try:
    from src.harness.tools import ToolRegistry, ToolSchema, ToolError
except ImportError:
    ToolRegistry = None  # type: ignore
    ToolSchema = None  # type: ignore
    ToolError = Exception  # type: ignore

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class BridgeError(Exception):
    """Base error for the tool bridge."""


class ServerConnectionError(BridgeError):
    """Could not connect to an MCP server."""


class ToolNotFoundError(BridgeError):
    """Tool not found on any connected MCP server."""


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

@dataclass
class ServerConnection:
    """A live connection to one MCP server."""

    record: MCPServerRecord
    session: Optional[ClientSession] = None
    tools: List[Tool] = field(default_factory=list)
    connected: bool = False
    last_error: Optional[str] = None
    _cleanup: Optional[Any] = None  # context manager exit callable

    @property
    def tool_names(self) -> set[str]:
        return {t.name for t in self.tools}


# ---------------------------------------------------------------------------
# Bridge stats
# ---------------------------------------------------------------------------

@dataclass
class BridgeStats:
    """Statistics about the bridge state."""

    servers_total: int = 0
    servers_connected: int = 0
    servers_failed: int = 0
    tools_discovered: int = 0
    calls_total: int = 0
    calls_failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "servers_total": self.servers_total,
            "servers_connected": self.servers_connected,
            "servers_failed": self.servers_failed,
            "tools_discovered": self.tools_discovered,
            "calls_total": self.calls_total,
            "calls_failed": self.calls_failed,
        }


# ---------------------------------------------------------------------------
# Tool Bridge
# ---------------------------------------------------------------------------

class MCPToolBridge:
    """Bridge MCP server tools into the harness native tool registry.

    The bridge manages connections to MCP servers and exposes their tools
    through a uniform ``call_tool`` interface as well as optionally
    registering them in the harness's :class:`ToolRegistry`.
    """

    def __init__(
        self,
        registry: MCPServerRegistry,
        native_registry: Optional[Any] = None,
        connect_timeout: float = 10.0,
        call_timeout: float = 30.0,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
    ):
        self._registry = registry
        self._native_registry = native_registry
        self._connect_timeout = connect_timeout
        self._call_timeout = call_timeout
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._connections: Dict[str, ServerConnection] = {}  # server_id -> connection
        self._tool_map: Dict[str, str] = {}  # tool_name -> server_id
        self._lock = asyncio.Lock()
        self._stats = BridgeStats()

    # -- properties -------------------------------------------------------

    @property
    def stats(self) -> BridgeStats:
        return self._stats

    @property
    def connections(self) -> Dict[str, ServerConnection]:
        return dict(self._connections)

    # -- connection management -------------------------------------------

    async def connect_all(self, enabled_only: bool = True) -> Dict[str, bool]:
        """Connect to all registered MCP servers.

        Returns a dict of server_id -> success.
        """
        records = self._registry.list_enabled() if enabled_only else self._registry.list_all()
        results: Dict[str, bool] = {}

        for record in records:
            try:
                await self._connect_one(record)
                results[record.id] = True
            except Exception as exc:
                log.error("Failed to connect to MCP server '%s': %s", record.name, exc)
                self._registry.set_health(record.id, "error")
                results[record.id] = False

        self._update_stats()
        return results

    async def connect_server(self, server_id: str) -> bool:
        """Connect to a single MCP server by ID."""
        record = self._registry.get(server_id)
        if record is None:
            raise KeyError(f"Server '{server_id}' not found in registry")
        try:
            await self._connect_one(record)
            self._update_stats()
            return True
        except Exception as exc:
            log.error("Failed to connect to MCP server '%s': %s", record.name, exc)
            self._registry.set_health(server_id, "error")
            self._update_stats()
            return False

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for conn in list(self._connections.values()):
            await self._disconnect_one(conn)
        self._connections.clear()
        self._tool_map.clear()
        self._update_stats()

    async def disconnect_server(self, server_id: str) -> bool:
        """Disconnect from a specific MCP server."""
        conn = self._connections.get(server_id)
        if conn is None:
            return False
        await self._disconnect_one(conn)
        self._connections.pop(server_id, None)
        # Remove tool mappings for this server
        self._tool_map = {
            t: sid for t, sid in self._tool_map.items() if sid != server_id
        }
        self._update_stats()
        return True

    async def _connect_one(self, record: MCPServerRecord) -> ServerConnection:
        """Establish a connection to one MCP server."""
        conn = ServerConnection(record=record)

        if record.transport == "stdio":
            await self._connect_stdio(conn)
        elif record.transport in ("http", "sse"):
            await self._connect_http(conn)
        else:
            raise BridgeError(f"Unknown transport: {record.transport}")

        # Discover tools
        tools = await asyncio.wait_for(
            conn.session.list_tools(),
            timeout=self._connect_timeout,
        )
        conn.tools = tools.tools if hasattr(tools, "tools") else []
        conn.connected = True

        # Register in connections map
        self._connections[record.id] = conn
        for tool in conn.tools:
            self._tool_map[tool.name] = record.id

        # Update registry health
        self._registry.set_health(record.id, "connected")

        # Register in native tool registry if available
        if self._native_registry is not None:
            await self._register_tools_in_native(conn)

        log.info(
            "Connected to MCP server '%s' (%d tools)",
            record.name, len(conn.tools),
        )
        return conn

    async def _connect_stdio(self, conn: ServerConnection) -> None:
        """Connect via stdio transport."""
        record = conn.record
        params = StdioServerParameters(
            command=record.command,
            args=record.args,
            env=record.env if record.env else None,
            cwd=record.cwd,
        )

        # Open stdio transport
        cm = stdio_client(params)
        read, write = await asyncio.wait_for(
            cm.__aenter__(),
            timeout=self._connect_timeout,
        )
        conn._cleanup = cm

        # Create session
        session = ClientSession(read_stream=read, write_stream=write)
        await asyncio.wait_for(
            session.__aenter__(),
            timeout=self._connect_timeout,
        )
        # Initialize
        await asyncio.wait_for(
            session.initialize(),
            timeout=self._connect_timeout,
        )
        conn.session = session

    async def _connect_http(self, conn: ServerConnection) -> None:
        """Connect via HTTP/SSE transport."""
        record = conn.record

        cm = streamable_http_client(record.url, terminate_on_close=True)
        read, write = await asyncio.wait_for(
            cm.__aenter__(),
            timeout=self._connect_timeout,
        )
        conn._cleanup = cm

        session = ClientSession(read_stream=read, write_stream=write)
        await asyncio.wait_for(
            session.__aenter__(),
            timeout=self._connect_timeout,
        )
        await asyncio.wait_for(
            session.initialize(),
            timeout=self._connect_timeout,
        )
        conn.session = session

    async def _disconnect_one(self, conn: ServerConnection) -> None:
        """Disconnect from one MCP server."""
        try:
            if conn.session is not None:
                if hasattr(conn.session, "aclose"):
                    await conn.session.aclose()
                elif hasattr(conn.session, "close"):
                    close = conn.session.close()
                    if asyncio.iscoroutine(close):
                        await close
        except Exception:
            pass

        try:
            if conn._cleanup is not None:
                if hasattr(conn._cleanup, "__aexit__"):
                    await conn._cleanup.__aexit__(None, None, None)
                elif hasattr(conn._cleanup, "close"):
                    close = conn._cleanup.close()
                    if asyncio.iscoroutine(close):
                        await close
        except Exception:
            pass

        conn.session = None
        conn.connected = False
        conn.tools = []

    async def _register_tools_in_native(self, conn: ServerConnection) -> None:
        """Register MCP tools in the native tool registry."""
        if self._native_registry is None:
            return

        for tool in conn.tools:
            try:
                schema = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }
                if hasattr(tool, "inputSchema") and tool.inputSchema:
                    schema = tool.inputSchema

                self._native_registry.register(
                    name=f"mcp.{conn.record.name}.{tool.name}",
                    description=f"[MCP:{conn.record.name}] {tool.description or ''}",
                    func=self._create_tool_func(tool.name, conn.record.id),
                    parameters=schema.get("properties", {}),
                    required=schema.get("required", []),
                )
            except Exception as exc:
                log.warning(
                    "Failed to register tool '%s' from server '%s': %s",
                    tool.name, conn.record.name, exc,
                )

    def _create_tool_func(self, tool_name: str, server_id: str):
        """Create a callable that routes tool calls to the MCP server."""
        async def _mcp_tool_func(**kwargs):
            return await self.call_tool_direct(tool_name, kwargs, server_id=server_id)

        _mcp_tool_func.__name__ = tool_name
        return _mcp_tool_func

    # -- tool discovery ---------------------------------------------------

    def available_tools(self) -> Dict[str, List[str]]:
        """Return dict of tool_name -> list of server names that provide it."""
        result: Dict[str, List[str]] = {}
        for tool_name, server_id in self._tool_map.items():
            conn = self._connections.get(server_id)
            if conn:
                result.setdefault(tool_name, []).append(conn.record.name)
        return result

    def find_server_for_tool(self, tool_name: str) -> Optional[str]:
        """Return server_id that provides the given tool, or None."""
        return self._tool_map.get(tool_name)

    # -- tool invocation --------------------------------------------------

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Mapping[str, Any]] = None,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """Call a tool by name, auto-routing to the correct server."""
        server_id = self._tool_map.get(tool_name)
        if server_id is None:
            raise ToolNotFoundError(
                f"Tool '{tool_name}' not found on any connected MCP server"
            )
        return await self.call_tool_direct(tool_name, arguments, server_id=server_id, timeout=timeout)

    async def call_tool_direct(
        self,
        tool_name: str,
        arguments: Optional[Mapping[str, Any]] = None,
        *,
        server_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Call a tool directly on a specific server."""
        timeout = timeout or self._call_timeout
        args = dict(arguments or {})

        # Find connection
        conn = None
        if server_id:
            conn = self._connections.get(server_id)
        else:
            # Search all connections
            for c in self._connections.values():
                if c.connected and c.record.id in [
                    sid for t, sid in self._tool_map.items() if t == tool_name
                ]:
                    conn = c
                    break

        if conn is None or not conn.connected:
            raise ServerConnectionError(
                f"No connected server for tool '{tool_name}'"
            )

        self._stats.calls_total += 1

        try:
            result: CallToolResult = await asyncio.wait_for(
                conn.session.call_tool(tool_name, args),
                timeout=timeout,
            )
            if hasattr(result, "isError") and result.isError:
                text = self._extract_text(result)
                self._stats.calls_failed += 1
                raise BridgeError(f"MCP tool error: {text}")
            return self._extract_result(result)
        except asyncio.TimeoutError:
            self._stats.calls_failed += 1
            raise BridgeError(f"Tool '{tool_name}' timed out after {timeout}s")
        except BridgeError:
            raise
        except Exception as exc:
            self._stats.calls_failed += 1
            raise BridgeError(f"Tool '{tool_name}' failed: {exc}") from exc

    @staticmethod
    def _extract_text(result: CallToolResult) -> str:
        """Extract error text from a CallToolResult."""
        parts: list[str] = []
        for content in result.content:
            if hasattr(content, "text"):
                parts.append(content.text)
            elif hasattr(content, "data"):
                parts.append(str(content.data))
        return "\n".join(parts) or "unknown error"

    @staticmethod
    def _extract_result(result: CallToolResult) -> Any:
        """Extract the best-effort Python value from a CallToolResult."""
        if hasattr(result, "structuredContent") and result.structuredContent is not None:
            return result.structuredContent
        texts: list[str] = []
        for content in result.content:
            if hasattr(content, "text"):
                texts.append(content.text)
        if texts:
            try:
                return json.loads(texts[0])
            except (json.JSONDecodeError, TypeError):
                return texts[0]
        return None

    # -- health checks ----------------------------------------------------

    async def health_check(self, server_id: str) -> bool:
        """Perform a health check on a specific server."""
        conn = self._connections.get(server_id)
        if conn is None or not conn.connected:
            return False
        try:
            await asyncio.wait_for(
                conn.session.list_tools(),
                timeout=5.0,
            )
            self._registry.set_health(server_id, "connected")
            return True
        except Exception as exc:
            log.warning("Health check failed for '%s': %s", conn.record.name, exc)
            self._registry.set_health(server_id, "error")
            return False

    async def health_check_all(self) -> Dict[str, bool]:
        """Run health checks on all connected servers."""
        results = {}
        for server_id in list(self._connections.keys()):
            results[server_id] = await self.health_check(server_id)
        return results

    # -- stats ------------------------------------------------------------

    def _update_stats(self) -> None:
        """Update bridge statistics."""
        self._stats.servers_total = self._registry.count()
        self._stats.servers_connected = sum(
            1 for c in self._connections.values() if c.connected
        )
        self._stats.servers_failed = (
            self._stats.servers_total - self._stats.servers_connected
        )
        self._stats.tools_discovered = len(self._tool_map)

    # -- context manager --------------------------------------------------

    async def __aenter__(self) -> "MCPToolBridge":
        await self.connect_all()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.disconnect_all()

    def __repr__(self) -> str:
        return (
            f"<MCPToolBridge connected={self._stats.servers_connected}"
            f"/{self._stats.servers_total} tools={self._stats.tools_discovered}>"
        )
