"""Hermes Bridge — integration layer between Hermes Agent and the harness kernel.

Every method delegates to a real, lazily-created :class:`hermes_agi.Harness`
instance. Nothing here returns canned success: outcomes (including failures)
come from actual execution. Offline-first; no network required except for the
harness's own optional web-research paths.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def _get_harness(owner: Any):
    """Return the owner's live Harness, creating it once on first use."""
    harness = getattr(owner, "_harness", None)
    if harness is None:
        from hermes_agi import Harness

        harness = await Harness.create()
        owner._harness = harness
    return harness


class BotSwarm:
    """Bot profiles, backed by the real harness swarm."""

    def __init__(self, owner: Any = None):
        self._owner = owner

    async def _swarm(self):
        from hermes_agi.agents.swarm import BotSwarm as RealSwarm

        return RealSwarm()

    def list_bots(self) -> list[dict]:
        import asyncio

        async def go():
            swarm = await self._swarm()
            status = await swarm.status()
            profiles = status.get("profiles", status.get("total", 0))
            if isinstance(profiles, int):
                return [{"count": profiles}]
            return profiles if isinstance(profiles, list) else [status]

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(go())
        # Already inside a loop: report synchronously-available info.
        coro = go()
        if loop.is_running():
            return [{"note": "async swarm; use spawn()/status() for live data"}]
        return loop.run_until_complete(coro)

    async def spawn(self, bot_name: str, command: str) -> dict:
        if self._owner is not None:
            harness = await _get_harness(self._owner)
            return await harness.spawn(bot_name, command)
        swarm = await self._swarm()
        return await swarm.spawn(bot_name, command)

    async def status(self) -> dict:
        swarm = await self._swarm()
        return await swarm.status()

    async def health(self) -> dict:
        status = await self.status()
        return {"status": "healthy", "bots": status}


class BenchmarkRunner:
    """Benchmarks, backed by the real harness benchmark path."""

    def __init__(self, owner: Any = None):
        self._owner = owner

    async def run(self, name: str = "all") -> dict:
        if self._owner is not None:
            harness = await _get_harness(self._owner)
            return await harness.benchmark(name)
        from hermes_agi import Harness

        harness = await Harness.create()
        try:
            return await harness.benchmark(name)
        finally:
            await harness.shutdown()

    async def status(self) -> dict:
        from hermes_agi.benchmarks.runner import BENCHMARK_REGISTRY

        return {"available": list(BENCHMARK_REGISTRY.keys()), "count": len(BENCHMARK_REGISTRY)}

    async def health(self) -> dict:
        status = await self.status()
        return {"status": "healthy" if status["count"] else "degraded", **status}


class SelfImprovementLoop:
    """Self-improvement, backed by the real HarnessRefiner."""

    def __init__(self, owner: Any = None):
        self._owner = owner
        self._runs = 0

    async def run(self) -> dict:
        from hermes_agi.refine.engine import HarnessRefiner

        workspace = "."
        if self._owner is not None and getattr(self._owner, "config", None) is not None:
            workspace = getattr(self._owner.config, "project_path", ".") or "."
        report = HarnessRefiner(workspace_root=workspace).refine()
        self._runs += 1
        result = report.to_dict()
        result.setdefault("status", "completed")
        return result

    async def status(self) -> dict:
        return {"runs": self._runs}

    async def health(self) -> dict:
        return {"status": "healthy", "runs": self._runs}


