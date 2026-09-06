# MCP Integration Layer

MCP (Model Context Protocol) integration for the Hermes AGI/ASI Harness.

## Components

### Server Registry (`server_registry.py`)

Persistent JSON-file registry of MCP server configurations with:
- CRUD operations (register, update, unregister)
- Capability tagging and search
- Health status tracking
- Thread-safe with `RLock`

```python
from core.mcp_integration import MCPServerRegistry

registry = MCPServerRegistry(config_path="~/.hermes-asi/mcp_servers.json")
registry.load()

record = registry.register(
    name="filesystem",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    capabilities=["filesystem", "read"],
)
registry.save()
```

### Tool Bridge (`tool_bridge.py`)

Live bridge connecting registered MCP servers to the harness native tool registry:
- Auto-connects to MCP servers (stdio + HTTP/SSE transports)
- Discovers tools via MCP protocol
- Exposes tools through `call_tool()` with automatic routing
- Retry with exponential backoff
- Health monitoring

```python
from core.mcp_integration import MCPToolBridge, MCPServerRegistry

registry = MCPServerRegistry()
registry.load()

bridge = MCPToolBridge(registry)
await bridge.connect_all()

# Call any MCP tool by name
result = await bridge.call_tool("read_file", {"path": "/tmp/test.txt"})

await bridge.disconnect_all()
```

### Plugin (`plugin.py`)

`IPlugin` entry point wiring registry + bridge into the harness control plane:

```python
from core.mcp_integration import MCPIntegrationPlugin
from harness_control_plane import PluginRegistry

plugin = MCPIntegrationPlugin()
plugin_registry.register(plugin)

await plugin.initialize({
    "config_path": "~/.hermes-asi/mcp_servers.json",
    "auto_connect": True,
})
```

## Supported Transports

| Transport | Protocol | Use Case |
|-----------|----------|----------|
| `stdio` | JSON-RPC over stdio | Local processes |
| `http` | Streamable HTTP | Remote servers |
| `sse` | Server-Sent Events | Remote servers (legacy) |

## Dependencies

- `mcp>=2.0.0` — Anthropic's official MCP SDK
- `httpx>=0.27.0` — HTTP client for HTTP/SSE transports
