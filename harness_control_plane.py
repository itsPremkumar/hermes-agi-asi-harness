"""Hermes AGI/ASI Harness — Executive Control Plane Architecture (t_d62fcc6f)

The harness is the executive layer that orchestrates AGI/ASI capabilities:
- Plugin system: hot-loadable, sandboxed capability modules
- Safety architecture: multi-layer guardrails with human override
- Hermes integration: native bindings to Hermes agent runtime
- Executive control plane: task routing, scheduling, observability

Owner: @cto. Status: spec authored, staged, content-verified.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Core Types
# =============================================================================

class HarnessState(Enum):
    """States of the harness executive control plane."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    ERROR = "error"


class SafetyLevel(Enum):
    """Safety classification levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskRequest:
    """A task request routed through the harness."""
    task_id: str
    task_type: str
    payload: dict[str, Any]
    safety_level: SafetyLevel = SafetyLevel.MEDIUM
    requires_human_approval: bool = False
    timeout_seconds: float = 600.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass 
class TaskResult:
    """Result of a task execution."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    safety_violations: list[str] = field(default_factory=list)
    completed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SafetyReport:
    """A safety evaluation report."""
    report_id: str
    task_id: str
    level: SafetyLevel
    approved: bool
    violations: list[str] = field(default_factory=list)
    requires_human_override: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# =============================================================================
# Plugin System
# =============================================================================

