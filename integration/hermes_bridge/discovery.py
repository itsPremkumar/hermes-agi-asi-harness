"""
Meta-Discovery Engine — finds and catalogs every available Hermes feature.

This module dynamically discovers:
- All slash commands
- All MCP servers and their tools
- All skills
- All plugins
- All bot profiles
- All toolsets
- All providers and models

Then makes them all available through a unified API.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredFeature:
    """A discovered Hermes feature."""
    name: str
    category: str  # slash_command, mcp_tool, skill, plugin, bot_profile, toolset, provider, model
    description: str
    source: str  # Where it was found
    capabilities: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class SlashCommand:
    """A Hermes slash command."""
    name: str
    description: str
    usage: str
    category: str


@dataclass
class MCPTool:
    """An MCP tool from a connected server."""
    server: str
    name: str
    full_name: str  # mcp_server_name
    description: str
    parameters: dict[str, Any]


@dataclass
class Skill:
    """A Hermes skill."""
    name: str
    description: str
    path: str
    category: str
    version: str = "1.0"


@dataclass
class BotProfile:
    """A dynamically created bot profile."""
    name: str
    model: str
    provider: str
    role: str
    tools: list[str]
    system_prompt: str
    created_at: float = 0.0
    dynamic: bool = True  # True if created at runtime


class MetaDiscovery:
    """
    Discovers and catalogs all available Hermes features.
    
    Usage:
        discovery = await MetaDiscovery.create()
        features = await discovery.discover_all()
        
        # Find features by capability
        research_tools = discovery.find_by_capability("research")
        
        # Get all slash commands
        commands = discovery.get_slash_commands()
        
        # Get all MCP tools
        tools = discovery.get_mcp_tools()
    """
    
    def __init__(self):
        self.features: dict[str, DiscoveredFeature] = {}
        self.slash_commands: dict[str, SlashCommand] = {}
        self.mcp_tools: dict[str, MCPTool] = {}
        self.skills: dict[str, Skill] = {}
        self.bot_profiles: dict[str, BotProfile] = {}
        self.providers: dict[str, dict] = {}
        self._hermes_home = Path.home() / ".hermes"
    
    @classmethod
    async def create(cls) -> "MetaDiscovery":
        """Create and initialize the discovery engine."""
        discovery = cls()
        await discovery.discover_all()
        return discovery
    
    async def discover_all(self) -> dict[str, list]:
        """Run all discovery methods."""
        results = {}
        
        results["slash_commands"] = await self._discover_slash_commands()
        results["mcp_tools"] = await self._discover_mcp_tools()
        results["skills"] = await self._discover_skills()
        results["plugins"] = await self._discover_plugins()
        results["providers"] = await self._discover_providers()
        results["toolsets"] = await self._discover_toolsets()
        
        return results
    
    async def _discover_slash_commands(self) -> list[SlashCommand]:
        """Discover all available slash commands."""
        commands = [
            SlashCommand("help", "Show help information", "/help", "general"),
            SlashCommand("status", "Show system status", "/status", "general"),
            SlashCommand("model", "Switch model", "/model <name>", "general"),
            SlashCommand("provider", "Switch provider", "/provider <name>", "general"),
            SlashCommand("reasoning", "Set reasoning level", "/reasoning <level>", "general"),
            SlashCommand("search", "Web search", "/search <query>", "research"),
            SlashCommand("browser", "Open browser", "/browser <url>", "research"),
            SlashCommand("research", "Deep research", "/research <topic>", "research"),
            SlashCommand("plan", "Create plan", "/plan <task>", "planning"),
            SlashCommand("tasks", "Show tasks", "/tasks", "planning"),
            SlashCommand("memory", "Memory operations", "/memory <action>", "memory"),
            SlashCommand("remember", "Store memory", "/remember <text>", "memory"),
            SlashCommand("recall", "Recall memory", "/recall <query>", "memory"),
            SlashCommand("skill", "Skill operations", "/skill <action>", "skills"),
            SlashCommand("skills", "List skills", "/skills", "skills"),
            SlashCommand("plugin", "Plugin operations", "/plugin <action>", "plugins"),
            SlashCommand("plugins", "List plugins", "/plugins", "plugins"),
            SlashCommand("mcp", "MCP operations", "/mcp <action>", "mcp"),
            SlashCommand("bots", "List bots", "/bots", "bots"),
            SlashCommand("bot", "Bot operations", "/bot <name> <action>", "bots"),
            SlashCommand("cron", "Cron operations", "/cron <action>", "automation"),
            SlashCommand("kanban", "Kanban board", "/kanban <action>", "collaboration"),
            SlashCommand("project", "Project operations", "/project <action>", "projects"),
            SlashCommand("session", "Session operations", "/session <action>", "sessions"),
            SlashCommand("config", "Config operations", "/config <action>", "config"),
            SlashCommand("doctor", "System check", "/doctor", "diagnostics"),
            SlashCommand("verify", "Verify setup", "/verify", "diagnostics"),
            SlashCommand("security", "Security audit", "/security", "security"),
            SlashCommand("gateway", "Gateway status", "/gateway", "gateway"),
            SlashCommand("proxy", "Proxy status", "/proxy", "proxy"),
            SlashCommand("desktop", "Desktop app", "/desktop", "desktop"),
            SlashCommand("dashboard", "Web dashboard", "/dashboard", "dashboard"),
            SlashCommand("tui", "Terminal UI", "/tui", "tui"),
            SlashCommand("gui", "GUI mode", "/gui", "gui"),
            SlashCommand("setup", "Setup wizard", "/setup", "setup"),
            SlashCommand("login", "Login", "/login <provider>", "auth"),
            SlashCommand("logout", "Logout", "/logout <provider>", "auth"),
            SlashCommand("auth", "Auth status", "/auth", "auth"),
            SlashCommand("send", "Send message", "/send <message>", "messaging"),
            SlashCommand("sync", "Sync skills", "/sync", "sync"),
            SlashCommand("import", "Import", "/import <path>", "import"),
            SlashCommand("export", "Export", "/export <path>", "export"),
            SlashCommand("worktree", "Worktree ops", "/worktree <action>", "git"),
            SlashCommand("secrets", "Secrets mgmt", "/secrets <action>", "secrets"),
            SlashCommand("hooks", "Hooks mgmt", "/hooks <action>", "hooks"),
            SlashCommand("approvals", "Approvals", "/approvals", "approvals"),
            SlashCommand("pause", "Pause all", "/pause", "control"),
            SlashCommand("resume", "Resume all", "/resume", "control"),
            SlashCommand("update", "Update Hermes", "/update", "update"),
            SlashCommand("uninstall", "Uninstall", "/uninstall", "uninstall"),
        ]
        
        for cmd in commands:
            self.slash_commands[cmd.name] = cmd
            self.features[f"slash_{cmd.name}"] = DiscoveredFeature(
                name=cmd.name,
                category="slash_command",
                description=cmd.description,
                source="hermes_builtin",
                capabilities=[cmd.category, cmd.name],
            )
        
        return list(self.slash_commands.values())
    
    async def _discover_mcp_tools(self) -> list[MCPTool]:
        """Discover all MCP tools from configured servers."""
        # Read MCP servers from config
        config_path = self._hermes_home / "config.yaml"
        if not config_path.exists():
            return []
        
        try:
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except Exception:
            return []
        
        mcp_servers = config.get("mcp_servers", {})
        
        for server_name, server_config in mcp_servers.items():
            if not server_config.get("enabled", True):
                continue
            
            # Try to discover tools from the server
            try:
                tools = await self._query_mcp_server(server_name, server_config)
                for tool in tools:
                    self.mcp_tools[tool.full_name] = tool
                    self.features[f"mcp_{tool.full_name}"] = DiscoveredFeature(
                        name=tool.full_name,
                        category="mcp_tool",
                        description=tool.description,
                        source=f"mcp_server:{server_name}",
                        capabilities=self._extract_capabilities(tool.description),
                    )
            except Exception as e:
                logger.warning(f"Failed to discover MCP tools from {server_name}: {e}")
        
        return list(self.mcp_tools.values())
    
    async def _query_mcp_server(self, name: str, config: dict) -> list[MCPTool]:
        """Query an MCP server for its tools."""
        # In production, this would connect to the MCP server
        # For now, return known tools from our harnix server
        if name == "harnix":
            return [
                MCPTool("harnix", "run", "harnix_run", "Run a task through the harnix kernel", {}),
                MCPTool("harnix", "spawn_bot", "harnix_spawn_bot", "Spawn a bot from the swarm", {}),
                MCPTool("harnix", "benchmark", "harnix_benchmark", "Run a benchmark", {}),
                MCPTool("harnix", "invoke_plugin", "harnix_invoke_plugin", "Invoke a plugin", {}),
                MCPTool("harnix", "status", "harnix_status", "Get system status", {}),
                MCPTool("harnix", "health", "harnix_health", "Get health status", {}),
                MCPTool("harnix", "list_bots", "harnix_list_bots", "List bot profiles", {}),
                MCPTool("harnix", "list_benchmarks", "harnix_list_benchmarks", "List benchmarks", {}),
                MCPTool("harnix", "improve", "harnix_improve", "Run self-improvement", {}),
                MCPTool("harnix", "bot_swarm_status", "harnix_bot_swarm_status", "Bot swarm status", {}),
            ]
        
        return []
    
    def _extract_capabilities(self, description: str) -> list[str]:
        """Extract capabilities from a description."""
        capabilities = []
        keywords = {
            "search": ["search", "find", "lookup", "query"],
            "research": ["research", "analyze", "investigate", "study"],
            "code": ["code", "implement", "program", "develop", "build"],
            "plan": ["plan", "strategy", "roadmap", "design"],
            "memory": ["memory", "remember", "recall", "store"],
            "benchmark": ["benchmark", "test", "evaluate", "measure"],
            "deploy": ["deploy", "release", "publish", "ship"],
            "monitor": ["monitor", "watch", "track", "observe"],
            "communicate": ["send", "message", "notify", "alert"],
            "create": ["create", "generate", "make", "build"],
            "modify": ["edit", "update", "change", "modify"],
            "delete": ["delete", "remove", "clean", "purge"],
            "security": ["security", "audit", "scan", "protect"],
            "data": ["data", "database", "query", "extract"],
            "file": ["file", "read", "write", "open"],
            "web": ["web", "browser", "url", "http"],
            "git": ["git", "commit", "push", "pull", "branch"],
            "image": ["image", "photo", "picture", "visual"],
            "audio": ["audio", "sound", "music", "voice"],
            "video": ["video", "movie", "clip", "stream"],
        }
        
        desc_lower = description.lower()
        for capability, words in keywords.items():
            if any(word in desc_lower for word in words):
                capabilities.append(capability)
        
        return capabilities
    
    async def _discover_skills(self) -> list[Skill]:
        """Discover all installed skills."""
        skills_dir = self._hermes_home / "skills"
        if not skills_dir.exists():
            return []
        
        for skill_path in skills_dir.iterdir():
            if not skill_path.is_dir():
                continue
            
            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                continue
            
            try:
                content = skill_md.read_text()
                # Extract frontmatter
                name = skill_path.name
                description = ""
                category = "general"
                version = "1.0"
                
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end != -1:
                        frontmatter = content[3:end]
                        for line in frontmatter.split("\n"):
                            if line.startswith("name:"):
                                name = line.split(":", 1)[1].strip()
                            elif line.startswith("description:"):
                                description = line.split(":", 1)[1].strip().strip('"')
                            elif line.startswith("category:"):
                                category = line.split(":", 1)[1].strip()
                            elif line.startswith("version:"):
                                version = line.split(":", 1)[1].strip()
                
                skill = Skill(
                    name=name,
                    description=description or f"Skill: {name}",
                    path=str(skill_path),
                    category=category,
                    version=version,
                )
                self.skills[name] = skill
                self.features[f"skill_{name}"] = DiscoveredFeature(
                    name=name,
                    category="skill",
                    description=skill.description,
                    source=f"skill:{skill_path}",
                    capabilities=[category, name],
                )
            except Exception as e:
                logger.warning(f"Failed to load skill {skill_path}: {e}")
        
        return list(self.skills.values())
    
    async def _discover_plugins(self) -> list[DiscoveredFeature]:
        """Discover all plugins."""
        plugins_dir = self._hermes_home / "plugins"
        if not plugins_dir.exists():
            return []
        
        plugins = []
        for plugin_path in plugins_dir.iterdir():
            if not plugin_path.is_dir():
                continue
            
            plugin_yaml = plugin_path / "plugin.yaml"
            if plugin_yaml.exists():
                try:
                    import yaml
                    with open(plugin_yaml) as f:
                        plugin_data = yaml.safe_load(f)
                    
                    feature = DiscoveredFeature(
                        name=plugin_data.get("name", plugin_path.name),
                        category="plugin",
                        description=plugin_data.get("description", ""),
                        source=f"plugin:{plugin_path}",
                        capabilities=plugin_data.get("capabilities", []),
                        config=plugin_data,
                    )
                    self.features[f"plugin_{feature.name}"] = feature
                    plugins.append(feature)
                except Exception as e:
                    logger.warning(f"Failed to load plugin {plugin_path}: {e}")
        
        return plugins
    
    async def _discover_providers(self) -> list[dict]:
        """Discover all configured providers."""
        config_path = self._hermes_home / "config.yaml"
        if not config_path.exists():
            return []
        
        try:
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except Exception:
            return []
        
        if not isinstance(config, dict):
            return []
        
        providers = {}
        
        # Primary provider
        model_config = config.get("model", {})
        if isinstance(model_config, dict):
            providers["primary"] = {
                "name": model_config.get("provider", "unknown"),
                "model": model_config.get("default", "unknown"),
            }
        elif isinstance(model_config, str):
            providers["primary"] = {
                "name": model_config,
                "model": "default",
            }
        
        # Fallback providers
        for i, fallback in enumerate(config.get("fallback_providers", [])):
            providers[f"fallback_{i}"] = fallback
        
        # MCP servers as providers
        for name, server_config in config.get("mcp_servers", {}).items():
            providers[f"mcp_{name}"] = {
                "type": "mcp",
                "command": server_config.get("command", ""),
                "args": server_config.get("args", []),
            }
        
        self.providers = providers
        return list(providers.values())
    
    async def _discover_toolsets(self) -> list[str]:
        """Discover all available toolsets."""
        config_path = self._hermes_home / "config.yaml"
        if not config_path.exists():
            return []
        
        try:
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except Exception:
            return []
        
        toolsets = config.get("toolsets", {}).get("enabled", [])
        return toolsets
    
    def find_by_capability(self, capability: str) -> list[DiscoveredFeature]:
        """Find all features that provide a capability."""
        return [
            f for f in self.features.values()
            if capability.lower() in [c.lower() for c in f.capabilities]
        ]
    
    def find_by_category(self, category: str) -> list[DiscoveredFeature]:
        """Find all features in a category."""
        return [f for f in self.features.values() if f.category == category]
    
    def search(self, query: str) -> list[DiscoveredFeature]:
        """Search features by name or description."""
        query_lower = query.lower()
        return [
            f for f in self.features.values()
            if query_lower in f.name.lower() or query_lower in f.description.lower()
        ]
    
    def get_slash_commands(self) -> list[SlashCommand]:
        """Get all slash commands."""
        return list(self.slash_commands.values())
    
    def get_mcp_tools(self) -> list[MCPTool]:
        """Get all MCP tools."""
        return list(self.mcp_tools.values())
    
    def get_skills(self) -> list[Skill]:
        """Get all skills."""
        return list(self.skills.values())
    
    def get_bot_profiles(self) -> list[BotProfile]:
        """Get all bot profiles."""
        return list(self.bot_profiles.values())
    
    def create_dynamic_profile(
        self,
        name: str,
        role: str,
        model: str = "meituan/longcat-2.0:free",
        provider: str = "nous",
        tools: list[str] | None = None,
        system_prompt: str = "",
    ) -> BotProfile:
        """Dynamically create a new bot profile."""
        import time
        
        if not system_prompt:
            system_prompt = f"""You are {name}. Your role: {role}.
You are part of the ASI Harness Bot Swarm.
You work under the direction of the Hermes Agent orchestrator.
Complete your assigned task efficiently and report back."""
        
        if not tools:
            tools = ["web_search", "file_read", "file_write", "terminal"]
        
        profile = BotProfile(
            name=name,
            model=model,
            provider=provider,
            role=role,
            tools=tools,
            system_prompt=system_prompt,
            created_at=time.time(),
            dynamic=True,
        )
        
        self.bot_profiles[name] = profile
        self.features[f"bot_{name}"] = DiscoveredFeature(
            name=name,
            category="bot_profile",
            description=role,
            source="dynamic_creation",
            capabilities=["dynamic", name],
        )
        
        return profile
    
    def get_all_features(self) -> dict[str, list[DiscoveredFeature]]:
        """Get all features organized by category."""
        categories = {}
        for feature in self.features.values():
            if feature.category not in categories:
                categories[feature.category] = []
            categories[feature.category].append(feature)
        return categories
