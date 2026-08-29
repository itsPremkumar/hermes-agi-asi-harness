"""Mock MCP client for testing.

Provides a lightweight in-process MCP client that can connect to
servers via stdio, HTTP, or SSE transport for testing purposes.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from mcptest.config import Config


class MockMCPClient:
    """A minimal MCP client for testing servers.

    Supports stdio (subprocess), HTTP, and SSE transports.
    Sends JSON-RPC 2.0 messages per the MCP specification.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._proc: Optional[subprocess.Popen] = None
        self._http: Optional[httpx.AsyncClient] = None
        self._id_counter = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._initialized = False
        self._reader_task: Optional[asyncio.Task] = None

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    async def connect(self) -> None:
        """Establish connection to the target server."""
        transport = self.config.target.transport
        if transport == "stdio":
            await self._connect_stdio()
        elif transport in ("http", "sse"):
            await self._connect_http()
        else:
            raise ValueError(f"Unsupported transport: {transport}")

    async def _connect_stdio(self) -> None:
        """Connect via stdio transport."""
        cmd = [self.config.target.command] + self.config.target.args
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**__import__("os").environ, **self.config.target.env},
        )
        self._reader_task = asyncio.create_task(self._read_stdio())

    async def _read_stdio(self) -> None:
        """Read JSON-RPC messages from stdout."""
        assert self._proc is not None
        loop = asyncio.get_event_loop()
        while True:
            try:
                line = await loop.run_in_executor(None, self._proc.stdout.readline)
                if not line:
                    break
                msg = json.loads(line.decode("utf-8").strip())
                if "id" in msg and msg["id"] in self._pending:
                    self._pending.pop(msg["id"]).set_result(msg)
            except Exception:
                break

    async def _connect_http(self) -> None:
        """Connect via HTTP transport."""
        self._http = httpx.AsyncClient(
            base_url=self.config.target.url,
            timeout=30.0,
        )

    async def disconnect(self) -> None:
        """Close the connection."""
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        if self._http:
            await self._http.aclose()
            self._http = None

    async def _send_stdio(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Send a message via stdio and await response."""
        assert self._proc is not None
        msg_id = msg.get("id")
        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()
        if msg_id is not None:
            self._pending[msg_id] = future
        line = (json.dumps(msg) + "\n").encode("utf-8")
        self._proc.stdin.write(line)
        self._proc.stdin.flush()
        return await asyncio.wait_for(future, timeout=30.0)

    async def _send_http(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Send a message via HTTP POST."""
        assert self._http is not None
        resp = await self._http.post("/", json=msg)
        resp.raise_for_status()
        return resp.json()

    async def _send(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC message."""
        if self.config.target.transport == "stdio":
            return await self._send_stdio(msg)
        return await self._send_http(msg)

    async def initialize(self) -> dict[str, Any]:
        """Send initialize request."""
        msg = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcptest", "version": "1.0.0"},
            },
        }
        resp = await self._send(msg)
        if "result" in resp:
            self._initialized = True
            # Send initialized notification
            await self._send({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            })
        return resp

    async def list_tools(self) -> dict[str, Any]:
        """Send tools/list request."""
        msg = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        }
        return await self._send(msg)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send tools/call request."""
        msg = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        return await self._send(msg)

    async def list_resources(self) -> dict[str, Any]:
        """Send resources/list request."""
        msg = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/list",
            "params": {},
        }
        return await self._send(msg)

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Send resources/read request."""
        msg = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/read",
            "params": {"uri": uri},
        }
        return await self._send(msg)

    async def list_prompts(self) -> dict[str, Any]:
        """Send prompts/list request."""
        msg = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "prompts/list",
            "params": {},
        }
        return await self._send(msg)

    async def get_prompt(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send prompts/get request."""
        msg = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "prompts/get",
            "params": {"name": name, "arguments": arguments},
        }
        return await self._send(msg)

    async def ping(self) -> dict[str, Any]:
        """Send ping request."""
        msg = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "ping",
            "params": {},
        }
        return await self._send(msg)

    async def send_raw(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Send a raw JSON-RPC message."""
        if "id" not in msg:
            msg["id"] = self._next_id()
        return await self._send(msg)
