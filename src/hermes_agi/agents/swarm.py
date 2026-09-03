"""Bot Swarm — manages specialized agent profiles."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BotProfile:
    """A bot profile."""
    name: str
    model: str
    provider: str
    role: str
    tools: list[str]
    description: str = ""
    can_spawn_subagents: bool = False
    dynamic: bool = False
    created_at: float = field(default_factory=time.time)


# 26 specialized bot profiles
BOT_PROFILES: dict[str, BotProfile] = {
    "harness-planner": BotProfile("harness-planner", "minimax/minimax-m3:free", "openrouter", "Master Planner", ["web_search", "browser", "file_read", "file_write", "memory", "skills", "todo", "clarify"], can_spawn_subagents=True),
    "harness-strategist": BotProfile("harness-strategist", "thinkingmachines/inkling:free", "openrouter", "Strategist", ["web_search", "browser", "file_read", "file_write", "memory", "skills"], can_spawn_subagents=True),
    "harness-architect": BotProfile("harness-architect", "nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter", "System Architect", ["web_search", "browser", "file_read", "file_write", "terminal", "memory", "skills"], can_spawn_subagents=True),
    "harness-researcher": BotProfile("harness-researcher", "nvidia/nemotron-3.5-lightning:free", "openrouter", "Deep Researcher", ["web_search", "browser", "file_read", "file_write", "memory", "skills"], can_spawn_subagents=True),
    "harness-trendwatcher": BotProfile("harness-trendwatcher", "z-ai/glm-5.2:free", "openrouter", "Trend Watcher", ["web_search", "browser", "file_read", "file_write", "memory", "skills"]),
    "harness-analyst": BotProfile("harness-analyst", "nvidia/nemotron-3-super-120b-a12b:free", "openrouter", "Data Analyst", ["web_search", "file_read", "file_write", "terminal", "code_execution", "memory", "skills"], can_spawn_subagents=True),
    "harness-coder": BotProfile("harness-coder", "meituan/longcat-2.0:free", "openrouter", "Core Coder", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills", "todo"], can_spawn_subagents=True),
    "harness-kernel-dev": BotProfile("harness-kernel-dev", "nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter", "Kernel Developer", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"], can_spawn_subagents=True),
    "harness-plugin-forge": BotProfile("harness-plugin-forge", "nvidia/nemotron-3.5-lightning:free", "openrouter", "Plugin Forge", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"], can_spawn_subagents=True),
    "harness-fullstack": BotProfile("harness-fullstack", "upstage/solar-pro4:free", "nous", "Full-Stack Developer", ["terminal", "file_read", "file_write", "code_execution", "web_search", "memory", "skills"], can_spawn_subagents=True),
    "harness-safety-governor": BotProfile("harness-safety-governor", "thinkingmachines/inkling-small:free", "openrouter", "Safety Governor", ["web_search", "browser", "file_read", "file_write", "memory", "skills"]),
    "harness-verifier": BotProfile("harness-verifier", "nvidia/nemotron-3-super-120b-a12b:free", "openrouter", "Verifier", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"], can_spawn_subagents=True),
    "harness-critic": BotProfile("harness-critic", "upstage/solar-pro4:free", "nous", "Critical Reviewer", ["web_search", "browser", "file_read", "file_write", "memory", "skills"]),
    "harness-test-master": BotProfile("harness-test-master", "stepfun/step-3.7-flash:free", "nous", "Test Master", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"], can_spawn_subagents=True),
    "harness-devops": BotProfile("harness-devops", "poolside/laguna-s-2.1:free", "openrouter", "DevOps Engineer", ["terminal", "file_read", "file_write", "cronjob", "memory", "skills"]),
    "harness-mcp-integrator": BotProfile("harness-mcp-integrator", "z-ai/glm-5.2:free", "openrouter", "MCP Integrator", ["terminal", "file_read", "file_write", "code_execution", "web_search", "memory", "skills"], can_spawn_subagents=True),
    "harness-rag-optimizer": BotProfile("harness-rag-optimizer", "poolside/laguna-xs-2.1:free", "openrouter", "RAG Optimizer", ["terminal", "file_read", "file_write", "code_execution", "web_search", "memory", "skills"], can_spawn_subagents=True),
    "harness-data-engineer": BotProfile("harness-data-engineer", "meituan/longcat-2.0:free", "openrouter", "Data Engineer", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"], can_spawn_subagents=True),
    "harness-optimizer": BotProfile("harness-optimizer", "tencent/hy3:free", "nous", "Performance Optimizer", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"], can_spawn_subagents=True),
    "harness-documenter": BotProfile("harness-documenter", "thinkingmachines/inkling-small:free", "openrouter", "Documenter", ["web_search", "browser", "file_read", "file_write", "memory", "skills"]),
    "harness-reviewer": BotProfile("harness-reviewer", "meituan/longcat-2.0:free", "openrouter", "Code Reviewer", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"]),
    "harness-tester": BotProfile("harness-tester", "meituan/longcat-2.0:free", "openrouter", "Tester", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"]),
    "harness-security": BotProfile("harness-security", "meituan/longcat-2.0:free", "openrouter", "Security Engineer", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"]),
    "harness-debugger": BotProfile("harness-debugger", "meituan/longcat-2.0:free", "openrouter", "Debug Master", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"]),
    "harness-integrator": BotProfile("harness-integrator", "meituan/longcat-2.0:free", "openrouter", "System Integrator", ["terminal", "file_read", "file_write", "code_execution", "memory", "skills"]),
    "harness-innovator": BotProfile("harness-innovator", "meituan/longcat-2.0:free", "openrouter", "Innovation Engine", ["web_search", "browser", "file_read", "file_write", "memory", "skills"]),
}


class BotSwarm:
    """Manages bot profiles."""
    
    def __init__(self):
        self._profiles: dict[str, BotProfile] = dict(BOT_PROFILES)
        self._active_bots: dict[str, dict] = {}
    
    def list_bots(self) -> list[dict]:
        return [{"name": p.name, "model": p.model, "role": p.role} for p in self._profiles.values()]
    
    def create_profile(self, name: str, role: str, model: str = "meituan/longcat-2.0:free", **kwargs) -> BotProfile:
        """Create a new bot profile dynamically."""
        profile = BotProfile(name=name, model=model, provider=kwargs.get("provider", "nous"), role=role, tools=kwargs.get("tools", ["web_search", "file_read", "file_write"]), dynamic=True)
        self._profiles[name] = profile
        return profile
    
    async def spawn(self, bot_name: str, command: str) -> dict:
        if bot_name not in self._profiles:
            return {"error": f"Bot '{bot_name}' not found", "available": list(self._profiles.keys())}
        profile = self._profiles[bot_name]
        self._active_bots[bot_name] = {"command": command, "status": "running"}
        return {"bot": bot_name, "model": profile.model, "command": command, "status": "spawned"}
    
    async def status(self) -> dict:
        return {"profiles": len(self._profiles), "active": len(self._active_bots)}
    
    async def health(self) -> dict:
        return {"status": "healthy"}
