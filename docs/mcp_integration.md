# MCP Integration Layer

The MCP Integration Layer connects all MCP servers to the harness runtime, enabling agent tool-calling across all MCP-provided capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Harness Runtime                         │
├─────────────────────────────────────────────────────────────┤
│  MCPBridge                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ ToolMapping │  │ Schema Conv │  │  Hooks      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  MCPRegistry              │  MCPAuth                        │
│  ┌─────────────────────┐  │  ┌─────────────────────┐       │
│  │ Server Registration │  │  │ Credential Store    │       │
│  │ Health Tracking     │  │  │ Auth Headers        │       │
│  │ Capability Discovery│  │  │ Token Refresh       │       │
│  └─────────────────────┘  │  └─────────────────────┘       │
├─────────────────────────────────────────────────────────────┤
│  MCPClient                │  MCPStreaming    │  MCPAudit   │
│  ┌─────────────────────┐  │  ┌───────────┐  │  ┌───────┐  │
│  │ Connection Lifecycle│  │  │ Streams   │  │  │ Events│  │
│  │ Tool Invocation     │  │  │ Progress  │  │  │ Export│  │
│  │ Retry & Reconnect   │  │  │ Callbacks │  │  │ Stats │  │
│  └─────────────────────┘  │  └───────────┘  │  └───────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Modules

### MCPRegistry (`registry.py`)

Server registration, health tracking, capability discovery.

```python
from harness.mcp.registry import MCPRegistry, ServerStatus

reg = MCPRegistry()
info = reg.register(
    name="search-server",
    transport="stdio",
    endpoint="python -m search_mcp",
    capabilities=["tools", "resources"],
    tools=["web_search", "fetch"],
    tags={"production"},
)

reg.update_status(info.server_id, ServerStatus.READY)
available = reg.get_available()
```

### MCPClient (`client.py`)

Connection management, tool invocation, error handling.

```python
from harness.mcp.client import MCPClient, ConnectionConfig

config = ConnectionConfig(
    transport="stdio",
    command="python",
    args=["-m", "my_server"],
    call_timeout=30.0,
    max_retries=3,
)

client = MCPClient(config=config, name="my-server")
client.connect()
result = client.call_tool("search", {"query": "hello"})
client.disconnect()
```

### MCPBridge (`bridge.py`)

Maps MCP tools to harness tool calls.

```python
from harness.mcp.bridge import MCPBridge

bridge = MCPBridge(registry)
mapping = bridge.register_tool(
    harness_tool_name="web_search",
    mcp_tool_name="search",
    server_id=info.server_id,
    description="Search the web",
)

result = bridge.call_tool("web_search", {"query": "test"})
```

### MCPAuth (`auth.py`)

Authentication, authorization, credential management.

```python
from harness.mcp.auth import MCPAuth, AuthMethod

auth = MCPAuth()
auth.add_api_key("my-server", "secret-key")
auth.add_bearer_token("my-server", "token123")
headers = auth.get_auth_headers("my-server")
```

### MCPStreaming (`streaming.py`)

Streaming responses, progress updates.

```python
from harness.mcp.streaming import MCPStream, StreamingManager

mgr = StreamingManager()
stream = mgr.create_stream(tool_name="search")
stream.start()
stream.push_progress(0.5, "Processing...")
stream.complete(result={"data": "done"})
```

### MCPAudit (`audit.py`)

Logging, tracing, compliance tracking.

```python
from harness.mcp.audit import MCPAudit, AuditLevel

audit = MCPAudit()
audit.log_tool_call("server", "tool", success=True, duration_ms=150.0)
audit.log_auth("server", "api_key", success=True)
errors = audit.get_errors()
```

## Installation

```bash
pip install mcp
```

## Running Tests

```bash
PYTHONPATH=src python -m pytest tests/test_mcp_*.py -v
```

## Test Coverage

| Module | Tests |
|--------|-------|
| registry.py | 34 |
| client.py | 43 |
| bridge.py | 20 |
| auth.py | 45 |
| streaming.py | 43 |
| audit.py | 35 |
| **Total** | **220** |
