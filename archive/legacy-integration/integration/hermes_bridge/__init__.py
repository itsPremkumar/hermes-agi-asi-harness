"""
Hermes Bridge — Integration layer between Hermes Agent and harnix kernel.

This module makes the harness controllable from Hermes as one unified system.
"""

from __future__ import annotations

__version__ = "2.0.0"

from .controller import KernelController
from .bot_swarm import BotSwarm, BOT_PROFILES
from .benchmark_runner import BenchmarkRunner
from .self_improvement import SelfImprovementLoop
from .discovery import MetaDiscovery
from .dynamic_plugins import DynamicPluginCreator


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
        discovery: MetaDiscovery,
    ):
        self.kernel = kernel
        self.bots = bots
        self.benchmarks = benchmarks
        self.improvement = improvement
        self.discovery = discovery
        self._initialized = False
    
    @classmethod
    async def create(cls, project_path: str | None = None) -> "HermesBridge":
        """Create and initialize the bridge."""
        from .config import load_config
        
        config = load_config(project_path)
        
        # Initialize discovery first
        discovery = await MetaDiscovery.create()
        
        kernel = await KernelController.create(config)
        bots = await BotSwarm.create(config, kernel, discovery)
        benchmarks = await BenchmarkRunner.create(config, kernel)
        improvement = await SelfImprovementLoop.create(config, kernel, bots, benchmarks)
        
        bridge = cls(kernel, bots, benchmarks, improvement, discovery)
        bridge._initialized = True
        
        return bridge
    
    async def dispatch(self, command: str, context: dict | None = None) -> dict:
        """Dispatch a command through the appropriate subsystem."""
        if not self._initialized:
            await self.kernel.initialize()
            self._initialized = True
        
        command = command.strip()
        lower = command.lower()
        
        # Discovery commands
        if lower.startswith("discover"):
            return await self._handle_discover(command[7:].strip())
        
        if lower.startswith("search "):
            query = command[7:].strip()
            results = self.discovery.search(query)
            return {"results": [{"name": r.name, "category": r.category, "description": r.description} for r in results]}
        
        if lower.startswith("find "):
            capability = command[5:].strip()
            results = self.discovery.find_by_capability(capability)
            return {"results": [{"name": r.name, "category": r.category, "description": r.description} for r in results]}
        
        if lower == "list all" or lower == "list features":
            return self._handle_list_all()
        
        # Benchmark commands
        if lower.startswith("benchmark "):
            bench_name = command[10:].strip().lower()
            return await self.benchmarks.run(bench_name)
        
        # Improvement
        if lower.startswith("improve") or lower.startswith("self-improve"):
            return await self.improvement.run()
        
        # Bot commands
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
        
        # Dynamic profile creation
        if lower.startswith("create profile ") or lower.startswith("create bot "):
            return self._handle_create_profile(command)
        
        # Status
        if lower == "status":
            return await self.status()
        
        if lower == "health":
            return await self.health()
        
        # List bots
        if lower == "list bots":
            return {"bots": self.bots.list_bots()}
        
        # List benchmarks
        if lower == "list benchmarks":
            return await self.benchmarks.status()
        
        # List skills
        if lower == "list skills":
            return {"skills": [{"name": s.name, "description": s.description} for s in self.discovery.get_skills()]}
        
        # List MCP tools
        if lower == "list mcp tools" or lower == "list tools":
            return {"tools": [{"name": t.full_name, "description": t.description} for t in self.discovery.get_mcp_tools()]}
        
        # List slash commands
        if lower == "list commands" or lower == "list slash commands":
            return {"commands": [{"name": c.name, "description": c.description, "usage": c.usage} for c in self.discovery.get_slash_commands()]}
        
        # Default: run through kernel
        return await self.kernel.run(command, context)
    
    async def _handle_discover(self, query: str) -> dict:
        """Handle discovery commands."""
        if not query:
            all_features = self.discovery.get_all_features()
            return {
                "categories": {
                    cat: [f.name for f in features]
                    for cat, features in all_features.items()
                },
                "total": sum(len(f) for f in all_features.values()),
            }
        
        results = self.discovery.find_by_capability(query)
        if not results:
            results = self.discovery.search(query)
        
        return {
            "query": query,
            "results": [
                {"name": r.name, "category": r.category, "description": r.description}
                for r in results
            ],
        }
    
    def _handle_create_profile(self, command: str) -> dict:
        """Handle dynamic profile creation."""
        parts = command.split()
        
        name = None
        role = None
        model = "meituan/longcat-2.0:free"
        provider = "nous"
        
        if "profile" in parts:
            idx = parts.index("profile")
            if idx + 1 < len(parts):
                name = parts[idx + 1]
        
        if "role" in parts:
            idx = parts.index("role")
            if idx + 1 < len(parts):
                role = " ".join(parts[idx + 1:])
                if "using" in role:
                    role = role[:role.index("using")].strip()
        
        if "model" in parts:
            idx = parts.index("model")
            if idx + 1 < len(parts):
                model = parts[idx + 1]
        
        if not name:
            return {"error": "Usage: create profile <name> with role <description> [using model <model>]"}
        
        if not role:
            role = f"Dynamic bot for {name}"
        
        profile = self.discovery.create_dynamic_profile(
            name=name,
            role=role,
            model=model,
            provider=provider,
        )
        
        return {
            "status": "created",
            "profile": {
                "name": profile.name,
                "model": profile.model,
                "role": profile.role,
                "tools": profile.tools,
            },
        }
    
    def _handle_list_all(self) -> dict:
        """Handle list all features command."""
        all_features = self.discovery.get_all_features()
        return {
            "features": {
                cat: [{"name": f.name, "description": f.description} for f in features]
                for cat, features in all_features.items()
            },
            "total": sum(len(f) for f in all_features.values()),
        }
    
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
            "discovery": {
                "total_features": len(self.discovery.features),
                "categories": list(set(f.category for f in self.discovery.features.values())),
            },
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
    "BOT_PROFILES",
    "BenchmarkRunner",
    "SelfImprovementLoop",
    "MetaDiscovery",
    "DynamicPluginCreator",
    "HermesBridge",
]
