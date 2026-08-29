"""plugin.py — Plugin system for pluggable evolution modules.

All evolutions are pluggable modules that can be registered, discovered,
and hot-swapped at runtime. Plugins implement a common interface and
are loaded into the evolution engine via a registry.

Module API:
- PluginBase: abstract base class for all evolution plugins
- PluginRegistry: discovers and manages plugin instances
- PluginMetadata: metadata for a plugin
- @plugin: decorator to register a class as a plugin
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


@dataclass
class PluginMetadata:
    """Metadata for an evolution plugin."""

    name: str
    version: str
    description: str
    author: str = ""
    level: int = 1  # 1-10, where 10 requires human approval
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "level": self.level,
            "tags": list(self.tags),
            "dependencies": list(self.dependencies),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PluginMetadata":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def requires_approval(self) -> bool:
        """Level 10 plugins require human approval."""
        return self.level >= 10


# ---------------------------------------------------------------------------
# Plugin base
# ---------------------------------------------------------------------------


class PluginBase(ABC):
    """Abstract base class for all evolution plugins.

    Subclass this to create a new evolution plugin. Override the
    `run` method to implement the evolution logic.

    Usage:
        class MyPlugin(PluginBase):
            METADATA = PluginMetadata(name="my_plugin", version="1.0.0", description="...")

            def run(self, state: dict[str, Any]) -> dict[str, Any]:
                # evolution logic
                return new_state
    """

    METADATA: PluginMetadata = None

    def __init__(self) -> None:
        if self.METADATA is None:
            raise ValueError(f"{self.__class__.__name__} must define METADATA")

    @abstractmethod
    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the plugin on the given state. Returns new state."""
        ...

    def validate(self, state: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate that the plugin can run on the given state."""
        return True, []

    def cleanup(self) -> None:
        """Clean up resources after the plugin finishes."""
        pass

    @property
    def name(self) -> str:
        return self.METADATA.name

    @property
    def level(self) -> int:
        return self.METADATA.level

    @property
    def requires_approval(self) -> bool:
        return self.METADATA.requires_approval

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.METADATA.to_dict(),
            "class": self.__class__.__name__,
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class PluginRegistry:
    """Discovers and manages evolution plugins.

    Usage:
        registry = PluginRegistry()
        registry.discover()  # auto-discover plugins in the package
        plugins = registry.list_plugins()
        plugin = registry.get("my_plugin")
    """

    def __init__(self) -> None:
        self._plugins: dict[str, type[PluginBase]] = {}
        self._instances: dict[str, PluginBase] = {}

    def register(self, plugin_class: type[PluginBase]) -> None:
        """Register a plugin class."""
        if not issubclass(plugin_class, PluginBase):
            raise TypeError(f"{plugin_class} must be a subclass of PluginBase")
        if plugin_class.METADATA is None:
            raise ValueError(f"{plugin_class.__name__} must define METADATA")
        name = plugin_class.METADATA.name
        self._plugins[name] = plugin_class

    def unregister(self, name: str) -> bool:
        """Unregister a plugin by name."""
        if name in self._plugins:
            del self._plugins[name]
            self._instances.pop(name, None)
            return True
        return False

    def get(self, name: str) -> PluginBase | None:
        """Get a plugin instance by name."""
        if name not in self._instances and name in self._plugins:
            self._instances[name] = self._plugins[name]()
        return self._instances.get(name)

    def get_class(self, name: str) -> type[PluginBase] | None:
        """Get a plugin class by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginMetadata]:
        """List metadata for all registered plugins."""
        return [cls.METADATA for cls in self._plugins.values()]

    def list_plugins_by_level(self, level: int) -> list[PluginMetadata]:
        """List plugins at a specific level."""
        return [m for m in self.list_plugins() if m.level == level]

    def list_requires_approval(self) -> list[PluginMetadata]:
        """List plugins that require human approval (level >= 10)."""
        return [m for m in self.list_plugins() if m.requires_approval]

    def discover(self, package: str = "evolution") -> int:
        """Auto-discover plugins in the given package.

        Returns the number of plugins discovered.
        """
        count = 0
        try:
            pkg = importlib.import_module(package)
            for _, modname, ispkg in pkgutil.iter_modules(pkg.__path__):
                if ispkg:
                    continue
                try:
                    mod = importlib.import_module(f"{package}.{modname}")
                    for name, obj in inspect.getmembers(mod, inspect.isclass):
                        if (
                            issubclass(obj, PluginBase)
                            and obj is not PluginBase
                            and obj.METADATA is not None
                        ):
                            self.register(obj)
                            count += 1
                except Exception:
                    continue
        except ImportError:
            pass
        return count

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        self._instances.clear()

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        return name in self._plugins

    def __iter__(self):
        return iter(self._plugins.keys())


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def plugin(
    name: str,
    version: str = "1.0.0",
    description: str = "",
    author: str = "",
    level: int = 1,
    tags: Sequence[str] | None = None,
    dependencies: Sequence[str] | None = None,
) -> Callable[[type], type]:
    """Decorator to register a class as a plugin.

    Usage:
        @plugin(name="my_plugin", version="1.0.0", description="...")
        class MyPlugin(PluginBase):
            def run(self, state):
                return state
    """

    def decorator(cls: type) -> type:
        cls.METADATA = PluginMetadata(
            name=name,
            version=version,
            description=description,
            author=author,
            level=level,
            tags=list(tags) if tags else [],
            dependencies=list(dependencies) if dependencies else [],
        )
        return cls

    return decorator


# ---------------------------------------------------------------------------
# Built-in plugins
# ---------------------------------------------------------------------------


@plugin(
    name="identity",
    version="1.0.0",
    description="Identity plugin that returns state unchanged (for testing).",
    level=1,
    tags=["core", "test"],
)
class IdentityPlugin(PluginBase):
    """Returns state unchanged."""

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        return dict(state)


@plugin(
    name="noop",
    version="1.0.0",
    description="No-op plugin that does nothing.",
    level=1,
    tags=["core", "test"],
)
class NoopPlugin(PluginBase):
    """Does nothing."""

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        return state
