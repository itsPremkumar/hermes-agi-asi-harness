# ASI Harness — Plugin Manifest & Architecture

## 1. Plugin Manifest (`plugin.yaml`)

This is the single source of truth for routing, safety, and lifecycle. Every plugin in the ASI harness implements the `IPlugin` contract.

```yaml
# plugin.yaml — required in every plugin root
id: safety                    # unique, kebab-case
name: Safety Gate Engine      # human-readable
version: 1.0.0                # semver
description: R0-R6 safety gate suite with fail-closed design

# Capability contract — this is the ROUTING contract
# If you claim it, you must pass the gate suite
capabilities:
  - safety_check
  - rate_limit
  - quota_enforce
  - anomaly_detect

# Safety level this plugin operates at
safety_level: 10              # 0-10 scale (10 = CRITICAL, human approval required)

# Resource isolation
resources:
  rate_limit_rpm: 60
  rate_limit_concurrent: 10
  cpu_quota: "500m"
  memory_quota: "256Mi"
  timeout_seconds: 30

# Lifecycle hooks
lifecycle:
  init: initialize
  execute: execute
  shutdown: shutdown
  health_check: health_check

# Dependencies on other plugins
depends_on: []

# Metadata
author: security-compliance
license: MIT
cost: free                    # free | optional-paid
```

## 2. IPlugin Base Class (`plugins/base.py`)

```python
# plugins/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class TaskResult:
    success: bool
    data: Any
    traces: list[str]
    metrics: dict[str, float]

class IPlugin(ABC):
    """Every plugin implements this contract. No exceptions."""
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def version(self) -> str: ...
    
    @property
    @abstractmethod
    def capabilities(self) -> list[str]: ...
    
    @abstractmethod
    def initialize(self, config: dict) -> None: ...
    
    @abstractmethod
    def execute(self, task: dict) -> TaskResult: ...
    
    @abstractmethod
    def shutdown(self) -> None: ...
    
    @abstractmethod
    def health_check(self) -> bool: ...
```

## 3. Plugin Registry (`plugins/registry.py`)

```python
# plugins/registry.py
from typing import Dict, Optional

class CapabilityNotFound(Exception):
    pass

class CapabilityRegistry:
    """Ground truth for what each plugin can do."""
    
    def __init__(self):
        self._plugins: Dict[str, IPlugin] = {}
        self._capabilities: Dict[str, str] = {}  # capability -> plugin_id
    
    def register(self, plugin: IPlugin) -> None:
        # Validate IPlugin contract
        assert hasattr(plugin, 'name'), "Plugin missing name"
        assert hasattr(plugin, 'capabilities'), "Plugin missing capabilities"
        assert hasattr(plugin, 'execute'), "Plugin missing execute"
        assert hasattr(plugin, 'initialize'), "Plugin missing initialize"
        assert hasattr(plugin, 'shutdown'), "Plugin missing shutdown"
        assert hasattr(plugin, 'health_check'), "Plugin missing health_check"
        
        self._plugins[plugin.name] = plugin
        for cap in plugin.capabilities:
            self._capabilities[cap] = plugin.name
    
    def route(self, task_type: str) -> IPlugin:
        """Route task to first plugin with matching capability."""
        plugin_id = self._capabilities.get(task_type)
        if not plugin_id:
            raise CapabilityNotFound(f"No plugin registered for capability: {task_type}")
        return self._plugins[plugin_id]
    
    def list_plugins(self) -> Dict[str, IPlugin]:
        return self._plugins.copy()
    
    def list_capabilities(self) -> Dict[str, str]:
        return self._capabilities.copy()
```

## 4. Plugin Manager (`plugins/manager.py`)

