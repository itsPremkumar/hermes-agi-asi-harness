"""MCP Integration Plugin — IPlugin entry point.

Wires the Server Registry + Tool Bridge into the harness control plane.
Registering this plugin makes all MCP server tools available to agents
through the native tool registry, with full lifecycle management.

Usage::

    from harness_control_plane import PluginRegistry
    from core.mcp_integration.plugin import MCPIntegrationPlugin

    plugin_registry = PluginRegistry()
    mcp_plugin = MCPIntegrationPlugin()
    plugin_registry.register(mcp_plugin)

    await mcp_plugin.initialize({
        "config_path": "~/.hermes-asi/mcp_servers.json",
        "auto_connect": True,
    })
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from harness_control_plane import IPlugin, TaskRequest, TaskResult

from .server_registry import MCPServerRegistry
from .tool_bridge import MCPToolBridge, BridgeStats

log = logging.getLogger(__name__)


class MCPIntegrationPlugin(IPlugin):
    """Harness plugin that bridges MCP servers into the native tool registry.

    On initialize, loads the server registry from disk and optionally
    auto-connects to all enabled servers. MCP tools become available
    in the harness native registry alongside local Python tools.
    """

    name = "mcp-integration"
    version = "1.0.0"
    capabilities = [
        "mcp_server_registry",
        "mcp_tool_bridge",
        "mcp_health_monitoring",
    ]

    def __init__(self) -> None:
        self._registry: Optional[MCPServerRegistry] = None
        self._bridge: Optional[MCPToolBridge] = None
        self._config: Dict[str, Any] = {}
        self._initialized = False

    @property
    def registry(self) -> Optional[MCPServerRegistry]:
        return self._registry

    @property
    def bridge(self) -> Optional[MCPToolBridge]:
        return self._bridge

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the MCP integration plugin.

        Parameters
        ----------
        config
            Configuration dict with optional keys:
            - config_path: path to the MCP servers JSON registry file
            - auto_connect: if True, connect to all enabled servers on init
            - connect_timeout: timeout for connecting to each server (seconds)
            - call_timeout: timeout for tool calls (seconds)
            - max_retries: max retry attempts for failed connections
            - retry_backoff: backoff between retries (seconds)
        """
        self._config = dict(config)
        config_path = self._config.get("config_path")

        # Load server registry
        self._registry = MCPServerRegistry(config_path=config_path)
        self._registry.load()
        log.info(
            "MCP integration initialized — %d servers registered",
            self._registry.count(),
        )

        # Build tool bridge (without native registry; we register tools lazily)
        self._bridge = MCPToolBridge(
            registry=self._registry,
            native_registry=None,  # wired by harness if ToolRegistry is available
            connect_timeout=self._config.get("connect_timeout", 10.0),
            call_timeout=self._config.get("call_timeout", 30.0),
            max_retries=self._config.get("max_retries", 3),
            retry_backoff=self._config.get("retry_backoff", 0.5),
        )

        self._initialized = True

        # Auto-connect if requested
        if self._config.get("auto_connect", False):
            await self._connect_all_servers()

    async def execute(self, task: TaskRequest) -> TaskResult:
        """Execute a task through the MCP integration.

        Supported task types:
        - ``list_servers`` — return all registered MCP servers
        - ``list_tools`` — return all discovered tools from connected servers
        - ``call_tool`` — call an MCP tool (payload: name, arguments)
        - ``register_server`` — add a new MCP server to the registry
        - ``unregister_server`` — remove an MCP server
        - ``health`` — health status of all connected servers
        - ``stats`` — bridge statistics
        - ``connect`` — connect to one or all servers
        - ``disconnect`` — disconnect from one or all servers
        """
        if not self._initialized:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error="MCP integration not initialized",
            )

        task_type = task.task_type
        payload = task.payload or {}

        try:
            if task_type == "list_servers":
                return self._list_servers(task.task_id)
            elif task_type == "list_tools":
                return self._list_tools(task.task_id)
            elif task_type == "call_tool":
                return await self._call_tool(task.task_id, payload)
            elif task_type == "register_server":
                return self._register_server(task.task_id, payload)
            elif task_type == "unregister_server":
                return self._unregister_server(task.task_id, payload)
            elif task_type == "health":
                return await self._health_check(task.task_id)
            elif task_type == "stats":
                return self._get_stats(task.task_id)
            elif task_type == "connect":
                return await self._connect_task(task.task_id, payload)
            elif task_type == "disconnect":
                return await self._disconnect_task(task.task_id, payload)
            else:
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"Unknown task type: {task_type}",
                )
        except Exception as exc:
            log.exception("MCP task '%s' failed", task_type)
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(exc),
            )

    async def shutdown(self) -> None:
        """Disconnect from all MCP servers and save the registry."""
        if self._bridge is not None:
            await self._bridge.disconnect_all()
        if self._registry is not None:
            self._registry.save()
        self._initialized = False
        log.info("MCP integration shut down")

    async def health_check(self) -> bool:
        """Check if the MCP integration is healthy."""
        if not self._initialized or self._registry is None:
            return False
        return self._registry.is_loaded()

    # -- task handlers ----------------------------------------------------

    def _list_servers(self, task_id: str) -> TaskResult:
        servers = []
        if self._registry:
            for r in self._registry.list_all():
                servers.append({
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "transport": r.transport,
                    "url": r.url or f"{r.command} {' '.join(r.args)}",
                    "capabilities": r.capabilities,
                    "health_status": r.health_status,
                    "enabled": r.enabled,
                })
        return TaskResult(task_id=task_id, success=True, result=servers)

    def _list_tools(self, task_id: str) -> TaskResult:
        tools = {}
        if self._bridge:
            for tool_name, server_names in self._bridge.available_tools().items():
                tools[tool_name] = server_names
        return TaskResult(task_id=task_id, success=True, result=tools)

    async def _call_tool(self, task_id: str, payload: Dict[str, Any]) -> TaskResult:
        tool_name = payload.get("name")
        arguments = payload.get("arguments", {})
        if not tool_name:
            return TaskResult(task_id=task_id, success=False, error="Missing tool name")

        assert self._bridge is not None
        result = await self._bridge.call_tool(tool_name, arguments)
        return TaskResult(task_id=task_id, success=True, result=result)

    def _register_server(self, task_id: str, payload: Dict[str, Any]) -> TaskResult:
        assert self._registry is not None
        name = payload.get("name")
        if not name:
            return TaskResult(task_id=task_id, success=False, error="Missing server name")

        record = self._registry.register(
            name=name,
            transport=payload.get("transport", "stdio"),
            command=payload.get("command", ""),
            args=payload.get("args"),
            env=payload.get("env"),
            cwd=payload.get("cwd"),
            url=payload.get("url", ""),
            description=payload.get("description", ""),
            capabilities=payload.get("capabilities"),
            metadata=payload.get("metadata"),
        )
        self._registry.save()
        return TaskResult(task_id=task_id, success=True, result=record.to_dict())

    def _unregister_server(self, task_id: str, payload: Dict[str, Any]) -> TaskResult:
        assert self._registry is not None
        server_id = payload.get("id")
        if not server_id:
            return TaskResult(task_id=task_id, success=False, error="Missing server ID")

        ok = self._registry.unregister(server_id)
        if ok:
            self._registry.save()
        return TaskResult(task_id=task_id, success=ok, result={"removed": ok})

    async def _health_check(self, task_id: str) -> TaskResult:
        results = {}
        if self._bridge:
            results = await self._bridge.health_check_all()
        return TaskResult(task_id=task_id, success=True, result=results)

    def _get_stats(self, task_id: str) -> TaskResult:
        if self._bridge:
            stats: BridgeStats = self._bridge.stats
            return TaskResult(task_id=task_id, success=True, result=stats.to_dict())
        return TaskResult(
            task_id=task_id,
            success=True,
            result={
                "servers_total": 0,
                "servers_connected": 0,
                "servers_failed": 0,
                "tools_discovered": 0,
                "calls_total": 0,
                "calls_failed": 0,
            },
        )

    async def _connect_task(self, task_id: str, payload: Dict[str, Any]) -> TaskResult:
        server_id = payload.get("id")
        if server_id:
            assert self._bridge is not None
            ok = await self._bridge.connect_server(server_id)
            return TaskResult(task_id=task_id, success=ok)
        else:
            return await self._connect_all_servers(task_id)

    async def _disconnect_task(self, task_id: str, payload: Dict[str, Any]) -> TaskResult:
        server_id = payload.get("id")
        if server_id:
            assert self._bridge is not None
            ok = await self._bridge.disconnect_server(server_id)
            return TaskResult(task_id=task_id, success=ok)
        else:
            if self._bridge:
                await self._bridge.disconnect_all()
            return TaskResult(task_id=task_id, success=True)

    async def _connect_all_servers(
        self, task_id: str = "internal"
    ) -> TaskResult:
        assert self._bridge is not None
        results = await self._bridge.connect_all()
        return TaskResult(task_id=task_id, success=True, result=results)
