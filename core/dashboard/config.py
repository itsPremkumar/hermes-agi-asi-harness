"""Config editor — manage system configuration with validation."""
from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConfigValidationError(Exception):
    """Raised when config validation fails."""
    pass


class ConfigScope(str, Enum):
    GLOBAL = "global"
    USER = "user"
    PROJECT = "project"


@dataclass
class ConfigItem:
    key: str
    value: Any
    scope: ConfigScope = ConfigScope.GLOBAL
    description: str = ""
    sensitive: bool = False  # If True, value is masked in output
    metadata: dict[str, Any] = field(default_factory=dict)


class ConfigEditor:
    """Manage system configuration with validation."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._config: dict[str, ConfigItem] = {}
        self._history: list[tuple[str, Any, float]] = []  # (key, old_value, timestamp)
        self._validators: dict[str, callable] = {}

    def set(self, key: str, value: Any, scope: ConfigScope = ConfigScope.GLOBAL,
            description: str = "", sensitive: bool = False) -> ConfigItem:
        # Validate if validator exists
        if key in self._validators:
            try:
                if not self._validators[key](value):
                    raise ConfigValidationError(f"Validation failed for key '{key}'")
            except Exception as e:
                if isinstance(e, ConfigValidationError):
                    raise
                raise ConfigValidationError(f"Validation error for '{key}': {e}")

        old_value = self._config[key].value if key in self._config else None
        self._history.append((key, old_value, __import__("time").time()))

        item = ConfigItem(
            key=key,
            value=value,
            scope=scope,
            description=description,
            sensitive=sensitive,
        )
        self._config[key] = item
        return item

    def get(self, key: str) -> ConfigItem | None:
        return self._config.get(key)

    def get_value(self, key: str, default: Any = None) -> Any:
        item = self._config.get(key)
        return item.value if item else default

    def remove(self, key: str) -> bool:
        if key in self._config:
            del self._config[key]
            return True
        return False

    def list_all(self) -> list[ConfigItem]:
        return list(self._config.values())

    def list_by_scope(self, scope: ConfigScope) -> list[ConfigItem]:
        return [c for c in self._config.values() if c.scope == scope]

    def register_validator(self, key: str, fn: callable) -> None:
        self._validators[key] = fn

    def get_history(self) -> list[tuple[str, Any, float]]:
        return list(self._history)

    def count(self) -> int:
        return len(self._config)

    def get_state(self) -> dict[str, Any]:
        return {
            "total": self.count(),
            "global": len(self.list_by_scope(ConfigScope.GLOBAL)),
            "user": len(self.list_by_scope(ConfigScope.USER)),
            "project": len(self.list_by_scope(ConfigScope.PROJECT)),
        }
