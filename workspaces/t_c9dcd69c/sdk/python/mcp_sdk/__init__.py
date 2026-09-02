"""MCPHub Python SDK for building MCP servers."""
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
import asyncio
import json


@dataclass
class MCPTool:
    """A single MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    transport: str = "stdio"  # stdio, http, sse
    tools: List[MCPTool] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPServer:
    """Base class for building MCP servers using MCPHub SDK."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._tools: Dict[str, MCPTool] = {}
        for tool in config.tools:
            self._tools[tool.name] = tool

    def tool(
        self,
        name: str,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
    ):
        """Decorator to register a tool."""
        def decorator(func: Callable):
            self._tools[name] = MCPTool(
                name=name,
                description=description or func.__doc__ or "",
                input_schema=input_schema or {},
                handler=func,
            )
            return func
        return decorator

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a registered tool."""
        if name not in self._tools:
            return {"error": f"Tool '{name}' not found"}
        tool = self._tools[name]
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                result = tool.handler(**arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        except Exception as e:
            return {"error": str(e)}

    def to_mcp_config(self) -> Dict[str, Any]:
        """Generate MCP client configuration."""
        return {
            "mcpServers": {
                self.config.name: {
                    "command": "python",
                    "args": ["-m", self.config.name],
                }
            }
        }

    def generate_manifest(self) -> Dict[str, Any]:
        """Generate server manifest for MCPHub registry."""
        return {
            "name": self.config.name,
            "version": self.config.version,
            "description": self.config.description,
            "author": self.config.author,
            "transport": self.config.transport,
            "tools": self.list_tools(),
            "metadata": self.config.metadata,
        }


def create_server(
    name: str,
    version: str = "1.0.0",
    description: str = "",
    author: str = "",
    transport: str = "stdio",
) -> MCPServer:
    """Factory function to create an MCP server."""
    config = MCPServerConfig(
        name=name,
        version=version,
        description=description,
        author=author,
        transport=transport,
    )
    return MCPServer(config)
