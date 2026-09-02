"""hermes-agi-asi-harness — plugin framework foundation."""

from __future__ import annotations

__version__ = "1.0.0"

from .plugin_base import Plugin, PluginMetadata, PluginStatus
from .registry import PluginRegistry
from .lifecycle import LifecycleManager, LifecycleEvent
from .dependency_resolver import DependencyResolver, DependencyGraph
from .config import PluginConfig, ConfigValidator, Config, ConfigChangeEvent
from .health import HealthMonitor, HealthStatus, HealthCheckResult
from .versioning import Version, VersionRange, Compatibility

__all__ = [
    "Compatibility",
    "Config",
    "ConfigChangeEvent",
    "ConfigValidator",
    "DependencyGraph",
    "DependencyResolver",
    "HealthCheckResult",
    "HealthMonitor",
    "HealthStatus",
    "LifecycleEvent",
    "LifecycleManager",
    "Plugin",
    "PluginConfig",
    "PluginMetadata",
    "PluginRegistry",
    "PluginStatus",
    "Version",
    "VersionRange",
]
