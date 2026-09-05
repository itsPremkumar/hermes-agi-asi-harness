"""
Planning registry — feature/skill catalog backing the Planner.

Split from planning.py: pure data + catalog, no execution. Import here for
new code; planning.py re-exports for backward compatibility.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────── Enums ────────────────────────────


class Phase(str, Enum):
    THINK = "think"
    PLAN = "plan"
    DECIDE = "decide"
    EXECUTE = "execute"
    VERIFY = "verify"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FeatureCategory(str, Enum):
    SLASH_COMMAND = "slash_command"
    TOOL = "tool"
    PLUGIN = "plugin"
    MCP_SERVER = "mcp_server"
    SKILL = "skill"
    BOT = "bot"
    PROVIDER = "provider"
    WORKFLOW = "workflow"


# ──────────────────────────── Data Classes ────────────────────────────


@dataclass
class Feature:
    """An available Hermes feature."""

    name: str
    category: FeatureCategory
    description: str
    capabilities: list[str]
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class Thought:
    """A thinking step."""

    thought_id: str
    content: str
    reasoning: str
    confidence: float
    alternatives: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass
class Decision:
    """A decision about which feature to use."""

    decision_id: str
    feature: Feature
    reason: str
    priority: Priority
    dependencies_satisfied: bool = True
    estimated_cost: float = 0.0
    estimated_time: float = 0.0


@dataclass
class PlanStep:
    """A step in the execution plan."""

    step_id: str
    name: str
    description: str
    feature: Feature
    dependencies: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""
    fallback: str = ""


@dataclass
class ExecutionPlan:
    """The complete execution plan."""

    plan_id: str
    goal: str
    thoughts: list[Thought]
    decisions: list[Decision]
    steps: list[PlanStep]
    estimated_total_time: float
    estimated_total_cost: float
    risk_assessment: dict[str, Any]
    created_at: float


# ──────────────────────────── Feature Registry ────────────────────────────


class FeatureRegistry:
    """
    Dynamically discovers and catalogs all available Hermes features.

    This includes:
    - All slash commands (/search, /plan, /benchmark, etc.)
    - All tools (web_search, browser, file_read, etc.)
    - All plugins (80+ available)
    - All MCP servers
    - All skills
    - All bot profiles
    - All providers
    """

    def __init__(self):
        self.features: dict[str, Feature] = {}
        self._register_all_features()

    def _register_all_features(self):
        """Register all known Hermes features."""

        # ── Slash Commands ──
        slash_commands = [
            ("/search", "Web search", ["search", "research", "web"], ["query"], ["results"]),
            ("/browser", "Open browser", ["web", "browser", "navigate"], ["url"], ["page_content"]),
            ("/research", "Deep research", ["research", "deep", "analyze"], ["topic"], ["report"]),
            ("/plan", "Create plan", ["planning", "strategy", "roadmap"], ["task"], ["plan"]),
            ("/tasks", "Show tasks", ["tasks", "tracking"], [], ["task_list"]),
            (
                "/memory",
                "Memory operations",
                ["memory", "store", "retrieve"],
                ["action"],
                ["result"],
            ),
            ("/remember", "Store memory", ["memory", "store"], ["text"], ["confirmation"]),
            ("/recall", "Recall memory", ["memory", "retrieve"], ["query"], ["memories"]),
            ("/skill", "Skill operations", ["skills", "manage"], ["action"], ["result"]),
            ("/skills", "List skills", ["skills", "list"], [], ["skill_list"]),
            ("/plugin", "Plugin operations", ["plugins", "manage"], ["action"], ["result"]),
            ("/plugins", "List plugins", ["plugins", "list"], [], ["plugin_list"]),
            ("/mcp", "MCP operations", ["mcp", "manage"], ["action"], ["result"]),
            ("/bots", "List bots", ["bots", "list"], [], ["bot_list"]),
            ("/bot", "Bot operations", ["bots", "manage"], ["name", "action"], ["result"]),
            ("/cron", "Cron operations", ["cron", "schedule"], ["action"], ["result"]),
            ("/kanban", "Kanban board", ["kanban", "collaboration"], ["action"], ["result"]),
            ("/project", "Project operations", ["projects", "manage"], ["action"], ["result"]),
            ("/session", "Session operations", ["sessions", "manage"], ["action"], ["result"]),
            ("/config", "Config operations", ["config", "manage"], ["action"], ["result"]),
            ("/doctor", "System check", ["diagnostics", "health"], [], ["diagnostics"]),
            ("/verify", "Verify setup", ["verify", "smoke_test"], [], ["verification"]),
            ("/security", "Security audit", ["security", "audit"], [], ["audit_report"]),
            ("/gateway", "Gateway status", ["gateway", "status"], [], ["status"]),
            ("/proxy", "Proxy status", ["proxy", "status"], [], ["status"]),
            ("/desktop", "Desktop app", ["desktop", "gui"], [], ["app"]),
            ("/dashboard", "Web dashboard", ["dashboard", "web"], [], ["dashboard"]),
            ("/tui", "Terminal UI", ["tui", "terminal"], [], ["tui"]),
            ("/gui", "GUI mode", ["gui", "graphical"], [], ["gui"]),
            ("/setup", "Setup wizard", ["setup", "wizard"], [], ["config"]),
            ("/login", "Login", ["auth", "login"], ["provider"], ["auth_status"]),
            ("/logout", "Logout", ["auth", "logout"], ["provider"], ["auth_status"]),
            ("/auth", "Auth status", ["auth", "status"], [], ["auth_status"]),
            ("/send", "Send message", ["messaging", "send"], ["message"], ["confirmation"]),
            ("/sync", "Sync skills", ["sync", "skills"], [], ["sync_status"]),
            ("/import", "Import", ["import", "restore"], ["path"], ["result"]),
            ("/export", "Export", ["export", "backup"], ["path"], ["result"]),
            ("/worktree", "Worktree ops", ["git", "worktree"], ["action"], ["result"]),
            ("/secrets", "Secrets mgmt", ["secrets", "manage"], ["action"], ["result"]),
            ("/hooks", "Hooks mgmt", ["hooks", "manage"], ["action"], ["result"]),
            ("/approvals", "Approvals", ["approvals", "manage"], [], ["approvals"]),
            ("/pause", "Pause all", ["control", "pause"], [], ["confirmation"]),
            ("/resume", "Resume all", ["control", "resume"], [], ["confirmation"]),
            ("/update", "Update Hermes", ["update", "upgrade"], [], ["update_status"]),
            ("/status", "Show status", ["status", "info"], [], ["status"]),
        ]

        for name, desc, caps, inputs, outputs in slash_commands:
            self.features[name] = Feature(
                name=name,
                category=FeatureCategory.SLASH_COMMAND,
                description=desc,
                capabilities=caps,
                inputs=inputs,
                outputs=outputs,
            )

        # ── Tools ──
        tools = [
            ("web_search", "Search the web", ["search", "web", "research"], ["query"], ["results"]),
            (
                "browser",
                "Control web browser",
                ["web", "browser", "navigate"],
                ["url"],
                ["content"],
            ),
            ("file_read", "Read file", ["file", "read"], ["path"], ["content"]),
            ("file_write", "Write file", ["file", "write"], ["path", "content"], ["confirmation"]),
            (
                "terminal",
                "Execute terminal commands",
                ["terminal", "exec"],
                ["command"],
                ["output"],
            ),
            ("subagents", "Spawn subagents", ["agents", "spawn"], ["task"], ["result"]),
            ("code_execution", "Execute code", ["code", "exec"], ["code"], ["output"]),
            ("vision", "Analyze images", ["vision", "image"], ["image"], ["analysis"]),
            ("speech_to_text", "Convert speech to text", ["stt", "audio"], ["audio"], ["text"]),
            ("text_to_speech", "Convert text to speech", ["tts", "audio"], ["text"], ["audio"]),
            ("computer_use", "Control computer", ["computer", "gui"], ["action"], ["result"]),
            ("mcp_call", "Call MCP tool", ["mcp", "call"], ["server", "tool", "args"], ["result"]),
        ]

        for name, desc, caps, inputs, outputs in tools:
            self.features[name] = Feature(
                name=name,
                category=FeatureCategory.TOOL,
                description=desc,
                capabilities=caps,
                inputs=inputs,
                outputs=outputs,
            )

        # ── Plugins (core capabilities) ──
        plugins = [
            ("memory", "Memory management", ["memory", "store", "retrieve", "search"]),
            ("model_router", "Model routing", ["routing", "models", "fallback"]),
            ("security_core", "Security enforcement", ["security", "enforce", "audit"]),
            ("verification_engine", "Multi-layer verification", ["verify", "prove", "test"]),
            ("evolution", "Self-improvement", ["evolve", "mutate", "improve"]),
            ("coding", "Code generation", ["code", "generate", "refactor"]),
            ("research", "Research engine", ["research", "search", "analyze"]),
            ("multi_agent", "Multi-agent orchestration", ["agents", "coordinate", "swarm"]),
            ("browser", "Browser automation", ["browser", "navigate", "extract"]),
            ("github", "GitHub integration", ["github", "pr", "issue", "review"]),
            ("mcp_client", "MCP client", ["mcp", "connect", "call"]),
            ("rag", "RAG engine", ["rag", "index", "retrieve", "generate"]),
            ("calibration", "Calibration tracking", ["calibrate", "track", "score"]),
            ("causal", "Causal reasoning", ["causal", "infer", "intervene"]),
            ("debate", "Debate protocol", ["debate", "argue", "judge"]),
            ("planning", "Planning engine", ["plan", "strategy", "roadmap"]),
            ("evaluation", "Evaluation suite", ["evaluate", "benchmark", "score"]),
            ("safety_gates", "Safety gates", ["safety", "gate", "check"]),
            ("goal_engine", "Goal management", ["goals", "track", "achieve"]),
            ("knowledge_graph", "Knowledge graph", ["knowledge", "graph", "entities"]),
        ]

        for name, desc, caps in plugins:
            self.features[name] = Feature(
                name=name,
                category=FeatureCategory.PLUGIN,
                description=desc,
                capabilities=caps,
            )

        # ── MCP Servers ──
        mcp_servers = [
            ("harnix", "harnix kernel MCP", ["kernel", "lifecycle", "tasks"]),
            ("formal_prover", "Formal verification MCP", ["verify", "prove", "math"]),
        ]

        for name, desc, caps in mcp_servers:
            self.features[f"mcp_{name}"] = Feature(
                name=f"mcp_{name}",
                category=FeatureCategory.MCP_SERVER,
                description=desc,
                capabilities=caps,
            )

        # ── Skills ──
        skills = [
            ("01-research", "Research super-optimized", ["research", "search", "evidence"]),
            ("02-planning", "Advanced planning", ["planning", "strategy", "dag"]),
            ("03-orchestration", "Swarm orchestration", ["swarm", "agents", "coordinate"]),
            ("04-tools", "Tools environment", ["tools", "sandbox", "docker"]),
            ("05-safety-evaluation", "Safety evaluation", ["safety", "risk", "invariants"]),
            ("06-memory-world", "Memory and world model", ["memory", "world", "entities"]),
            ("07-search-optimized", "Search super-optimized", ["search", "web", "extract"]),
            ("08-project-synthesis", "Project synthesis", ["project", "synthesize", "build"]),
            ("09-github-advanced", "GitHub advanced", ["github", "pr", "review", "ci"]),
            ("10-hub-recommended", "Hub recommended", ["hub", "skills", "install"]),
            ("11-deep-cognition", "Deep cognition", ["cognition", "reasoning", "metacognition"]),
            ("12-bot-mode-agi", "Bot mode AGI", ["bots", "agi", "swarm"]),
        ]

        for name, desc, caps in skills:
            self.features[f"skill_{name}"] = Feature(
                name=f"skill_{name}",
                category=FeatureCategory.SKILL,
                description=desc,
                capabilities=caps,
            )

        # ── Bot Profiles ──
        bots = [
            ("planner", "Master Planner", ["planning", "strategy", "6-plan"]),
            ("strategist", "Strategist", ["strategy", "foresight", "scenarios"]),
            ("architect", "System Architect", ["architecture", "design", "system"]),
            ("researcher", "Deep Researcher", ["research", "evidence", "analysis"]),
            ("coder", "Core Coder", ["coding", "implementation", "development"]),
            ("verifier", "Verifier", ["verification", "testing", "validation"]),
            ("critic", "Critical Reviewer", ["review", "critique", "bias_detection"]),
            ("optimizer", "Performance Optimizer", ["optimization", "performance", "speed"]),
            ("safety_governor", "Safety Governor", ["safety", "governance", "invariants"]),
            ("documenter", "Documenter", ["documentation", "docs", "api_docs"]),
        ]

        for name, role, caps in bots:
            self.features[f"bot_{name}"] = Feature(
                name=f"bot_{name}",
                category=FeatureCategory.BOT,
                description=role,
                capabilities=caps,
            )

        # ── Workflows ──
        workflows = [
            ("daily_improvement", "Daily improvement cycle", ["improvement", "daily", "evolution"]),
            ("sleep_cycle", "13-step sleep cycle", ["sleep", "dream", "consolidation"]),
            ("world_sync", "World state synchronization", ["world", "sync", "forecast"]),
            ("curriculum", "Curriculum learning", ["curriculum", "learning", "progression"]),
            ("benchmark", "Benchmark execution", ["benchmark", "evaluation", "scoring"]),
            ("self_healing", "Self-healing loop", ["healing", "recovery", "repair"]),
        ]

        for name, desc, caps in workflows:
            self.features[f"workflow_{name}"] = Feature(
                name=f"workflow_{name}",
                category=FeatureCategory.WORKFLOW,
                description=desc,
                capabilities=caps,
            )

    def find_by_capability(self, capability: str) -> list[Feature]:
        """Find features that provide a capability."""
        capability_lower = capability.lower()
        return [
            f
            for f in self.features.values()
            if any(capability_lower in c.lower() for c in f.capabilities)
        ]

    def find_by_category(self, category: FeatureCategory) -> list[Feature]:
        """Find features by category."""
        return [f for f in self.features.values() if f.category == category]

    def search(self, query: str) -> list[Feature]:
        """Search features by name or description."""
        query_lower = query.lower()
        return [
            f
            for f in self.features.values()
            if query_lower in f.name.lower() or query_lower in f.description.lower()
        ]

    def get_all_capabilities(self) -> set[str]:
        """Get all unique capabilities."""
        caps = set()
        for f in self.features.values():
            caps.update(f.capabilities)
        return caps
