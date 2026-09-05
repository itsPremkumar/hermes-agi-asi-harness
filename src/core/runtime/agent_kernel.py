#!/usr/bin/env python3
"""
Hermes Agent Kernel — generic plugin discovery + registry.

Discovers all plugins under /plugins/*/__init__.py that expose a ``Plugin``
class following the core.runtime.plugin_base.PluginBase contract
(load -> start -> run -> stop, plus health() and get_capabilities()).

This is the ONLY module that imports plugins directly. The agent never
imports a plugin — it goes through the kernel by name or capability.
"""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("hermes.agent_kernel")


class AgentKernel:
    """
    Loads plugins, holds a name->instance registry, and exposes capability lookup.
    """

    def __init__(self, plugins_root: str = "plugins"):
        if plugins_root != "plugins":
            self.plugins_root = Path(plugins_root)
        elif Path("src/plugins").exists():
            self.plugins_root = Path("src/plugins")
        else:
            self.plugins_root = Path(plugins_root)
        self._instances: dict[str, Any] = {}
        self._capabilities: dict[str, list[str]] = {}
        self._loaded = False

    # ── Discovery ──────────────────────────────────────────────────────

    def discover(self) -> list[str]:
        """Find plugin module names (directories containing __init__.py)."""
        if not self.plugins_root.exists():
            logger.warning("Plugins root not found: %s", self.plugins_root)
            return []

        found = []
        for entry in sorted(self.plugins_root.iterdir()):
            if entry.is_dir() and (entry / "__init__.py").exists():
                # Skip the package __init__ itself
                if entry.name in ("__pycache__",):
                    continue
                found.append(entry.name)
        return found

    # ── Loading ────────────────────────────────────────────────────────

    async def load_all(self, include: list[str] | None = None,
                       exclude: list[str] | None = None) -> dict[str, bool]:
        """Load and start every discovered plugin (or a filtered subset)."""
        exclude = set(exclude or [])
        names = self.discover()
        results: dict[str, bool] = {}

        # Ensure plugins root is importable
        root_str = str(self.plugins_root.resolve().parent)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)

        for name in names:
            if include and name not in include:
                continue
            if name in exclude:
                continue
            try:
                mod = importlib.import_module(f"plugins.{name}")
                plugin_cls = getattr(mod, "Plugin", None)
                if plugin_cls is None:
                    logger.debug("No Plugin class in plugins.%s — skipping", name)
                    results[name] = False
                    continue

                instance = plugin_cls()
                await instance.load()
                await instance.start()
                self._instances[name] = instance

                # Index capabilities
                caps = []
                try:
                    caps = instance.get_capabilities() or []
                except Exception:
                    caps = []
                for cap in caps:
                    self._capabilities.setdefault(cap, []).append(name)

                results[name] = True
                logger.info("Loaded plugin: %s (%d capabilities)", name, len(caps))
            except Exception as e:
                logger.error("Failed to load plugin %s: %s", name, e)
                results[name] = False

        self._loaded = True
        return results

    async def load_one(self, name: str) -> bool:
        """Load a single plugin by name."""
        try:
            mod = importlib.import_module(f"plugins.{name}")
            plugin_cls = getattr(mod, "Plugin", None)
            if plugin_cls is None:
                return False
            instance = plugin_cls()
            await instance.load()
            await instance.start()
            self._instances[name] = instance
            caps = instance.get_capabilities() or []
            for cap in caps:
                self._capabilities.setdefault(cap, []).append(name)
            return True
        except Exception as e:
            logger.error("Failed to load plugin %s: %s", name, e)
            return False

    # ── Access ─────────────────────────────────────────────────────────

    def get(self, name: str) -> Any | None:
        return self._instances.get(name)

    def get_plugins_by_capability(self, capability: str) -> list[str]:
        return list(self._capabilities.get(capability, []))

    def has(self, name: str) -> bool:
        return name in self._instances

    @property
    def plugins(self) -> dict[str, Any]:
        return dict(self._instances)

    @property
    def capabilities(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self._capabilities.items()}

    # ── Health ─────────────────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        report = {}
        for name, inst in self._instances.items():
            try:
                if hasattr(inst, "health"):
                    report[name] = await inst.health()
                else:
                    report[name] = {"state": "unknown"}
            except Exception as e:
                report[name] = {"state": "error", "error": str(e)}
        healthy = sum(1 for r in report.values() if r.get("healthy") or r.get("state") in ("running", "loaded", "unknown"))
        return {
            "total": len(report),
            "healthy": healthy,
            "plugins": report,
        }

    # ── Shutdown ──────────────────────────────────────────────────────

    async def shutdown(self):
        for name, inst in reversed(list(self._instances.items())):
            try:
                await inst.stop()
            except Exception as e:
                logger.error("Error stopping plugin %s: %s", name, e)
        self._instances.clear()
        self._capabilities.clear()
        self._loaded = False


# Convenience factory
async def build_kernel(plugins_root: str = "plugins",
                       include: list[str] | None = None) -> AgentKernel:
    kernel = AgentKernel(plugins_root)
    await kernel.load_all(include=include)
    return kernel


# The 21 fully-implemented, tested-working plugins this runtime is built on.
WORKING_PLUGINS = [
    "state_manager", "config_manager", "permission_system",
    "shell_tool", "filesystem_tool", "http_tool", "python_tool", "git_tool",
    "rag_engine", "vision_engine", "document_intel",
    "multi_agent_orchestrator", "debate_engine", "swarm_intelligence",
    "evolution_engine", "skill_learner", "memory_curator",
    "permission_sandbox", "audit_logger", "mcp_client", "streaming_output",
]
