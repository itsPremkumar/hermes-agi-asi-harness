"""MCPBridge — maps MCP tools to harness tool calls.

The bridge translates between MCP tool definitions and the harness's
internal tool-call format. It handles schema conversion, argument
validation, and result normalization.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .client import MCPClient, MCPConnectionError, MCPTimeoutError, MCPToolError
from .registry import MCPRegistry, MCPServerInfo, ServerStatus

log = logging.getLogger(__name__)


@dataclass
class ToolMapping:
    """Maps an MCP tool to a harness tool name."""
    harness_tool_name: str
    mcp_tool_name: str
    server_id: str
    server_name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        """Get the qualified tool name: mcp__<server>__<tool>."""
        return f"mcp__{self.server_name}__{self.mcp_tool_name}"


class MCPBridge:
    """Maps MCP tools to harness tool calls.

    The bridge maintains a mapping between harness-facing tool names
    and MCP server tools. It handles:
    - Schema conversion (MCP JSON Schema -> harness format)
    - Argument validation against tool schemas
    - Result normalization
    - Tool name sanitization and namespacing
    """

    def __init__(self, registry: MCPRegistry):
        self._registry = registry
        self._bridge_id = f"bridge-{uuid.uuid4().hex[:12]}"
        self._mcp_clients: Dict[str, MCPClient] = {}
        self._tool_mappings: Dict[str, ToolMapping] = {}  # harness_name -> mapping
        self._mcp_to_harness: Dict[str, str] = {}  # qualified_mcp_name -> harness_name
        self._pre_call_hooks: List[Callable[[str, Dict[str, Any]], None]] = []
        self._post_call_hooks: List[Callable[[str, Any, float], None]] = []

    @property
    def bridge_id(self) -> str:
        return self._bridge_id

    @property
    def tool_count(self) -> int:
        return len(self._tool_mappings)

    # -- Tool Registration --------------------------------------------------

    def register_tool(
        self,
        harness_tool_name: str,
        mcp_tool_name: str,
        server_id: str,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolMapping:
        """Register a tool mapping."""
        server = self._registry.get(server_id)
        if server is None:
            raise ValueError(f"Server '{server_id}' not found in registry")

        mapping = ToolMapping(
            harness_tool_name=harness_tool_name,
            mcp_tool_name=mcp_tool_name,
            server_id=server_id,
            server_name=server.name,
            description=description,
            input_schema=input_schema or {},
            metadata=dict(metadata or {}),
        )

        self._tool_mappings[harness_tool_name] = mapping
        self._mcp_to_harness[mapping.qualified_name] = harness_tool_name

        return mapping

    def unregister_tool(self, harness_name: str) -> bool:
        """Remove a tool mapping."""
        mapping = self._tool_mappings.pop(harness_name, None)
        if mapping is None:
            return False
        self._mcp_to_harness.pop(mapping.qualified_name, None)
        return True

    def get_mapping(self, harness_name: str) -> Optional[ToolMapping]:
        """Get a tool mapping by harness name."""
        return self._tool_mappings.get(harness_name)

    def get_mapping_by_qualified(self, qualified_name: str) -> Optional[ToolMapping]:
        """Get a tool mapping by qualified MCP name."""
        harness_name = self._mcp_to_harness.get(qualified_name)
        return self._tool_mappings.get(harness_name) if harness_name else None

    def list_tools(self) -> List[ToolMapping]:
        """List all registered tool mappings."""
        return list(self._tool_mappings.values())

    def list_available_tools(self) -> List[ToolMapping]:
        """List tool mappings for available servers."""
        return [
            m for m in self._tool_mappings.values()
            if self._registry.get(m.server_id)
            and self._registry.get(m.server_id).is_available
        ]

    # -- Tool Invocation ---------------------------------------------------

    def call_tool(
        self,
        harness_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Call a registered tool by its harness name."""
        import time

        mapping = self._tool_mappings.get(harness_name)
        if mapping is None:
            raise ValueError(f"Tool '{harness_name}' not registered in bridge")

        # Validate arguments
        if mapping.input_schema:
            self._validate_arguments(arguments or {}, mapping.input_schema)

        # Fire pre-call hooks
        for hook in self._pre_call_hooks:
            try:
                hook(harness_name, arguments or {})
            except Exception:
                pass

        start_time = time.time()

        try:
            result = self._invoke_mcp_tool(mapping, arguments or {})
            elapsed = time.time() - start_time

            # Fire post-call hooks
            for hook in self._post_call_hooks:
                try:
                    hook(harness_name, result, elapsed)
                except Exception:
                    pass

            return result

        except Exception:
            elapsed = time.time() - start_time
            for hook in self._post_call_hooks:
                try:
                    hook(harness_name, None, elapsed)
                except Exception:
                    pass
            raise

    def _invoke_mcp_tool(self, mapping: ToolMapping, arguments: Dict[str, Any]) -> Any:
        """Invoke the MCP tool on the appropriate server."""
        client = self._mcp_clients.get(mapping.server_id)
        if client is None or not client.is_connected:
            # Try to get a client for this server
            client = self._get_or_create_client(mapping.server_id)
            if client is None:
                raise MCPConnectionError(
                    f"No available client for server '{mapping.server_name}'"
                )

        return client.call_tool(mapping.mcp_tool_name, arguments)

    def _get_or_create_client(self, server_id: str) -> Optional[MCPClient]:
        """Get or create an MCP client for a server."""
        from .client import ConnectionConfig

        server = self._registry.get(server_id)
        if server is None:
            return None

        if server.transport == "stdio":
            # Parse endpoint as command
            parts = server.endpoint.split()
            config = ConnectionConfig(
                transport="stdio",
                command=parts[0],
                args=parts[1:] if len(parts) > 1 else [],
            )
        elif server.transport == "http":
            config = ConnectionConfig(
                transport="http",
                url=server.endpoint,
            )
        else:
            log.error("Unknown transport '%s' for server '%s'", server.transport, server.name)
            return None

        client = MCPClient(config=config, name=server.name)
        try:
            client.connect()
            self._mcp_clients[server_id] = client
            return client
        except Exception as exc:
            log.error("Failed to connect to server '%s': %s", server.name, exc)
            return None

    # -- Schema Conversion --------------------------------------------------

    @staticmethod
    def sanitize_tool_name(name: str) -> str:
        """Sanitize a tool name for use in the harness."""
        # Replace non-alphanumeric with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Remove leading digits
        sanitized = re.sub(r'^[0-9]+', '', sanitized)
        # Collapse multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Strip leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized or "tool"

    @staticmethod
    def convert_mcp_schema(mcp_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert an MCP JSON Schema to harness format."""
        if not mcp_schema:
            return {"type": "object", "properties": {}, "required": []}

        converted = dict(mcp_schema)

        # Ensure type is present
        if "type" not in converted:
            converted["type"] = "object"

        # Ensure properties exist
        if "properties" not in converted:
            converted["properties"] = {}

        # Ensure required is a list
        if "required" not in converted:
            converted["required"] = []
        elif not isinstance(converted["required"], list):
            converted["required"] = list(converted["required"])

        return converted

    @staticmethod
    def _validate_arguments(arguments: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate arguments against a JSON Schema."""
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # Check required fields
        for field_name in required:
            if field_name not in arguments:
                raise ValueError(f"Missing required argument: '{field_name}'")

        # Check property types (basic validation)
        for key, value in arguments.items():
            if key in properties:
                prop_schema = properties[key]
                expected_type = prop_schema.get("type")
                if expected_type:
                    MCPBridge._check_type(key, value, expected_type)

    @staticmethod
    def _check_type(name: str, value: Any, expected_type: str) -> None:
        """Basic type checking for a value."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        python_type = type_map.get(expected_type)
        if python_type and not isinstance(value, python_type):
            raise TypeError(
                f"Argument '{name}' expected {expected_type}, got {type(value).__name__}"
            )

    # -- Hooks --------------------------------------------------------------

    def on_pre_call(self, hook: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register a pre-call hook: fn(tool_name, arguments)."""
        self._pre_call_hooks.append(hook)

    def on_post_call(self, hook: Callable[[str, Any, float], None]) -> None:
        """Register a post-call hook: fn(tool_name, result, elapsed_seconds)."""
        self._post_call_hooks.append(hook)

    # -- Tool Discovery -----------------------------------------------------

    def discover_and_register(self, server_id: str, prefix: str = "") -> List[ToolMapping]:
        """Discover tools from a server and register them."""
        server = self._registry.get(server_id)
        if server is None:
            raise ValueError(f"Server '{server_id}' not found")

        client = self._get_or_create_client(server_id)
        if client is None:
            raise MCPConnectionError(f"Cannot connect to server '{server.name}'")

        mappings = []
        for tool in client.tools:
            harness_name = f"{prefix}{self.sanitize_tool_name(tool.name)}" if prefix else self.sanitize_tool_name(tool.name)
            mapping = self.register_tool(
                harness_name=harness_name,
                mcp_tool_name=tool.name,
                server_id=server_id,
                description=tool.description or "",
                input_schema=dict(tool.inputSchema) if tool.inputSchema else {},
            )
            mappings.append(mapping)

        return mappings

    # -- Stats & Reporting --------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "bridge_id": self._bridge_id,
            "registered_tools": len(self._tool_mappings),
            "connected_clients": sum(
                1 for c in self._mcp_clients.values() if c.is_connected
            ),
            "total_clients": len(self._mcp_clients),
            "available_tools": len(self.list_available_tools()),
        }

    def get_tool_manifest(self) -> List[Dict[str, Any]]:
        """Get a manifest of all registered tools."""
        return [
            {
                "harness_name": m.harness_tool_name,
                "mcp_name": m.mcp_tool_name,
                "qualified_name": m.qualified_name,
                "server": m.server_name,
                "description": m.description,
                "schema": m.input_schema,
            }
            for m in self._tool_mappings.values()
        ]

    def clear(self) -> None:
        """Remove all tool mappings and disconnect clients."""
        self._tool_mappings.clear()
        self._mcp_to_harness.clear()
        for client in self._mcp_clients.values():
            try:
                client.disconnect()
            except Exception:
                pass
        self._mcp_clients.clear()