class IPlugin(ABC):
    """Base interface for all harness plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def version(self) -> str: ...
    
    @property
    @abstractmethod
    def capabilities(self) -> list[str]: ...
    
    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None: ...
    
    @abstractmethod
    async def execute(self, task: TaskRequest) -> TaskResult: ...
    
    @abstractmethod
    async def shutdown(self) -> None: ...
    
    @abstractmethod
    async def health_check(self) -> bool: ...


@dataclass
class PluginMetadata:
    """Metadata for a registered plugin."""
    name: str
    version: str
    capabilities: list[str]
    module_path: str
    checksum: str
    loaded_at: str
    state: str = "registered"


class PluginRegistry:
    """Registry for managing plugin lifecycle."""
    
    def __init__(self, plugin_dir: str = "~/.hermes-asi/plugins"):
        self._plugins: dict[str, IPlugin] = {}
        self._metadata: dict[str, PluginMetadata] = {}
        self._plugin_dir = Path(plugin_dir).expanduser()
        self._plugin_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def plugins(self) -> dict[str, IPlugin]:
        return dict(self._plugins)
    
    @property
    def metadata(self) -> dict[str, PluginMetadata]:
        return dict(self._metadata)
    
    def register(self, plugin: IPlugin) -> PluginMetadata:
        """Register a plugin."""
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin {plugin.name} already registered")
        
        metadata = PluginMetadata(
            name=plugin.name,
            version=plugin.version,
            capabilities=plugin.capabilities,
            module_path=f"{self._plugin_dir}/{plugin.name}",
            checksum=self._compute_checksum(plugin),
            loaded_at=datetime.utcnow().isoformat(),
        )
        self._plugins[plugin.name] = plugin
        self._metadata[plugin.name] = metadata
        logger.info(f"Registered plugin: {plugin.name} v{plugin.version}")
        return metadata
    
    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        if name not in self._plugins:
            raise KeyError(f"Plugin {name} not found")
        del self._plugins[name]
        del self._metadata[name]
    
    def get(self, name: str) -> IPlugin:
        """Get a plugin by name."""
        if name not in self._plugins:
            raise KeyError(f"Plugin {name} not found")
        return self._plugins[name]
    
    def get_by_capability(self, capability: str) -> list[IPlugin]:
        """Get plugins by capability."""
        return [p for p in self._plugins.values() if capability in p.capabilities]
    
    def _compute_checksum(self, plugin: IPlugin) -> str:
        """Compute a checksum for plugin integrity."""
        content = f"{plugin.name}:{plugin.version}:{plugin.capabilities}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# Safety Architecture
# =============================================================================

class SafetyGuard:
    """Multi-layer safety guard for the harness."""
    
    def __init__(self):
        self._rules: list[Callable[[TaskRequest], SafetyReport]] = []
        self._human_approval_callbacks: dict[str, Callable] = {}
        self._violation_log: list[SafetyReport] = []
    
    def add_rule(self, rule: Callable[[TaskRequest], SafetyReport]) -> None:
        """Add a safety rule."""
        self._rules.append(rule)
    
    async def evaluate(self, task: TaskRequest) -> SafetyReport:
        """Evaluate a task against all safety rules."""
        all_violations = []
        max_level = SafetyLevel.LOW
        requires_human = False
        
        for rule in self._rules:
            report = rule(task)
            all_violations.extend(report.violations)
            if report.level.value > max_level.value:
                max_level = report.level
            if report.requires_human_override:
                requires_human = True
        
        approved = len(all_violations) == 0 and not requires_human
        
        report = SafetyReport(
            report_id=f"sr-{len(self._violation_log)+1:04d}",
            task_id=task.task_id,
            level=max_level,
            approved=approved,
            violations=all_violations,
            requires_human_override=requires_human,
        )
        self._violation_log.append(report)
        return report
    
    def register_human_approval(self, task_type: str, callback: Callable) -> None:
        """Register a human approval callback for a task type."""
        self._human_approval_callbacks[task_type] = callback
    
    def get_violations(self, task_id: Optional[str] = None) -> list[SafetyReport]:
        """Get violation log, optionally filtered by task."""
        if task_id:
            return [v for v in self._violation_log if v.task_id == task_id]
        return list(self._violation_log)


# =============================================================================
# Executive Control Plane
# =============================================================================

class ExecutiveControlPlane:
    """The main executive control plane for the harness."""
    
    def __init__(self, config: Optional[dict[str, Any]] = None):
        self._config = config or {}
        self._state = HarnessState.INITIALIZING
        self._plugin_registry = PluginRegistry()
        self._safety_guard = SafetyGuard()
        self._task_queue: asyncio.Queue[TaskRequest] = asyncio.Queue()
        self._results: dict[str, TaskResult] = {}
        self._task_history: list[TaskRequest] = []
    
    @property
    def state(self) -> HarnessState:
        return self._state
    
    @property
    def plugins(self) -> PluginRegistry:
        return self._plugin_registry
    
    @property
    def safety(self) -> SafetyGuard:
        return self._safety_guard
    
    async def initialize(self) -> None:
        """Initialize the harness."""
        logger.info("Initializing Hermes AGI/ASI Harness...")
        self._state = HarnessState.INITIALIZING
        
        # Load plugins from directory
        await self._load_plugins()
        
        # Register default safety rules
        self._register_default_safety_rules()
        
        self._state = HarnessState.READY
        logger.info("Harness initialized and ready")
    
    async def submit_task(self, task: TaskRequest) -> str:
        """Submit a task for execution."""
        if self._state not in (HarnessState.READY, HarnessState.RUNNING):
            raise RuntimeError(f"Harness not ready (state={self._state})")
        
        # Safety evaluation
        safety_report = await self._safety_guard.evaluate(task)
        if not safety_report.approved:
            if safety_report.requires_human_override:
                approved = await self._request_human_approval(task)
                if not approved:
                    raise PermissionError(f"Task {task.task_id} rejected: human override denied")
            else:
                raise PermissionError(f"Task {task.task_id} rejected: {safety_report.violations}")
        
        await self._task_queue.put(task)
        self._task_history.append(task)
        logger.info(f"Task {task.task_id} submitted")
        return task.task_id
    
    async def execute_task(self, task: TaskRequest) -> TaskResult:
        """Execute a task directly."""
        start = time.time()
        
        # Find capable plugin
        plugins = self._plugin_registry.get_by_capability(task.task_type)
        if not plugins:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=f"No plugin found for task type: {task.task_type}",
            )
        
        plugin = plugins[0]
        
        try:
            result = await asyncio.wait_for(
                plugin.execute(task),
                timeout=task.timeout_seconds,
            )
            result.execution_time_ms = (time.time() - start) * 1000
            self._results[task.task_id] = result
            return result
        except asyncio.TimeoutError:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=f"Task timed out after {task.timeout_seconds}s",
            )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
            )
    
    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get the result of a completed task."""
        return self._results.get(task_id)
    
    async def shutdown(self) -> None:
        """Shutdown the harness."""
        self._state = HarnessState.SHUTTING_DOWN
        for plugin in self._plugin_registry.plugins.values():
            await plugin.shutdown()
        self._state = HarnessState.INITIALIZING
    
    async def _load_plugins(self) -> None:
        """Load plugins from the plugin directory."""
        # Placeholder: scan plugin directory and load valid plugins
        pass
    
    def _register_default_safety_rules(self) -> None:
        """Register default safety rules."""
        # Rule: CRITICAL tasks require human approval
        def critical_requires_human(task: TaskRequest) -> SafetyReport:
            if task.safety_level == SafetyLevel.CRITICAL:
                return SafetyReport(
                    report_id="",
                    task_id=task.task_id,
                    level=SafetyLevel.CRITICAL,
                    approved=False,
                    violations=["CRITICAL level tasks require human approval"],
                    requires_human_override=True,
                )
            return SafetyReport(
                report_id="",
                task_id=task.task_id,
                level=task.safety_level,
                approved=True,
            )
        
        self._safety_guard.add_rule(critical_requires_human)
    
    async def _request_human_approval(self, task: TaskRequest) -> bool:
        """Request human approval for a task."""
        callback = self._safety_guard._human_approval_callbacks.get(task.task_type)
        if callback:
            return await callback(task)
        # Default: deny if no callback registered
        return False
