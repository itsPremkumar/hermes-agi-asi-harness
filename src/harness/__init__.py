"""hermes-agi-asi-harness — plugin framework foundation."""

from __future__ import annotations

__version__ = "1.0.0"

from .config import Config, ConfigChangeEvent, ConfigValidator, PluginConfig
from .dependency_resolver import DependencyGraph, DependencyResolver
from .health import HealthCheckResult, HealthMonitor, HealthStatus
from .lifecycle import LifecycleEvent, LifecycleManager
from .plugin_base import Plugin, PluginMetadata, PluginStatus
from .registry import PluginRegistry
from .versioning import Compatibility, Version, VersionRange

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