```python
# plugins/manager.py
import os
import yaml
from pathlib import Path
from typing import Dict, List

class PluginManager:
    """Install, enable, rollback plugins."""
    
    def __init__(self, plugin_dir: str = "harness/plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.registry = CapabilityRegistry()
        self._loaded: Dict[str, IPlugin] = {}
    
    def discover(self) -> List[str]:
        """Scan plugin directory for valid plugin.yaml manifests."""
        plugins = []
        for path in self.plugin_dir.iterdir():
            manifest = path / "plugin.yaml"
            if manifest.exists():
                with open(manifest) as f:
                    config = yaml.safe_load(f)
                plugins.append(config.get("id", path.name))
        return plugins
    
    def load(self, plugin_id: str) -> IPlugin:
        """Load and initialize a plugin by ID."""
        manifest_path = self.plugin_dir / plugin_id / "plugin.yaml"
        with open(manifest_path) as f:
            config = yaml.safe_load(f)
        
        # Dynamic import of plugin module
        module_name = f"harness.plugins.{plugin_id}.plugin"
        import importlib
        module = importlib.import_module(module_name)
        
        # Instantiate plugin class
        plugin_class = getattr(module, config.get("class", "Plugin"))
        plugin = plugin_class()
        
        # Initialize with config
        plugin.initialize(config)
        
        # Register capabilities
        self.registry.register(plugin)
        self._loaded[plugin_id] = plugin
        
        return plugin
    
    def unload(self, plugin_id: str) -> None:
        """Gracefully shutdown and unregister a plugin."""
        if plugin_id in self._loaded:
            self._loaded[plugin_id].shutdown()
            del self._loaded[plugin_id]
    
    def rollback(self, plugin_id: str, version: str) -> None:
        """Rollback plugin to a previous version."""
        # Implementation: restore from backup, reinitialize
        pass
```

## 5. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    ASI Harness Runtime                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Executive Control Plane                     │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │ │
│  │  │ Task     │ │ Safety   │ │ Plugin   │ │ Event    │  │ │
│  │  │ Router   │ │ Gate     │ │ Registry │ │ Stream   │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                               │
│  ┌───────────────────────────┴─────────────────────────────┐ │
│  │                   Plugin Sandbox                         │ │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │ │
│  │  │Safety  │ │Hermes  │ │Formal  │ │Scientific          │ │
│  │  │Plugin  │ │Integr. │ │Reason. │ │Discovery│           │ │
│  │  └────────┘ └────────┘ └────────┘ └────────┘           │ │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │ │
│  │  │Scheduler│ │Kanban  │ │AVO     │ │Custom  │           │ │
│  │  │Plugin  │ │Plugin  │ │Search  │ │Plugins │           │ │
│  │  └────────┘ └────────┘ └────────┘ └────────┘           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                               │
│  ┌───────────────────────────┴─────────────────────────────┐ │
│  │              Hermes Agent Kernel                         │ │
│  │  (Profiles, Memory, Skills, Gateway, Tools)              │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 6. Safety Gate Suite (R0-R6)

| Gate | Purpose | Scope | Failure |
|------|---------|-------|---------|
| R0 — Input Sanitization | Reject malformed/oversized/injection-bearing inputs | All incoming task payloads | Task rejected |
| R1 — Authorization | Verify caller has permission | Every task | Task rejected |
| R2 — Rate Limiting | Prevent runaway loops | Per-profile, per-capability, global | Task rejected |
| R3 — Capability Scoping | Prevent plugin overreach | Plugin dispatch | Task rejected |
| R4 — Resource Quotas | Enforce CPU, memory, API-call limits | Per-execution | Task rejected or killed |
| R5 — Anomaly Detection | Detect behavioral drift | Per-execution and aggregate | Task flagged for review |
| R6 — Semantic Policy | Enforce high-level policy constraints | Pre- and post-execution | Task rejected |

## 7. Capability-Based Routing

Tasks carry a `task_type` field. The control plane routes to the first plugin whose `capabilities` list includes that type. This decouples task specification from plugin implementation.

```python
# Example routing
task = {"type": "safety_check", "payload": {...}}
plugin = registry.route(task["type"])  # Returns Safety Gate Engine
result = plugin.execute(task)
```

## 8. Lifecycle

```
DISCOVER → LOAD → INITIALIZE → ACTIVE → IDLE → UNLOAD → SHUTDOWN
```

- **DISCOVER**: Scan plugin directory, validate checksums
- **LOAD**: Import module, instantiate plugin class
- **INITIALIZE**: Call `plugin.initialize(config)`
- **ACTIVE**: Accepting and executing tasks
- **IDLE**: Healthy but not currently executing
- **UNLOAD**: Remove from registry, drain in-flight
- **SHUTDOWN**: Call `plugin.shutdown()`, release resources

---

**@cto** — this is the manifest + ARCH for T-002. The IPlugin contract matches §2.2 of ARCHITECTURE.md. Review against the R0-R6 gate suite and IPlugin base class. Once approved, @fullstack-dev can start T-001 using this as the foundation.
