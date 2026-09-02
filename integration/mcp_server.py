"""
MCP Server — proper MCP server using the `mcp` library for Hermes integration.

This exposes the harnix kernel, plugins, bots, and benchmarks as MCP tools
that Hermes auto-discovers and makes available in every conversation.

Usage in Hermes config:
    mcp_servers:
      harnix:
        command: python
        args: ["-m", "integration.mcp_server"]
        timeout: 120

Then tools are available as: harnix_run, harnix_spawn_bot, harnix_benchmark, etc.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)

# We need to import the bridge modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


async def create_mcp_server() -> Any:
    """Create the MCP server."""
    server = Server("harnix-kernel")

    @server.list_tools()
    async def list_tools() -> list[Any]:
        return [
            Tool(
                name="run",
                description="Run a task through the harnix kernel lifecycle",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task description"},
                        "context": {"type": "object", "description": "Optional context"},
                    },
                    "required": ["task"],
                },
            ),
            Tool(
                name="spawn_bot",
                description="Spawn a specialized bot from the 26-bot swarm",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string", "description": "Bot name"},
                        "command": {"type": "string", "description": "Command for the bot"},
                    },
                    "required": ["bot_name", "command"],
                },
            ),
            Tool(
                name="benchmark",
                description="Run a benchmark (mmlu, gsm8k, humaneval, swe_bench, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Benchmark name"},
                    },
                },
            ),
            Tool(
                name="invoke_plugin",
                description="Invoke a specific plugin action",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plugin_id": {"type": "string", "description": "Plugin ID"},
                        "action": {"type": "string", "description": "Action to invoke"},
                        "params": {"type": "object", "description": "Action parameters"},
                    },
                    "required": ["plugin_id", "action"],
                },
            ),
            Tool(
                name="status",
                description="Get full system status (kernel, bots, benchmarks, improvement)",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="health",
                description="Get health status of all subsystems",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="list_bots",
                description="List all available bot profiles",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="list_benchmarks",
                description="List all available benchmarks",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="improve",
                description="Run the self-improvement cycle",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="bot_swarm_status",
                description="Get bot swarm status",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[Any]:
        from integration.hermes_bridge import HermesBridge
        from integration.hermes_bridge.config import load_config

        config = load_config()
        bridge = await HermesBridge.create(config)
        result = {"error": "Unknown tool"}

        if name == "run":
            result = await bridge.kernel.run(arguments.get("task", ""))
        elif name == "spawn_bot":
            result = await bridge.bots.spawn(arguments.get("bot_name", ""), arguments.get("command", ""))
        elif name == "benchmark":
            result = await bridge.benchmarks.run(arguments.get("name", "all"))
        elif name == "invoke_plugin":
            result = await bridge.kernel.invoke_plugin(
                arguments.get("plugin_id", ""),
                arguments.get("action", ""),
                arguments.get("params"),
            )
        elif name == "status":
            result = await bridge.status()
        elif name == "health":
            result = await bridge.health()
        elif name == "list_bots":
            result = bridge.bots.list_bots()
        elif name == "list_benchmarks":
            result = await bridge.benchmarks.status()
        elif name == "improve":
            result = await bridge.improvement.run()
        elif name == "bot_swarm_status":
            result = await bridge.bots.status()

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return server


async def run_mcp_server():
    """Run the MCP server."""
    if not HAS_MCP:
        logger.error("MCP SDK not available. Install with: pip install mcp")
        sys.exit(1)

    server = await create_mcp_server()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(run_mcp_server())
