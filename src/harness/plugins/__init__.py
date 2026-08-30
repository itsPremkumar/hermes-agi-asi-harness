"""
Plugin & Hook System for the AGI/ASI Harness.

This module provides the pluggable architecture for the harness, enabling
extensibility without modifying core code. It includes:

- Plugin base classes and type definitions
- Plugin Manager for runtime load/register/unregister
- Hook Registry with priority-ordered event handling
- Plugin Discovery via filesystem scan and entry points
- Plugin Isolation with sandboxing and rollback
- Dynamic async configuration with hot-reload
"""

from .base import (
    Plugin,
    PluginManifest,
    PluginContext,
    PluginType,
    FrameworkPlugin,
    SolverPlugin,
    EvalPlugin,
    MemoryPlugin,
    ToolPlugin,
    GuardPlugin,
    ExecutionResult,
    Capability,
)
from .manager import PluginManager
from .loader import PluginLoader
from .hooks import HookRegistry, HookEvent, HookHandler, Priority
from .registry import Registry

__all__ = [
    "Plugin",
    "PluginManifest",
    "PluginContext",
    "PluginType",
    "FrameworkPlugin",
    "SolverPlugin",
    "EvalPlugin",
    "MemoryPlugin",
    "ToolPlugin",
    "GuardPlugin",
    "ExecutionResult",
    "Capability",
    "PluginManager",
    "PluginLoader",
    "HookRegistry",
    "HookEvent",
    "HookHandler",
    "Priority",
    "Registry",
]
