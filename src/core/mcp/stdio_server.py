"""Real MCP stdio server — exposes the harness to spec-compliant MCP clients.

Lets Hermes Agent (native MCP client) call harness capabilities as
first-class tools: ``mcp_hermes_harness_asi``, ``..._run_task``, etc.

Requires the official SDK: ``pip install mcp`` (``pip install -e \".[mcp]\"``).
Transport: stdio (Content-Length framing handled by the SDK).

Run: ``python -m hermes_agi mcp-serve``
Hermes config snippet (in the integration doc ``docs/HERMES_INTEGRATION.md``).
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_bridge: Any = None


async def _get_bridge():
    """Single shared bridge (one Harness) for the server process lifetime."""
    global _bridge
    if _bridge is None:
        from hermes_agi.bridge import HermesBridge

        _bridge = await HermesBridge.create(None)
    return _bridge


def _dump(result: Any) -> str:
    try:
        return json.dumps(result, default=str)[:20000]
    except Exception:  # noqa: BLE001 - MCP must always return text
        return str(result)[:20000]


def build_server():
    """Create the MCP server with all harness tools registered."""
    from mcp.server.mcpserver import MCPServer

    server = MCPServer(
        name="hermes-agi-asi",
        instructions=(
            "Hermes AGI/ASI Harness: autonomous task execution with deliberation, "
            "dual-substrate execution, verification proofs, benchmarks, research, "
            "and bot spawning. Prefer the 'asi' tool for any task."
        ),
    )

    @server.tool()
    async def asi(task: str) -> str:
        """Handle ANY task at ASI level: deliberate, execute, verify, report with proof."""
        bridge = await _get_bridge()
        return _dump(await bridge.asi(task))

    @server.tool()
    async def run_task(task: str, mode: str = "auto") -> str:
        """Run a task through the harness kernel (modes: auto, dual_substrate, intelligence_os)."""
        bridge = await _get_bridge()
        return _dump(await bridge.run(task, mode=mode))

    @server.tool()
    async def think(goal: str) -> str:
        """Deep Graph-of-Thought deliberation on a goal (hypotheses, risks, invariants)."""
        bridge = await _get_bridge()
        return _dump(await bridge.think(goal))

    @server.tool()
    async def research(topic: str, depth: int = 3) -> str:
        """Autonomous deep research on a topic; returns an evidence dossier."""
        bridge = await _get_bridge()
        return _dump(await bridge.research(topic, depth=int(depth)))

    @server.tool()
    async def benchmark(name: str = "all") -> str:
        """Run harness benchmarks with real measured scores."""
        bridge = await _get_bridge()
        return _dump(await bridge.benchmark(name))

    @server.tool()
    async def spawn_bot(bot_name: str, command: str) -> str:
        """Spawn a specialized harness bot to execute a command."""
        bridge = await _get_bridge()
        return _dump(await bridge.spawn_bot(bot_name, command))

    @server.tool()
    async def discover(query: str = "") -> str:
        """Search harness capabilities and features."""
        bridge = await _get_bridge()
        return _dump(await bridge.discover(query))

    @server.tool()
    async def allocate(task: str, role: str = "hermes-coder") -> str:
        """Allocate a monitored mission packet for a Hermes-side executor."""
        bridge = await _get_bridge()
        return _dump(await bridge.allocate(task, role=role))

    @server.tool()
    async def status() -> str:
        """Live harness status across kernel, bots, benchmarks, improvement."""
        bridge = await _get_bridge()
        return _dump(await bridge.status())

    @server.tool()
    async def health() -> str:
        """Live health across all harness subsystems."""
        bridge = await _get_bridge()
        return _dump(await bridge.health())

    return server


async def serve_stdio() -> None:
    """Run the MCP server on stdio (blocking; Ctrl+C to stop)."""
    server = build_server()
    await server.run_stdio_async()
