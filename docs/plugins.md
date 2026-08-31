# Plugin & Hook System

The Plugin & Hook System provides the pluggable architecture for the AGI/ASI Harness, enabling extensibility without modifying core code.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Plugin Manager                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │  Discovery  │  │  Lifecycle   │  │  Isolation       │       │
│  │  (loader)   │  │  (init/      │  │  (sandbox,       │       │
│  │             │  │   shutdown)  │  │   rollback)      │       │
│  └─────────────┘  └──────────────┘  └──────────────────┘       │
├─────────────────────────────────────────────────────────────────┤
│                     Hook Registry                                │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │  Register   │  │  Priority    │  │  Fire/Propagate  │       │
│  │  (per event)│  │  Ordering    │  │  (async chain)   │       │
│  └─────────────┘  └──────────────┘  └──────────────────┘       │
├─────────────────────────────────────────────────────────────────┤
│                     Plugin Registry                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │  Register/  │  │  Version     │  │  Dependency      │       │
│  │  Unregister │  │  Management  │  │  Resolution      │       │
│  └─────────────┘  └──────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## Plugin Types

| Type | Purpose | Example |
|------|---------|---------|
| `FrameworkPlugin` | Core infrastructure | Scheduler, Event Bus |
| `SolverPlugin` | Problem-solving strategies | Planner, Reasoner |
| `EvalPlugin` | Metrics and scoring | Accuracy, Performance |
| `MemoryPlugin` | Storage and retrieval | Vector store, Cache |
| `ToolPlugin` | External tool integrations | Web search, Code exec |
| `GuardPlugin` | Safety gates | Content filter, Rate limit |

## Lifecycle

```
[Discovery] → [Loading] → [Initialization] → [Registration] → [Active] → [Shutdown]
```

1. **Discovery**: Plugins are found via filesystem scan, entry points, or config
2. **Loading**: Plugin code is loaded into an isolated environment
3. **Initialization**: Plugin registers capabilities and hooks
4. **Registration**: Plugin appears in the registry
5. **Active**: Plugin can execute capabilities
6. **Shutdown**: Plugin cleans up and unregisters

## Hook Events

| Event | When Fired |
|-------|------------|
| `on_before_execute` | Before a capability is executed |
| `on_after_execute` | After a capability completes |
| `on_error` | When a capability raises an exception |
| `on_feedback` | When feedback is received |
| `on_node_start` | When a workflow node starts |
| `on_node_end` | When a workflow node ends |
| `on_plugin_load` | When a plugin is loaded |
| `on_plugin_unload` | When a plugin is unloaded |
| `on_config_reload` | When configuration is reloaded |

## Usage

### Loading Plugins

```python
from harness.plugins import PluginManager

manager = PluginManager(harness_config={"env": "production"})

# Load from directory
await manager.load_from_directory("/path/to/plugins")

# Load from file
await manager.load_from_file("/path/to/plugin.py")

# Load from config
await manager.load_from_config({
    "plugins": [
        {"module": "my_package.plugins.my_plugin"},
        {"file": "/path/to/other.py"},
    ]
})
```

### Registering Hooks

```python
from harness.plugins import Priority

async def my_hook(event):
    print(f"Event: {event.name}, Data: {event.data}")

manager.hooks.register(
    "on_before_execute",
    my_hook,
    priority=Priority.HIGH,
    plugin_id="my-plugin",
)
```

### Executing Capabilities

```python
result = await manager.execute_capability(
    "hello-world",
    "greet",
    {"name": "World"},
)
if result.success:
    print(result.output)  # "Hello, World!"
```

### Creating a Plugin

```python
from harness.plugins.base import (
    ToolPlugin, PluginManifest, PluginType,
    PluginContext, Capability, ExecutionResult,
)

class MyPlugin(ToolPlugin):
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="my-plugin",
            version="1.0.0",
            plugin_type=PluginType.TOOL,
            description="My custom plugin",
        )

    async def initialize(self, context: PluginContext) -> None:
        context.log("info", "Initialized!")

    async def shutdown(self) -> None:
        pass

    def get_capabilities(self) -> list[Capability]:
        return [Capability(name="my_capability")]

    async def execute(self, capability, params, context):
        return ExecutionResult(success=True, output="done")
```

## Dynamic Configuration

The `Config` class provides async configuration with hot-reload:

```python
from harness.config import Config

config = Config(env_prefix="HARNESS_")
await config.load_file("config.yaml")
await config.start_hot_reload()

# Subscribe to changes
config.subscribe(lambda key, old, new: print(f"{key}: {old} -> {new}"))
```

## File Structure

```
src/harness/
├── config.py              # Dynamic async configuration
└── plugins/
    ├── __init__.py        # Public API exports
    ├── base.py            # Plugin base classes and types
    ├── hooks.py           # Hook registry and events
    ├── loader.py          # Plugin discovery and loading
    ├── manager.py         # Plugin lifecycle management
    ├── registry.py        # Plugin registration and lookup
    └── examples/
        └── __init__.py    # Example plugins
```

## Testing

```bash
pytest tests/test_plugins.py -v
pytest tests/test_config.py -v
```

## Dependencies

- Python >= 3.11
- PyYAML (optional, for YAML config files)
- pytest >= 7.0 (dev)
- pytest-asyncio >= 0.21 (dev)
