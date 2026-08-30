"""Tool Registry — standardized tool definitions with schema, validation, rate limiting."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..errors import ToolError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Token bucket rate limiter."""

    max_calls: int = 10
    period: float = 60.0
    _calls: list[float] = field(default_factory=list, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def allow(self) -> bool:
        now = time.time()
        with self._lock:
            self._calls = [t for t in self._calls if now - t < self.period]
            if len(self._calls) < self.max_calls:
                self._calls.append(now)
                return True
            return False

    @property
    def remaining(self) -> int:
        now = time.time()
        with self._lock:
            self._calls = [t for t in self._calls if now - t < self.period]
            return max(0, self.max_calls - len(self._calls))


@dataclass
class ToolSchema:
    """JSON Schema for a tool."""

    type: str = "object"
    properties: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)

    def validate(self, params: dict[str, Any]) -> list[str]:
        errors = []
        for key in self.required:
            if key not in params:
                errors.append(f"Missing required parameter: {key}")
        for key, value in params.items():
            if key in self.properties:
                prop = self.properties[key]
                expected_type = prop.get("type")
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Parameter {key} must be string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Parameter {key} must be number")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Parameter {key} must be boolean")
                elif expected_type == "array" and not isinstance(value, list):
                    errors.append(f"Parameter {key} must be array")
        return errors


class Tool:
    """Registered tool."""

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        schema: ToolSchema,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        self.name = name
        self.description = description
        self.func = func
        self.schema = schema
        self.rate_limiter = rate_limiter
        self.call_count = 0
        self.error_count = 0

    def invoke(self, **kwargs: Any) -> Any:
        errors = self.schema.validate(kwargs)
        if errors:
            raise ToolError(f"Validation failed for {self.name}: {'; '.join(errors)}", tool_name=self.name)
        if self.rate_limiter and not self.rate_limiter.allow():
            raise RateLimitError(f"Rate limit exceeded for {self.name}")
        try:
            result = self.func(**kwargs)
            self.call_count += 1
            return result
        except Exception as e:
            self.error_count += 1
            if isinstance(e, ToolError):
                raise
            raise ToolError(f"Tool {self.name} failed: {e}", tool_name=self.name) from e

    def to_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": self.schema.type,
                "properties": self.schema.properties,
                "required": self.schema.required,
            },
        }


class ToolRegistry:
    """Centralized tool registry."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        parameters: Optional[dict[str, Any]] = None,
        required: Optional[list[str]] = None,
        rate_limit: Optional[tuple[int, float]] = None,
    ) -> Tool:
        schema = ToolSchema(properties=parameters or {}, required=required or [])
        rate_limiter = RateLimiter(*rate_limit) if rate_limit else None
        tool = Tool(name=name, description=description, func=func, schema=schema, rate_limiter=rate_limiter)
        with self._lock:
            if name in self._tools:
                logger.warning(f"Tool {name} already registered, overwriting")
            self._tools[name] = tool
        return tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def invoke(self, name: str, **kwargs: Any) -> Any:
        tool = self.get(name)
        if tool is None:
            raise ToolError(f"Unknown tool: {name}", tool_name=name)
        return tool.invoke(**kwargs)

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._tools.pop(name, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._tools.clear()

    @property
    def count(self) -> int:
        return len(self._tools)
