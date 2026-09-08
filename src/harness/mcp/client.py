"""MCPClient — connection management, tool invocation, error handling.

Manages a single connection to an MCP server. Provides connection lifecycle,
tool listing, invocation with timeouts and retries, and automatic reconnection.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, ListToolsResult, Tool

log = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection lifecycle states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class MCPConnectionError(Exception):
    """Raised when a connection to an MCP server fails."""
    pass


class MCPTimeoutError(Exception):
    """Raised when a tool call times out."""
    pass


class MCPToolError(Exception):
    """Raised when a tool call returns an error."""

    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}': {message}")


@dataclass
class ConnectionConfig:
    """Configuration for an MCP client connection."""
    transport: str = "stdio"  # "stdio" | "http"
    # stdio settings
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    # http settings
    url: str = ""
    headers: Optional[Dict[str, str]] = None
    # timeouts
    connect_timeout: float = 10.0
    call_timeout: float = 30.0
    # retry
    max_retries: int = 3
    retry_backoff: float = 0.5
    # keepalive
    keepalive_interval: float = 60.0
    idle_timeout_seconds: float = 300.0


class MCPClient:
    """Manages a single connection to an MCP server.

    Thread-safe. Supports connection lifecycle, tool discovery,
    invocation with timeouts and retries, and automatic reconnection.
    """

    def __init__(self, config: ConnectionConfig, name: str = "default"):
        self._config = config
        self._name = name
        self._client_id = f"client-{uuid.uuid4().hex[:12]}"
        self._state = ConnectionState.DISCONNECTED
        self._session: Optional[ClientSession] = None
        self._tools: List[Tool] = []
        self._lock = threading.RLock()
        self._last_activity: float = time.time()
        self._call_count: int = 0
        self._error_count: int = 0
        self._created_at: float = time.time()
        self._connected_at: Optional[float] = None

    @property
    def client_id(self) -> str:
        return self._client_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def tools(self) -> List[Tool]:
        return list(self._tools)

    @property
    def tool_names(self) -> set:
        return {t.name for t in self._tools}

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def uptime(self) -> float:
        if self._connected_at is None:
            return 0.0
        return time.time() - self._connected_at

    @property
    def idle_time(self) -> float:
        return time.time() - self._last_activity

    # -- Connection Lifecycle -----------------------------------------------

    def connect(self) -> bool:
        """Connect to the MCP server. Returns True on success."""
        import asyncio

        with self._lock:
            if self._state == ConnectionState.CONNECTED:
                return True

            self._state = ConnectionState.CONNECTING

            attempt = 0
            last_exc: Optional[Exception] = None

            while attempt <= self._config.max_retries:
                try:
                    loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self._do_connect())
                    finally:
                        loop.close()

                    self._state = ConnectionState.CONNECTED
                    self._connected_at = time.time()
                    self._last_activity = time.time()
                    return True

                except Exception as exc:
                    last_exc = exc
                    attempt += 1
                    log.warning(
                        "Connection attempt %d/%d to '%s' failed: %s",
                        attempt,
                        self._config.max_retries + 1,
                        self._name,
                        exc,
                    )
                    if attempt <= self._config.max_retries:
                        backoff = self._config.retry_backoff * (2 ** (attempt - 1))
                        time.sleep(backoff)

            self._state = ConnectionState.FAILED
            raise MCPConnectionError(
                f"Failed to connect to '{self._name}' after {attempt} attempts: {last_exc}"
            )

    async def _do_connect(self) -> None:
        """Perform the actual connection."""
        import asyncio

        if self._config.transport == "stdio":
            params = StdioServerParameters(
                command=self._config.command,
                args=self._config.args,
                env=self._config.env,
                cwd=self._config.cwd,
            )

            # Use asyncio.wait_for with timeout
            async def connect_stdio():
                async with stdio_client(params) as (read_stream, write_stream):
                    await self._init_session(read_stream, write_stream)

            await asyncio.wait_for(connect_stdio(), timeout=self._config.connect_timeout)

        elif self._config.transport == "http":
            async def connect_http():
                async with streamable_http_client(
                    self._config.url,
                    terminate_on_close=True,
                ) as (read_stream, write_stream):
                    await self._init_session(read_stream, write_stream)

            await asyncio.wait_for(connect_http(), timeout=self._config.connect_timeout)
        else:
            raise ValueError(f"Unknown transport: {self._config.transport}")

    async def _init_session(self, read_stream, write_stream) -> None:
        """Initialize the MCP session and discover tools."""
        import asyncio

        self._session = ClientSession(read_stream=read_stream, write_stream=write_stream)

        async with self._session:
            init = await asyncio.wait_for(self._session.initialize(), timeout=30.0)
            log.debug(
                "Server '%s' initialised: %s",
                self._name,
                init.serverInfo.name if init else "?",
            )
            result: ListToolsResult = await asyncio.wait_for(
                self._session.list_tools(), timeout=30.0
            )
            self._tools = result.tools

    def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        import asyncio

        with self._lock:
            if self._session is not None:
                try:
                    loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(loop)
                        if hasattr(self._session, "aclose"):
                            loop.run_until_complete(
                                asyncio.wait_for(self._session.aclose(), timeout=10.0)
                            )
                        elif hasattr(self._session, "close"):
                            close = self._session.close()
                            if asyncio.iscoroutine(close):
                                loop.run_until_complete(
                                    asyncio.wait_for(close, timeout=10.0)
                                )
                    finally:
                        loop.close()
                except Exception:
                    pass

            self._session = None
            self._tools = []
            self._state = ConnectionState.DISCONNECTED

    def reconnect(self) -> bool:
        """Disconnect and reconnect."""
        self.disconnect()
        return self.connect()

    # -- Tool Operations ----------------------------------------------------

    def list_tools(self) -> List[Tool]:
        """List available tools from the connected server."""
        import asyncio

        self._ensure_connected()

        try:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    asyncio.wait_for(self._session.list_tools(), timeout=30.0)
                )
                self._tools = result.tools
                self._last_activity = time.time()
                return self._tools
            finally:
                loop.close()
        except Exception as exc:
            self._error_count += 1
            raise MCPConnectionError(f"Failed to list tools: {exc}")

    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a tool on the MCP server. Returns the result."""
        import asyncio

        self._ensure_connected()

        if tool_name not in self.tool_names:
            raise MCPToolError(tool_name, "Tool not available on this server")

        self._call_count += 1

        try:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    asyncio.wait_for(
                        self._session.call_tool(tool_name, arguments or {}),
                        timeout=self._config.call_timeout,
                    )
                )
            finally:
                loop.close()

            self._last_activity = time.time()

            if result.is_error:
                text = self._extract_error_text(result)
                raise MCPToolError(tool_name, text)

            return self._extract_result(result)

        except asyncio.TimeoutError:
            self._error_count += 1
            raise MCPTimeoutError(f"Tool '{tool_name}' timed out after {self._config.call_timeout}s")
        except (MCPToolError, MCPTimeoutError):
            raise
        except Exception as exc:
            self._error_count += 1
            raise MCPConnectionError(f"Tool call failed: {exc}")

    def has_tool(self, tool_name: str) -> bool:
        """Check if the server provides a specific tool."""
        return tool_name in self.tool_names

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get a tool definition by name."""
        for t in self._tools:
            if t.name == tool_name:
                return t
        return None

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get the input schema for a tool."""
        tool = self.get_tool(tool_name)
        return tool.inputSchema if tool else None

    # -- Health & Metrics ---------------------------------------------------

    def health_check(self) -> bool:
        """Perform a health check by listing tools."""
        try:
            self.list_tools()
            return True
        except Exception:
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics."""
        return {
            "client_id": self._client_id,
            "name": self._name,
            "state": self._state.value,
            "transport": self._config.transport,
            "tools_count": len(self._tools),
            "call_count": self._call_count,
            "error_count": self._error_count,
            "uptime": self.uptime,
            "idle_time": self.idle_time,
        }

    # -- Private Helpers ----------------------------------------------------

    def _ensure_connected(self) -> None:
        """Ensure the client is connected."""
        if self._state != ConnectionState.CONNECTED or self._session is None:
            raise MCPConnectionError(f"Client '{self._name}' is not connected")

    @staticmethod
    def _extract_result(result: CallToolResult) -> Any:
        """Extract the best-effort Python value from a CallToolResult."""
        if result.structured_content is not None:
            return result.structured_content
        texts: list = []
        for content in result.content:
            if hasattr(content, "text"):
                texts.append(content.text)
        if texts:
            try:
                return json.loads(texts[0])
            except Exception:
                return texts[0]
        return None

    @staticmethod
    def _extract_error_text(result: CallToolResult) -> str:
        """Extract error text from a CallToolResult."""
        parts: list = []
        for content in result.content:
            if hasattr(content, "text"):
                parts.append(content.text)
            elif hasattr(content, "data"):
                parts.append(str(content.data))
        return "\n".join(parts) or "unknown error"
