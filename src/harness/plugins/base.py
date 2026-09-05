"""
Plugin base classes and type definitions.

Defines the core abstractions for the plugin system:
- Plugin manifest and metadata
- Plugin context passed during initialization
- Plugin type enumeration
- Abstract base classes for all plugin types
- Execution result and capability types
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


class PluginType(enum.Enum):
    """Enumeration of plugin types in the harness."""
    FRAMEWORK = "framework"
    SOLVER = "solver"
    EVAL = "eval"
    MEMORY = "memory"
    TOOL = "tool"
    GUARD = "guard"


@dataclass
class PluginManifest:
    """Plugin metadata and configuration.
    
    Each plugin provides a manifest describing its identity,
    capabilities, permissions, and dependencies.
    """
    name: str
    version: str
    plugin_type: PluginType
    description: str = ""
    author: str = ""
    permissions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    hooks: dict[str, str] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    entry_point: str = ""
    config_schema: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Unique plugin identifier."""
        return f"{self.name}@{self.version}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize manifest to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "type": self.plugin_type.value,
            "description": self.description,
            "author": self.author,
            "permissions": self.permissions,
            "dependencies": self.dependencies,
            "hooks": self.hooks,
            "safety": self.safety,
            "entry_point": self.entry_point,
            "config_schema": self.config_schema,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest:
        """Deserialize manifest from dictionary."""
        return cls(
            name=data["name"],
            version=data["version"],
            plugin_type=PluginType(data["type"]),
            description=data.get("description", ""),
            author=data.get("author", ""),
            permissions=data.get("permissions", []),
            dependencies=data.get("dependencies", []),
            hooks=data.get("hooks", {}),
            safety=data.get("safety", {}),
            entry_point=data.get("entry_point", ""),
            config_schema=data.get("config_schema", {}),
        )


@dataclass
class PluginContext:
    """Context passed to plugins during initialization.
    
    Provides access to harness services, configuration, and
    the plugin's own sandboxed environment.
    """
    plugin_id: str
    config: dict[str, Any] = field(default_factory=dict)
    harness_config: dict[str, Any] = field(default_factory=dict)
    scratch_dir: str = ""
    logger: Any = None
    event_bus: Any = None
    registry: Any = None

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def log(self, level: str, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a message through the harness logger."""
        if self.logger is not None:
            getattr(self.logger, level, lambda *a, **k: None)(message, *args, **kwargs)


@dataclass
class Capability:
    """A capability provided by a plugin."""
    name: str
    description: str = ""
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    returns_schema: dict[str, Any] = field(default_factory=dict)
    rate_limit: Optional[int] = None  # max calls per minute
    timeout: float = 30.0  # seconds


@dataclass
class ExecutionResult:
    """Result of a plugin capability execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def failed(self) -> bool:
        return not self.success

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration": self.duration,
            "metadata": self.metadata,
        }


class Plugin(ABC):
    """Abstract base class for all plugins.
    
    All plugins must implement get_manifest, initialize, and shutdown.
    Plugins provide capabilities and register hooks with the harness.
    """

    def __init__(self) -> None:
        self._context: Optional[PluginContext] = None
        self._initialized: bool = False
        self._active: bool = False

    @abstractmethod
    def get_manifest(self) -> PluginManifest:
        """Return the plugin manifest."""
        ...

    @abstractmethod
    async def initialize(self, context: PluginContext) -> None:
        """Initialize the plugin with the given context."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the plugin and clean up resources."""
        ...

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def context(self) -> Optional[PluginContext]:
        return self._context

    async def _do_initialize(self, context: PluginContext) -> None:
        """Internal initialization wrapper."""
        self._context = context
        await self.initialize(context)
        self._initialized = True
        self._active = True

    async def _do_shutdown(self) -> None:
        """Internal shutdown wrapper."""
        try:
            await self.shutdown()
        finally:
            self._active = False
            self._initialized = False


class FrameworkPlugin(Plugin):
    """Plugin type for framework-level extensions.
    
    Framework plugins provide core infrastructure capabilities
    such as scheduling, resource management, and event bus integration.
    """

    @abstractmethod
    def get_capabilities(self) -> list[Capability]:
        """Return the capabilities this plugin provides."""
        ...

    @abstractmethod
    async def execute(
        self, capability: str, params: dict[str, Any], context: PluginContext
    ) -> ExecutionResult:
        """Execute a capability."""
        ...


class SolverPlugin(Plugin):
    """Plugin type for solver/strategy extensions.
    
    Solver plugins provide problem-solving strategies, planning
    algorithms, and reasoning approaches.
    """

    @abstractmethod
    def get_capabilities(self) -> list[Capability]:
        """Return the capabilities this plugin provides."""
        ...

    @abstractmethod
    async def execute(
        self, capability: str, params: dict[str, Any], context: PluginContext
    ) -> ExecutionResult:
        """Execute a capability."""
        ...


class EvalPlugin(Plugin):
    """Plugin type for evaluation extensions.
    
    Eval plugins provide metrics, scoring, and assessment
    capabilities for measuring agent performance.
    """

    @abstractmethod
    def get_capabilities(self) -> list[Capability]:
        """Return the capabilities this plugin provides."""
        ...

    @abstractmethod
    async def execute(
        self, capability: str, params: dict[str, Any], context: PluginContext
    ) -> ExecutionResult:
        """Execute a capability."""
        ...


class MemoryPlugin(Plugin):
    """Plugin type for memory extensions.
    
    Memory plugins provide storage, retrieval, and management
    of agent memory and knowledge.
    """

    @abstractmethod
    def get_capabilities(self) -> list[Capability]:
        """Return the capabilities this plugin provides."""
        ...

    @abstractmethod
    async def execute(
        self, capability: str, params: dict[str, Any], context: PluginContext
    ) -> ExecutionResult:
        """Execute a capability."""
        ...


class ToolPlugin(Plugin):
    """Plugin type for tool extensions.
    
    Tool plugins provide external tool integrations such as
    web search, code execution, file I/O, and API access.
    """

    @abstractmethod
    def get_capabilities(self) -> list[Capability]:
        """Return the capabilities this plugin provides."""
        ...

    @abstractmethod
    async def execute(
        self, capability: str, params: dict[str, Any], context: PluginContext
    ) -> ExecutionResult:
        """Execute a capability."""
        ...


class GuardPlugin(Plugin):
    """Plugin type for safety guard extensions.
    
    Guard plugins provide safety gates, content filtering,
    and constraint enforcement capabilities.
    """

    @abstractmethod
    def get_capabilities(self) -> list[Capability]:
        """Return the capabilities this plugin provides."""
        ...

    @abstractmethod
    async def execute(
        self, capability: str, params: dict[str, Any], context: PluginContext
    ) -> ExecutionResult:
        """Execute a capability."""
        ...
