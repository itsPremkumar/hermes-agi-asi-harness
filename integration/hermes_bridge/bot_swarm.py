"""
Bot Swarm — manages 26 specialized bot profiles for Hermes integration.

Each bot is a Hermes profile with a specific model, toolset, and role.
Hermes can spawn these bots as subagents via delegate_task.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class BotProfile:
    """A bot profile configuration."""
    name: str
    model: str
    provider: str
    role: str
    phase: str
    tools: list[str]
    description: str
    can_spawn_subagents: bool = False


# The 26 bot profiles
BOT_PROFILES: dict[str, BotProfile] = {
    "harness-planner": BotProfile(
        name="harness-planner",
        model="minimax/minimax-m3:free",
        provider="openrouter",
        role="Master Planner — 6-plan portfolios, DAG orchestration",
        phase="planning",
        tools=["web_search", "browser", "file_read", "file_write", "session_search", "memory", "skills", "todo", "clarify"],
        description="Creates 6-plan portfolios with DAGs, decomposes ASI harness into phases",
        can_spawn_subagents=True,
    ),
    "harness-strategist": BotProfile(
        name="harness-strategist",
        model="thinkingmachines/inkling:free",
        provider="openrouter",
        role="Strategist — 100x foresight, scenario trees",
        phase="strategy",
        tools=["web_search", "browser", "file_read", "file_write", "session_search", "memory", "skills"],
        description="Performs 100x horizon foresight, builds scenario trees",
        can_spawn_subagents=True,
    ),
    "harness-architect": BotProfile(
        name="harness-architect",
        model="nvidia/nemotron-3-ultra-550b-a55b:free",
        provider="openrouter",
        role="System Architect — kernel + plugin architecture",
        phase="architecture",
        tools=["web_search", "browser", "file_read", "file_write", "terminal", "session_search", "memory", "skills"],
        description="Designs harnix kernel lifecycle, plugin system, multi-agent topologies",
        can_spawn_subagents=True,
    ),
    "harness-researcher": BotProfile(
        name="harness-researcher",
        model="nvidia/nemotron-3.5-lightning:free",
        provider="openrouter",
        role="Deep Researcher — evidence graphs, 5-parallel search",
        phase="research",
        tools=["web_search", "browser", "file_read", "file_write", "session_search", "memory", "skills"],
        description="Conducts 5-parallel searches, builds evidence graphs",
        can_spawn_subagents=True,
    ),
    "harness-trendwatcher": BotProfile(
        name="harness-trendwatcher",
        model="z-ai/glm-5.2:free",
        provider="openrouter",
        role="Trend Watcher — AI landscape monitoring",
        phase="intelligence",
        tools=["web_search", "browser", "file_read", "file_write", "session_search", "memory", "skills"],
        description="Monitors AI agent landscape for new models and techniques",
    ),
    "harness-analyst": BotProfile(
        name="harness-analyst",
        model="nvidia/nemotron-3-super-120b-a12b:free",
        provider="openrouter",
        role="Data Analyst — benchmark analysis, Brier scoring",
        phase="analysis",
        tools=["web_search", "file_read", "file_write", "terminal", "code_execution", "session_search", "memory", "skills"],
        description="Analyzes benchmark results, tracks capability metrics",
        can_spawn_subagents=True,
    ),
    "harness-coder": BotProfile(
        name="harness-coder",
        model="meituan/longcat-2.0:free",
        provider="openrouter",
        role="Core Coder — kernel, plugins, verification engine",
        phase="implementation",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills", "todo"],
        description="Implements harnix kernel, plugins, verification engine",
        can_spawn_subagents=True,
    ),
    "harness-kernel-dev": BotProfile(
        name="harness-kernel-dev",
        model="nvidia/nemotron-3-ultra-550b-a55b:free",
        provider="openrouter",
        role="Kernel Developer — harnix runtime, state machine",
        phase="kernel",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Builds harnix runtime kernel, state machine, event bus",
        can_spawn_subagents=True,
    ),
    "harness-plugin-forge": BotProfile(
        name="harness-plugin-forge",
        model="nvidia/nemotron-3.5-lightning:free",
        provider="openrouter",
        role="Plugin Forge — all 80+ plugins",
        phase="plugins",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Builds all 80+ plugins, plugin manager, capability registry",
        can_spawn_subagents=True,
    ),
    "harness-fullstack": BotProfile(
        name="harness-fullstack",
        model="upstage/solar-pro4:free",
        provider="nous",
        role="Full-Stack Developer — end-to-end integration",
        phase="integration",
        tools=["terminal", "file_read", "file_write", "code_execution", "web_search", "session_search", "memory", "skills"],
        description="Integrates kernel, plugins, API layer, and dashboard",
        can_spawn_subagents=True,
    ),
    "harness-safety-governor": BotProfile(
        name="harness-safety-governor",
        model="thinkingmachines/inkling-small:free",
        provider="openrouter",
        role="Safety Governor — R0-R6, 22 invariants",
        phase="safety",
        tools=["web_search", "browser", "file_read", "file_write", "session_search", "memory", "skills"],
        description="Implements R0-R6 risk classification, 22 safety invariants",
    ),
    "harness-verifier": BotProfile(
        name="harness-verifier",
        model="nvidia/nemotron-3-super-120b-a12b:free",
        provider="openrouter",
        role="Verifier — triple verification, 12 gates",
        phase="verification",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Performs triple verification: Builder → Independent → Formal",
        can_spawn_subagents=True,
    ),
    "harness-critic": BotProfile(
        name="harness-critic",
        model="upstage/solar-pro4:free",
        provider="nous",
        role="Critical Reviewer — red-team, bias detection",
        phase="evaluation",
        tools=["web_search", "browser", "file_read", "file_write", "session_search", "memory", "skills"],
        description="Performs red-team analysis, adversarial testing, bias detection",
    ),
    "harness-test-master": BotProfile(
        name="harness-test-master",
        model="stepfun/step-3.7-flash:free",
        provider="nous",
        role="Test Master — all tests, 100% pass rate",
        phase="testing",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Writes all unit, integration, and regression tests",
        can_spawn_subagents=True,
    ),
    "harness-devops": BotProfile(
        name="harness-devops",
        model="poolside/laguna-s-2.1:free",
        provider="openrouter",
        role="DevOps Engineer — CI/CD, Docker, K8s",
        phase="deployment",
        tools=["terminal", "file_read", "file_write", "cronjob", "session_search", "memory", "skills"],
        description="Sets up CI/CD pipelines, Docker, Kubernetes",
    ),
    "harness-mcp-integrator": BotProfile(
        name="harness-mcp-integrator",
        model="z-ai/glm-5.2:free",
        provider="openrouter",
        role="MCP Integrator — MCP server/client, A2A protocol",
        phase="integration",
        tools=["terminal", "file_read", "file_write", "code_execution", "web_search", "session_search", "memory", "skills"],
        description="Builds MCP server/client, A2A protocol implementation",
        can_spawn_subagents=True,
    ),
    "harness-rag-optimizer": BotProfile(
        name="harness-rag-optimizer",
        model="poolside/laguna-xs-2.1:free",
        provider="openrouter",
        role="RAG Optimizer — retrieval-augmented generation",
        phase="memory",
        tools=["terminal", "file_read", "file_write", "code_execution", "web_search", "session_search", "memory", "skills"],
        description="Builds RAG pipeline, knowledge graph, semantic index",
        can_spawn_subagents=True,
    ),
    "harness-data-engineer": BotProfile(
        name="harness-data-engineer",
        model="meituan/longcat-2.0:free",
        provider="openrouter",
        role="Data Engineer — SQLite+FTS5, event sourcing",
        phase="infrastructure",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Builds state stores, checkpointing, event sourcing",
        can_spawn_subagents=True,
    ),
    "harness-optimizer": BotProfile(
        name="harness-optimizer",
        model="tencent/hy3:free",
        provider="nous",
        role="Performance Optimizer — latency, caching, parallel execution",
        phase="optimization",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Reduces latency, implements caching, enables parallel execution",
        can_spawn_subagents=True,
    ),
    "harness-documenter": BotProfile(
        name="harness-documenter",
        model="thinkingmachines/inkling-small:free",
        provider="openrouter",
        role="Documenter — ARCHITECTURE.md, API docs",
        phase="documentation",
        tools=["web_search", "browser", "file_read", "file_write", "session_search", "memory", "skills"],
        description="Writes architecture docs, API documentation, evidence graphs",
    ),
    "harness-reviewer": BotProfile(
        name="harness-reviewer",
        model="meituan/longcat-2.0:free",
        provider="openrouter",
        role="Code Reviewer — quality gates",
        phase="review",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Reviews code, enforces quality gates",
    ),
    "harness-tester": BotProfile(
        name="harness-tester",
        model="meituan/longcat-2.0:free",
        provider="openrouter",
        role="Tester — unit/integration tests",
        phase="testing",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Writes and runs unit/integration tests",
    ),
    "harness-security": BotProfile(
        name="harness-security",
        model="meituan/longcat-2.0:free",
        provider="openrouter",
        role="Security Engineer — security hardening",
        phase="security",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Security hardening, vulnerability scanning",
    ),
    "harness-debugger": BotProfile(
        name="harness-debugger",
        model="meituan/longcat-2.0:free",
        provider="openrouter",
        role="Debug Master — root cause analysis",
        phase="debugging",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Root cause analysis, debugging",
    ),
    "harness-integrator": BotProfile(
        name="harness-integrator",
        model="meituan/longcat-2.0:free",
        provider="openrouter",
        role="System Integrator — component integration",
        phase="integration",
        tools=["terminal", "file_read", "file_write", "code_execution", "session_search", "memory", "skills"],
        description="Integrates components into cohesive system",
    ),
    "harness-innovator": BotProfile(
        name="harness-innovator",
        model="meituan/longcat-2.0:free",
        provider="openrouter",
        role="Innovation Engine — novel technique discovery",
        phase="innovation",
        tools=["web_search", "browser", "file_read", "file_write", "session_search", "memory", "skills"],
        description="Discovers novel techniques and approaches",
    ),
}


class BotSwarm:
    """
    Manages the 26 specialized bot profiles.
    
    Hermes can spawn these bots as subagents via delegate_task.
    Each bot runs in its own isolated context with its own model and tools.
    """
    
    def __init__(self, config: dict, profiles: dict[str, BotProfile]):
        self.config = config
        self.profiles = profiles
        self._active_bots: dict[str, dict] = {}
    
    @classmethod
    async def create(cls, config: dict, kernel: Any) -> "BotSwarm":
        """Create the bot swarm."""
        profiles = {}
        profiles_dir = config.get("profiles_dir", os.path.expanduser("~/.hermes/profiles"))
        
        # Load profiles from disk if they exist
        for name, profile in BOT_PROFILES.items():
            profile_path = os.path.join(profiles_dir, name, "config.yaml")
            if os.path.exists(profile_path):
                profiles[name] = profile
            else:
                # Use default profile
                profiles[name] = profile
        
        return cls(config, profiles)
    
    async def spawn(self, bot_name: str, command: str) -> dict:
        """
        Spawn a bot as a subagent.
        
        Args:
            bot_name: Name of the bot profile (e.g., "harness-coder")
            command: What the bot should do
        
        Returns:
            Bot execution result
        """
        if bot_name not in self.profiles:
            return {
                "error": f"Bot '{bot_name}' not found",
                "available_bots": list(self.profiles.keys()),
            }
        
        profile = self.profiles[bot_name]
        
        # In production, this would use delegate_task to spawn a subagent
        # For now, return the spawn configuration
        spawn_config = {
            "bot_name": bot_name,
            "model": profile.model,
            "provider": profile.provider,
            "role": profile.role,
            "tools": profile.tools,
            "command": command,
            "status": "spawned",
        }
        
        self._active_bots[bot_name] = spawn_config
        
        return {
            "status": "spawned",
            "bot": bot_name,
            "model": profile.model,
            "command": command,
            "message": f"Bot '{bot_name}' spawned with model '{profile.model}'",
        }
    
    async def status(self) -> dict:
        """Get swarm status."""
        return {
            "total_profiles": len(self.profiles),
            "active_bots": len(self._active_bots),
            "available_bots": list(self.profiles.keys()),
            "active": {name: bot["command"] for name, bot in self._active_bots.items()},
        }
    
    async def health(self) -> dict:
        """Get swarm health."""
        return {
            "status": "healthy",
            "profiles_loaded": len(self.profiles),
            "active_bots": len(self._active_bots),
        }
    
    def get_profile(self, bot_name: str) -> Optional[BotProfile]:
        """Get a bot profile."""
        return self.profiles.get(bot_name)
    
    def list_bots(self) -> list[dict]:
        """List all available bots."""
        return [
            {
                "name": name,
                "model": profile.model,
                "role": profile.role,
                "phase": profile.phase,
            }
            for name, profile in self.profiles.items()
        ]
