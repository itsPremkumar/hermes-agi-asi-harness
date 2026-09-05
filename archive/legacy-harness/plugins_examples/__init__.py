"""
Example plugins demonstrating the plugin system.

Includes:
- HelloWorldPlugin: A simple tool plugin
- SafetyGuardPlugin: A guard plugin with content filtering
- MetricsPlugin: A monitoring plugin
"""

from __future__ import annotations

import logging
from typing import Any

from ..base import (
    Plugin,
    PluginManifest,
    PluginContext,
    PluginType,
    ToolPlugin,
    GuardPlugin,
    Capability,
    ExecutionResult,
)


logger = logging.getLogger(__name__)


class HelloWorldPlugin(ToolPlugin):
    """A simple example plugin that says hello."""

    def __init__(self) -> None:
        super().__init__()
        self._call_count = 0

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="hello-world",
            version="1.0.0",
            plugin_type=PluginType.TOOL,
            description="A simple hello world plugin",
            author="Harness Team",
            permissions=[],
            dependencies=[],
            hooks={},
        )

    async def initialize(self, context: PluginContext) -> None:
        context.log("info", "HelloWorldPlugin initialized")
        self._call_count = 0

    async def shutdown(self) -> None:
        logger.info("HelloWorldPlugin shutting down (calls: %d)", self._call_count)

    def get_capabilities(self) -> list[Capability]:
        return [
            Capability(
                name="greet",
                description="Generate a greeting",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name to greet"},
                        "greeting": {"type": "string", "description": "Greeting style"},
                    },
                    "required": ["name"],
                },
            ),
            Capability(
                name="count",
                description="Get the number of greetings issued",
            ),
        ]

    async def execute(
        self, capability: str, params: dict[str, Any], context: PluginContext
    ) -> ExecutionResult:
        if capability == "greet":
            name = params.get("name", "World")
            style = params.get("greeting", "Hello")
            self._call_count += 1
            return ExecutionResult(
                success=True,
                output=f"{style}, {name}!",
            )
        elif capability == "count":
            return ExecutionResult(
                success=True,
                output=self._call_count,
            )
        return ExecutionResult(
            success=False,
            error=f"Unknown capability: {capability}",
        )


class SafetyGuardPlugin(GuardPlugin):
    """A guard plugin that filters harmful content."""

    def __init__(self, blocked_words: list[str] | None = None) -> None:
        super().__init__()
        self._blocked_words = blocked_words or ["harmful", "dangerous", "unsafe"]

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="safety-guard",
            version="1.0.0",
            plugin_type=PluginType.GUARD,
            description="Filters potentially harmful content",
            author="Harness Team",
            permissions=[],
            dependencies=[],
        )

    async def initialize(self, context: PluginContext) -> None:
        # Allow customization via config
        words = context.get_config("blocked_words", [])
        if words:
            self._blocked_words = words
        context.log("info", "SafetyGuardPlugin initialized with %d rules", len(self._blocked_words))

    async def shutdown(self) -> None:
        logger.info("SafetyGuardPlugin shutting down")

    def get_capabilities(self) -> list[Capability]:
        return [
            Capability(
                name="check_content",
                description="Check content for harmful material",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                    },
                    "required": ["content"],
                },
            ),
            Capability(
                name="add_rule",
                description="Add a blocked word",
            ),
        ]

    async def execute(
        self, capability: str, params: dict[str, Any], context: PluginContext
    ) -> ExecutionResult:
        if capability == "check_content":
            content = params.get("content", "")
            violations = [
                word for word in self._blocked_words
                if word.lower() in content.lower()
            ]
            return ExecutionResult(
                success=True,
                output={
                    "safe": len(violations) == 0,
                    "violations": violations,
                },
            )
        elif capability == "add_rule":
            word = params.get("word", "")
            if word and word not in self._blocked_words:
                self._blocked_words.append(word)
            return ExecutionResult(success=True, output=True)
        return ExecutionResult(
            success=False,
            error=f"Unknown capability: {capability}",
        )


class MetricsPlugin(ToolPlugin):
    """A plugin that tracks execution metrics."""

    def __init__(self) -> None:
        super().__init__()
        self._metrics: dict[str, Any] = {
            "executions": 0,
            "errors": 0,
            "total_duration": 0.0,
        }

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="metrics",
            version="1.0.0",
            plugin_type=PluginType.TOOL,
            description="Tracks execution metrics",
            author="Harness Team",
        )

    async def initialize(self, context: PluginContext) -> None:
        self._metrics = {
            "executions": 0,
            "errors": 0,
            "total_duration": 0.0,
        }

    async def shutdown(self) -> None:
        logger.info("MetricsPlugin shutting down: %s", self._metrics)

    def get_capabilities(self) -> list[Capability]:
        return [
            Capability(name="record_execution", description="Record an execution"),
            Capability(name="get_metrics", description="Get current metrics"),
            Capability(name="reset", description="Reset all metrics"),
        ]

    async def execute(
        self, capability: str, params: dict[str, Any], context: PluginContext
    ) -> ExecutionResult:
        if capability == "record_execution":
            self._metrics["executions"] += 1
            if params.get("error"):
                self._metrics["errors"] += 1
            self._metrics["total_duration"] += params.get("duration", 0.0)
            return ExecutionResult(success=True, output=dict(self._metrics))
        elif capability == "get_metrics":
            return ExecutionResult(success=True, output=dict(self._metrics))
        elif capability == "reset":
            self._metrics = {
                "executions": 0,
                "errors": 0,
                "total_duration": 0.0,
            }
            return ExecutionResult(success=True, output=dict(self._metrics))
        return ExecutionResult(
            success=False,
            error=f"Unknown capability: {capability}",
        )


def create_hello_world() -> HelloWorldPlugin:
    """Factory function for HelloWorldPlugin."""
    return HelloWorldPlugin()


def create_safety_guard() -> SafetyGuardPlugin:
    """Factory function for SafetyGuardPlugin."""
    return SafetyGuardPlugin()


def create_metrics() -> MetricsPlugin:
    """Factory function for MetricsPlugin."""
    return MetricsPlugin()
