"""MCP Integration Layer — Server Registry + Tool Bridge.

This package implements the MCP integration for the Hermes AGI/ASI Harness:

* :mod:`server_registry` — persistent registry of MCP server configurations
  with CRUD, health checks, capability tagging, and search.
* :mod:`tool_bridge` — live bridge that connects to registered MCP servers,
  discovers their tools, and exposes them through the harness's native
  :class:`~src.harness.tools.ToolRegistry` so existing agents can call MCP
  tools alongside local Python tools.
* :mod:`plugin` — :class:`~harness_control_plane.IPlugin` entry point that
  wires the registry + bridge into the harness control plane.

Output Law: files written to workspace, committed and pushed to
itsPremkumar/hermes-agi-asi-harness.
"""

from .server_registry import MCPServerRecord, MCPServerRegistry
from .tool_bridge import MCPToolBridge, BridgeStats
from .plugin import MCPIntegrationPlugin

__all__ = [
    "MCPServerRecord",
    "MCPServerRegistry",
    "MCPToolBridge",
    "BridgeStats",
    "MCPIntegrationPlugin",
]

__version__ = "1.0.0"
