"""Plugin configuration and validation — enhanced with full Config system."""

from __future__ import annotations

import asyncio
import copy
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from pathlib import Path


@dataclass
class PluginConfig:
    """Configuration for a plugin."""
    plugin_id: str
    values: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value

    def merge(self, other: PluginConfig) -> None:
        self.values.update(other.values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "values": copy.deepcopy(self.values),
            "enabled": self.enabled,
            "priority": self.priority,
        }


class ConfigValidator:
    """Validates plugin configurations against schemas."""

    def __init__(self):
        self._lock = threading.RLock()
        self._schemas: dict[str, dict[str, Any]] = {}

    def register_schema(self, plugin_id: str, schema: dict[str, Any]) -> None:
        with self._lock:
            self._schemas[plugin_id] = schema

    def validate(self, plugin_id: str, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a config against its schema. Returns (valid, errors)."""
        with self._lock:
            schema = self._schemas.get(plugin_id)
            if schema is None:
                return True, []  # No schema, no validation

            errors = []
            required = schema.get("required", [])
            properties = schema.get("properties", {})

            # Check required fields
            for req in required:
                if req not in config:
                    errors.append(f"Missing required field: {req}")

            # Check field types
            for key, value in config.items():
                if key in properties:
                    prop = properties[key]
                    expected_type = prop.get("type")
                    if expected_type:
                        type_map = {
                            "string": str,
                            "integer": int,
                            "number": (int, float),
                            "boolean": bool,
                            "array": list,
                            "object": dict,
                        }
                        py_type = type_map.get(expected_type)
                        if py_type and not isinstance(value, py_type):
                            errors.append(f"Field '{key}' expected {expected_type}, got {type(value).__name__}")

                    # Check enum
                    if "enum" in prop and value not in prop["enum"]:
                        errors.append(f"Field '{key}' value '{value}' not in enum {prop['enum']}")

                    # Check min/max
                    if "minimum" in prop and isinstance(value, (int, float)):
                        if value < prop["minimum"]:
                            errors.append(f"Field '{key}' value {value} below minimum {prop['minimum']}")
                    if "maximum" in prop and isinstance(value, (int, float)):
                        if value > prop["maximum"]:
                            errors.append(f"Field '{key}' value {value} above maximum {prop['maximum']}")

            return len(errors) == 0, errors

    def get_schema(self, plugin_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._schemas.get(plugin_id)


@dataclass
class ConfigChangeEvent:
    """Represents a configuration change."""
    key: str
    old_value: Any
    new_value: Any
    timestamp: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return f"ConfigChangeEvent(key={self.key!r}, old={self.old_value!r}, new={self.new_value!r})"


class Config:
    """Dynamic configuration system with pub/sub, snapshots, and env loading."""

    def __init__(self, env_prefix: str = ""):
        self._data: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._subscribers: list[Callable] = []
        self._change_log: list[ConfigChangeEvent] = []
        self._env_prefix = env_prefix

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key (supports dot-separated nested keys)."""
        with self._lock:
            keys = key.split(".")
            current = self._data
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default
            return current

    async def set(self, key: str, value: Any) -> None:
        """Set a value by key (supports dot-separated nested keys)."""
        with self._lock:
            old_value = self.get(key)
            keys = key.split(".")
            current = self._data
            for k in keys[:-1]:
                if k not in current or not isinstance(current[k], dict):
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value

            event = ConfigChangeEvent(key=key, old_value=old_value, new_value=value)
            self._change_log.append(event)

        # Notify subscribers
        for callback in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(key, old_value, value)
                else:
                    callback(key, old_value, value)
            except Exception:
                pass

    def has(self, key: str) -> bool:
        """Check if a key exists."""
        with self._lock:
            keys = key.split(".")
            current = self._data
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return False
            return True

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed."""
        with self._lock:
            old_value = self.get(key)
            keys = key.split(".")
            current = self._data
            for k in keys[:-1]:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return False
            if keys[-1] in current:
                del current[keys[-1]]
                event = ConfigChangeEvent(key=key, old_value=old_value, new_value=None)
                self._change_log.append(event)
                return True
            return False

    async def load_file(self, path: str) -> None:
        """Load configuration from a JSON file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Config file must contain a JSON object")
        for key, value in data.items():
            await self.set(key, value)

    def subscribe(self, callback: Callable) -> Callable:
        """Subscribe to config changes. Returns unsubscribe function."""
        self._subscribers.append(callback)

        def unsubscribe():
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe

    def snapshot(self) -> dict[str, Any]:
        """Create a snapshot of current config."""
        with self._lock:
            return copy.deepcopy(self._data)

    async def restore(self, snapshot: dict[str, Any]) -> None:
        """Restore config from a snapshot."""
        with self._lock:
            self._data = copy.deepcopy(snapshot)

    async def merge(self, other: dict[str, Any]) -> None:
        """Merge a dict into config (deep merge)."""
        def _deep_merge(base: dict, overlay: dict) -> dict:
            result = copy.deepcopy(base)
            for key, value in overlay.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = _deep_merge(result[key], value)
                else:
                    result[key] = copy.deepcopy(value)
            return result
        with self._lock:
            self._data = _deep_merge(self._data, other)
        # Notify subscribers for top-level changes
        for key in other:
            old_val = None
            for cb in self._subscribers:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(key, old_val, other[key])
                    else:
                        cb(key, old_val, other[key])
                except Exception:
                    pass

    def get_change_log(self) -> list[ConfigChangeEvent]:
        """Get the change log."""
        with self._lock:
            return list(self._change_log)

    @property
    def data(self) -> dict[str, Any]:
        """Get a copy of the config data."""
        with self._lock:
            return copy.deepcopy(self._data)

    async def load_env(self) -> int:
        """Load environment variables with the configured prefix."""
        count = 0
        prefix = self._env_prefix
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace("__", ".")
                # Try to parse as number/bool
                parsed_value: Any = value
                if value.lower() in ("true", "false"):
                    parsed_value = value.lower() == "true"
                else:
                    try:
                        parsed_value = int(value)
                    except ValueError:
                        try:
                            parsed_value = float(value)
                        except ValueError:
                            pass
                await self.set(config_key, parsed_value)
                count += 1
        return count

    def __repr__(self) -> str:
        with self._lock:
            return f"Config(keys={len(self._data)})"
