"""
Hermes Bridge — Integration layer between Hermes Agent and harnix kernel.

This module makes the harness controllable from Hermes as one unified system.
"""

from __future__ import annotations

__version__ = "2.0.0"

from .controller import KernelController
from .bot_swarm import BotSwarm
from .benchmark_runner import BenchmarkRunner
from .self_improvement import SelfImprovementLoop


class HermesBridge:
    """
    Unified bridge between Hermes Agent and the harnix kernel.
    """
    
    def __init__(
        self,
        kernel: KernelController,
        bots: BotSwarm,
        benchmarks: BenchmarkRunner,
        improvement: SelfImprovementLoop,
    ):
        self.kernel = kernel
        self.bots = bots
        self.benchmarks = benchmarks
        self.improvement = improvement
        self._initialized = False
    
    @classmethod
    async def create(cls, project_path: str | None = None) -> "HermesBridge":
        """Create and initialize the bridge."""
        from .config import load_config
        
        config = load_config(project_path)
        
        kernel = await KernelController.create(config)
        bots = await BotSwarm.create(config, kernel)
        benchmarks = await BenchmarkRunner.create(config, kernel)
        improvement = await SelfImprovementLoop.create(config, kernel, bots, benchmarks)
        
        bridge = cls(kernel, bots, benchmarks, improvement)
        bridge._initialized = True
        
        return bridge
    
    async def dispatch(self, command: str, context: dict | None = None) -> dict:
        """Dispatch a command through the appropriate subsystem."""
        if not self._initialized:
            await self.kernel.initialize()
            self._initialized = True
        
        command = command.strip()
        lower = command.lower()
        
        if lower.startswith("benchmark "):
            bench_name = command[10:].strip().lower()
            return await self.benchmarks.run(bench_name)
        
        if lower.startswith("improve") or lower.startswith("self-improve"):
            return await self.improvement.run()
        
        if lower.startswith("spawn "):
            rest = command[6:].strip()
            if ":" in rest:
                bot_name, bot_command = rest.split(":", 1)
                return await self.bots.spawn(bot_name.strip(), bot_command.strip())
            return {"error": "Usage: spawn bot_name: command"}
        
        if lower.startswith("bot "):
            rest = command[4:].strip()
            parts = rest.split(None, 1)
            if len(parts) == 2:
                return await self.bots.spawn(parts[0], parts[1])
            return {"error": "Usage: bot bot_name command"}
        
        return await self.kernel.run(command, context)
    
    async def run(self, task: str, context: dict | None = None) -> dict:
        """Run a task through the harnix kernel."""
        return await self.kernel.run(task, context)
    
    async def benchmark(self, name: str = "all") -> dict:
        """Run benchmarks."""
        return await self.benchmarks.run(name)
    
    async def spawn_bot(self, bot_name: str, command: str) -> dict:
        """Spawn a bot from the swarm."""
        return await self.bots.spawn(bot_name, command)
    
    async def improve(self) -> dict:
        """Run the self-improvement cycle."""
        return await self.improvement.run()
    
    async def status(self) -> dict:
        """Get full system status."""
        return {
            "kernel": await self.kernel.status(),
            "bots": await self.bots.status(),
            "benchmarks": await self.benchmarks.status(),
            "improvement": await self.improvement.status(),
        }
    
    async def health(self) -> dict:
        """Get health status of all subsystems."""
        results = {}
        try:
            results["kernel"] = await self.kernel.health()
        except Exception as e:
            results["kernel"] = {"status": "error", "error": str(e)}
        try:
            results["bots"] = await self.bots.health()
        except Exception as e:
            results["bots"] = {"status": "error", "error": str(e)}
        try:
            results["benchmarks"] = await self.benchmarks.health()
        except Exception as e:
            results["benchmarks"] = {"status": "error", "error": str(e)}
        try:
            results["improvement"] = await self.improvement.health()
        except Exception as e:
            results["improvement"] = {"status": "error", "error": str(e)}
        return results


__all__ = [
    "KernelController",
    "BotSwarm",
    "BenchmarkRunner",
    "SelfImprovementLoop",
    "HermesBridge",
]
