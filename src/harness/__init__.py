"""hermes-agi-asi-harness — plugin framework foundation."""

from __future__ import annotations

__version__ = "0.1.0"

from harness.plugin_base import Plugin, PluginMetadata, PluginStatus
from harness.registry import PluginRegistry
from harness.lifecycle import LifecycleManager, LifecycleEvent
from harness.dependency_resolver import DependencyResolver, DependencyGraph
from harness.config import PluginConfig, ConfigValidator
from harness.health import HealthMonitor, HealthStatus, HealthCheckResult
from harness.versioning import Version, VersionRange, Compatibility

__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginStatus",
    "PluginRegistry",
    "LifecycleManager",
    "LifecycleEvent",
    "DependencyResolver",
    "DependencyGraph",
    "PluginConfig",
    "ConfigValidator",
    "HealthMonitor",
    "HealthStatus",
    "HealthCheckResult",
    "Version",
    "VersionRange",
    "Compatibility",
]
