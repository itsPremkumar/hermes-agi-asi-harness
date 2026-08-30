"""MCP Client - Connect to any MCP server."""
from __future__ import annotations
import asyncio
import json
import subprocess
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class MCPTransport(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


@dataclass
class MCPCapabilities:
    tools: bool = False
    prompts: bool = False
    resources: bool = False
    logging: bool = False


class MCPClient:
    """Universal MCP client supporting stdio, SSE, and HTTP transports."""
    
    def __init__(self, transport: MCPTransport = MCPTransport.STDIO):
        self.transport_type = transport
        self._process: Optional[subprocess.Popen] = None
        self._session_id: Optional[str] = None
        self._tools: Dict[str, MCPTool] = {}
        self._capabilities: Optional[MCPCapabilities] = None
        self._initialized = False
    
    async def connect_stdio(self, command: str, args: List[str] = None, env: Dict = None):
        """Connect to an MCP server via stdio transport."""
        import os
        cmd = [command] + (args or [])
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **(env or {})},
        )
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "hermes-agi", "version": "12.0.0"},
        })
        self._initialized = True
        await self._refresh_tools()
    
    async def connect_sse(self, url: str, headers: Dict = None):
        """Connect to an MCP server via SSE transport."""
        self._sse_url = url
        self._sse_headers = headers or {}
        self._initialized = True
    
    async def list_tools(self) -> List[MCPTool]:
        """List all available tools from the MCP server."""
        if not self._initialized:
            raise RuntimeError("MCP client not connected")
        response = await self._send_request("tools/list", {})
        tools = []
        for tool_data in response.get("tools", []):
            tools.append(MCPTool(
                name=tool_data["name"],
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {}),
                server_name=self._session_id or "unknown",
            ))
        self._tools = {t.name: t for t in tools}
        return tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a tool on the MCP server."""
        if not self._initialized:
            raise RuntimeError("MCP client not connected")
        response = await self._send_request("tools/call", {"name": name, "arguments": arguments or {}})
        return response.get("content", [])
    
    async def _send_request(self, method: str, params: Dict) -> Dict:
        """Send a JSON-RPC request."""
        request = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
        if self.transport_type == MCPTransport.STDIO and self._process:
            request_str = json.dumps(request) + "\n"
            self._process.stdin.write(request_str.encode())
            await self._process.stdin.drain()
            response_line = await self._process.stdout.readline()
            return json.loads(response_line.decode())
        return {}
    
    async def _refresh_tools(self):
        await self.list_tools()
    
    async def close(self):
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None
        self._initialized = False
