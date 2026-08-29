"""WASM-based plugin system for agent extensions."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class PluginManifest:
    """Plugin metadata and configuration."""
    name: str
    version: str
    description: str = ""
    author: str = ""
    entry_point: str = "main"
    permissions: list[str] | None = None
    dependencies: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "entry_point": self.entry_point,
            "permissions": self.permissions or [],
            "dependencies": self.dependencies or [],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest:
        return cls(**data)


@dataclass
class Plugin:
    """A loaded plugin instance."""
    manifest: PluginManifest
    path: Path
    wasm_bytes: bytes | None = None
    python_module: Any = None
    loaded: bool = False
    checksum: str = ""

    def __post_init__(self) -> None:
        if self.wasm_bytes:
            self.checksum = hashlib.sha256(self.wasm_bytes).hexdigest()


class PluginError(Exception):
    """Raised when plugin operations fail."""
    pass


class PluginManager:
    """Manages loading, validation, and execution of plugins."""

    def __init__(self, plugin_dir: str | None = None) -> None:
        self.plugin_dir = Path(plugin_dir) if plugin_dir else Path(tempfile.mkdtemp(prefix="agentos_plugins_"))
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self._plugins: dict[str, Plugin] = {}
        self._hooks: dict[str, list[Callable[..., Any]]] = {}

    def register_hook(self, event: str, callback: Callable[..., Any]) -> None:
        """Register a hook for plugin events."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def _trigger_hook(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Trigger all hooks for an event."""
        for callback in self._hooks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception:
                pass

    def load_from_file(self, path: str | Path) -> Plugin:
        """Load a plugin from a file path."""
        path = Path(path)
        if not path.exists():
            raise PluginError(f"Plugin file not found: {path}")

        if path.suffix == ".json":
            return self._load_python_plugin(path)
        elif path.suffix in (".wasm", ".wat"):
            return self._load_wasm_plugin(path)
        else:
            raise PluginError(f"Unsupported plugin format: {path.suffix}")

    def load_from_manifest(self, manifest: PluginManifest,
                           code: bytes | None = None) -> Plugin:
        """Load a plugin from a manifest and optional code bytes."""
        plugin_path = self.plugin_dir / f"{manifest.name}-{manifest.version}"
        plugin_path.mkdir(parents=True, exist_ok=True)

        # Write manifest
        manifest_path = plugin_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))

        # Write code if provided
        if is_wasm := code and (manifest.entry_point.endswith(".wasm") or
                                self._looks_like_wasm(code)):
            code_path = plugin_path / "plugin.wasm"
            code_path.write_bytes(code)
            plugin = Plugin(
                manifest=manifest,
                path=plugin_path,
                wasm_bytes=code,
            )
        else:
            # Treat as Python plugin
            code_path = plugin_path / "plugin.py"
            if code:
                code_path.write_bytes(code)
            plugin = Plugin(manifest=manifest, path=plugin_path)

        plugin.loaded = True
        self._plugins[manifest.name] = plugin
        self._trigger_hook("loaded", plugin)
        return plugin

    def _load_python_plugin(self, path: Path) -> Plugin:
        """Load a Python-based plugin."""
        import importlib.util

        manifest_data = json.loads(path.read_text())
        manifest = PluginManifest.from_dict(manifest_data)

        # Look for companion .py file
        code_path = path.with_suffix(".py")
        if code_path.exists():
            spec = importlib.util.spec_from_file_location(
                f"agentos_plugin_{manifest.name}", str(code_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            module = None

        plugin = Plugin(
            manifest=manifest,
            path=path.parent,
            python_module=module,
            loaded=True,
        )
        self._plugins[manifest.name] = plugin
        self._trigger_hook("loaded", plugin)
        return plugin

    def _load_wasm_plugin(self, path: Path) -> Plugin:
        """Load a WASM plugin."""
        wasm_bytes = path.read_bytes()

        # Look for companion manifest
        manifest_path = path.with_suffix(".json")
        if manifest_path.exists():
            manifest = PluginManifest.from_dict(json.loads(manifest_path.read_text()))
        else:
            manifest = PluginManifest(
                name=path.stem,
                version="0.1.0",
                description=f"WASM plugin: {path.stem}",
            )

        plugin = Plugin(
            manifest=manifest,
            path=path.parent,
            wasm_bytes=wasm_bytes,
            loaded=True,
        )
        self._plugins[manifest.name] = plugin
        self._trigger_hook("loaded", plugin)
        return plugin

    def unload(self, name: str) -> bool:
        """Unload a plugin."""
        plugin = self._plugins.pop(name, None)
        if plugin:
            self._trigger_hook("unloaded", plugin)
            return True
        return False

    def get(self, name: str) -> Plugin | None:
        """Get a loaded plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[Plugin]:
        """List all loaded plugins."""
        return list(self._plugins.values())

    def execute(self, name: str, input_data: Any) -> Any:
        """Execute a plugin's main function."""
        plugin = self._plugins.get(name)
        if not plugin:
            raise PluginError(f"Plugin not found: {name}")

        if plugin.python_module:
            func = getattr(plugin.python_module, plugin.manifest.entry_point, None)
            if func is None:
                raise PluginError(
                    f"Entry point '{plugin.manifest.entry_point}' not found "
                    f"in plugin '{name}'"
                )
            return func(input_data)

        if plugin.wasm_bytes:
            return self._execute_wasm(plugin, input_data)

        raise PluginError(f"Plugin '{name}' has no executable code")

    def _execute_wasm(self, plugin: Plugin, input_data: Any) -> Any:
        """Execute a WASM plugin (simplified — requires wasmtime in production)."""
        # In production, this would use wasmtime or similar
        # For now, return a placeholder
        return {
            "status": "executed",
            "plugin": plugin.manifest.name,
            "input": input_data,
            "output": None,
            "note": "WASM execution requires wasmtime runtime",
        }

    @staticmethod
    def _looks_like_wasm(data: bytes) -> bool:
        """Check if bytes look like a WASM module."""
        return data[:4] == b"\x00asm"

    def validate(self, name: str) -> list[str]:
        """Validate a plugin's integrity and permissions."""
        plugin = self._plugins.get(name)
        if not plugin:
            return [f"Plugin not found: {name}"]

        issues = []

        # Check checksum
        if plugin.wasm_bytes and plugin.checksum:
            expected = hashlib.sha256(plugin.wasm_bytes).hexdigest()
            if expected != plugin.checksum:
                issues.append("Checksum mismatch — plugin may be corrupted")

        # Check permissions
        dangerous_perms = {"filesystem.write", "network.raw", "process.spawn"}
        if plugin.manifest.permissions:
            for perm in plugin.manifest.permissions:
                if perm in dangerous_perms:
                    issues.append(f"Potentially dangerous permission: {perm}")

        return issues