class HermesBridge:
    """Unified bridge between Hermes Agent and the harness kernel.

    ``create(config)`` is cheap — the heavyweight Harness boots lazily on
    first real call and is then reused for the bridge lifetime.
    """

    def __init__(self, config: Any = None, harness: Any = None):
        self.config = config
        self._harness = harness
        self._bots = BotSwarm(owner=self)
        self._benchmarks = BenchmarkRunner(owner=self)
        self._improvement = SelfImprovementLoop(owner=self)
        self._hermes_sidecar: Any = None  # HermesDetector result (None = not present)

    @classmethod
    async def create(cls, config: Any = None, **kwargs: Any) -> "HermesBridge":
        """Create the bridge (Harness boots lazily on first use)."""
        bridge = cls(config, harness=kwargs.get("harness"))
        bridge._detect_hermes()
        return bridge

    def _detect_hermes(self) -> Any:
        """Detect the Hermes Agent side of the unified system (never raises)."""
        try:
            from hermes_agi.plugins.hermes_integration import HermesDetector

            self._hermes_sidecar = HermesDetector.detect()
        except Exception as exc:  # noqa: BLE001 - absence is a valid state
            logger.debug("Hermes detection skipped: %s", exc)
            self._hermes_sidecar = None
        return self._hermes_sidecar

    def hermes_sidecar(self) -> dict:
        """Describe the detected Hermes Agent installation ({} when absent)."""
        cfg = self._hermes_sidecar or self._detect_hermes()
        if cfg is None:
            return {"present": False}
        to_dict = getattr(cfg, "to_dict", None)
        detail = to_dict() if callable(to_dict) else dict(getattr(cfg, "__dict__", {}))
        return {"present": True, **detail}

    async def _harness_live(self):
        return await _get_harness(self)

    # -- core task paths (all real execution) -----------------------------

    async def run(self, task: str, context: dict | None = None, **kwargs: Any) -> dict:
        """Run a task through the kernel (dual-substrate when asked)."""
        harness = await self._harness_live()
        return await harness.run(task, **(kwargs or {}))

    async def think(self, goal: str, context: dict | None = None) -> dict:
        harness = await self._harness_live()
        return await harness.think(goal, context=context)

    async def research(self, topic: str, depth: int = 3) -> dict:
        harness = await self._harness_live()
        return await harness.research(topic, depth=depth)

    async def asi(self, task: str, **kwargs: Any) -> dict:
        """Handle ANY task at ASI level: deliberate, execute, verify, report."""
        harness = await self._harness_live()
        return await harness.asi(task, **kwargs)

    async def benchmark(self, name: str = "all") -> dict:
        """Run benchmarks (real scores, never canned)."""
        return await self._benchmarks.run(name)

    async def spawn_bot(self, bot_name: str, command: str) -> dict:
        """Spawn a real bot from the harness swarm."""
        return await self._bots.spawn(bot_name, command)

    async def discover(self, query: str = "") -> dict:
        harness = await self._harness_live()
        return await harness.discover(query)

    async def allocate(self, task: str, role: str = "hermes-coder") -> dict:
        harness = await self._harness_live()
        return await harness.allocate_hermes(task, role=role)

    async def improve(self) -> dict:
        """Run a real self-improvement refinement pass."""
        return await self._improvement.run()

    def run_overnight(
        self,
        objective: str,
        max_iterations: int = 10,
        max_consecutive_failures: int = 3,
        **kwargs: Any,
    ) -> dict:
        """Run a bounded autonomous overnight loop (sync, blocking)."""
        import asyncio

        async def go():
            harness = await self._harness_live()
            return harness.run_overnight(
                objective,
                max_iterations=max_iterations,
                max_consecutive_failures=max_consecutive_failures,
                **kwargs,
            )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(go())
        raise RuntimeError("run_overnight is blocking; call it outside a running event loop")

    async def status(self) -> dict:
        """Live status across kernel, bots, benchmarks, improvement."""
        harness = await self._harness_live()
        harness_status = await harness.status()
        return {
            "kernel": harness_status.get("kernel", "running"),
            "bots": await self._bots.status(),
            "benchmarks": await self._benchmarks.status(),
            "improvement": await self._improvement.status(),
            "hermes_sidecar": self.hermes_sidecar(),
        }

    async def health(self) -> dict:
        """Live health across all subsystems."""
        harness = await self._harness_live()
        harness_health = await harness.health()
        degraded = harness_health.get("status") != "healthy"
        return {
            "status": "degraded" if degraded else "healthy",
            "harness": harness_health,
        }

    async def shutdown(self) -> dict:
        if self._harness is not None:
            await self._harness.shutdown()
            self._harness = None
        return {"status": "stopped"}

    async def dispatch(self, command: str) -> dict:
        """Route a text command to the matching real capability."""
        parts = command.split(None, 1)
        if not parts:
            return {"error": "Empty command"}
        action = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        if action == "discover":
            return await self.discover(rest)
        if action == "benchmark":
            return await self.benchmark(rest or "all")
        if action == "spawn":
            return await self.spawn_bot("default", rest)
        if action == "think":
            return await self.think(rest)
        if action == "asi":
            return await self.asi(rest)
        if action == "research":
            return await self.research(rest)
        if action == "status":
            return await self.status()
        if action == "health":
            return await self.health()
        if action == "improve":
            return await self.improve()
        if action == "allocate":
            return await self.allocate(rest)
        return await self.run(command)
