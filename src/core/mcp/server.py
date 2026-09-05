"""MCP Server - Expose Hermes tools as an MCP server."""
from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class MCPToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable


class MCPServer:
    """MCP server that exposes Hermes tools to other agents."""
    
    def __init__(self, name: str = "hermes-agi", version: str = "12.0.0"):
        self.name = name
        self.version = version
        self._tools: dict[str, MCPToolDefinition] = {}
        self._running = False
    
    def register_tool(self, name: str, description: str, input_schema: dict[str, Any], handler: Callable):
        self._tools[name] = MCPToolDefinition(name=name, description=description, input_schema=input_schema, handler=handler)
    
    async def start_stdio(self):
        self._running = True
        while self._running:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                request = json.loads(line)
                response = await self._handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}) + "\n")
                sys.stdout.flush()
    
    async def _handle_request(self, request: dict) -> dict:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        try:
            if method == "initialize":
                result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {"listChanged": True}}, "serverInfo": {"name": self.name, "version": self.version}}
            elif method == "tools/list":
                result = {"tools": [{"name": t.name, "description": t.description, "inputSchema": t.input_schema} for t in self._tools.values()]}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                tool_def = self._tools.get(tool_name)
                if not tool_def:
                    raise ValueError(f"Tool not found: {tool_name}")
                result = await tool_def.handler(arguments)
                result = {"content": [{"type": "text", "text": str(result)}]}
            else:
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method: {method}"}}
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(e)}}
    
    def stop(self):
        self._running = False
