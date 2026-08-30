"""Plugin configuration and validation."""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Any, Optional


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

    def merge(self, other: 'PluginConfig') -> None:
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

    def get_schema(self, plugin_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            return self._schemas.get(plugin_id)
