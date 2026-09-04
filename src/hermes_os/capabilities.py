"""
HERMES INTELLIGENCE OS — CAPABILITY AWARENESS OS (v9)
===================================================
Enables Hermes to reason explicitly over its own capabilities BEFORE planning:
- Machine-readable Capability Manifests (Tools, Skills, Plugins, Commands, Models, Agents, MCP).
- On-Demand Skill Loader (metadata stored compactly; full SKILL.md loaded only on selection).
- Plugin Health, Dependency, and Permission Checker.
- Control-Plane Command Registry (/plan, /research, /deep-research, /think, /autonomous, etc.).
- Hierarchical Capability Graph (Research, Coding, Computer Use, Autonomous Execution).
- Explicit Capability Selection as a first-class cognitive decision step.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("hermes.os.capabilities")


class CapabilityKind(str, enum.Enum):
    """Classification of intelligence and actuation capabilities."""
    MODEL = "model"
    AGENT = "agent"
    TOOL = "tool"
    SKILL = "skill"
    PLUGIN = "plugin"
    COMMAND = "command"
    MCP = "mcp"
    EXTERNAL_RUNTIME = "external_runtime"


@dataclass
class CapabilityManifest:
    """Machine-readable contract describing an operational capability."""
    id: str
    kind: CapabilityKind
    name: str
    description: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    risk: str = "low"                      # "low", "medium", "high", "critical"
    cost: Dict[str, str] = field(default_factory=lambda: {"tokens": "medium", "latency": "medium"})
    best_for: List[str] = field(default_factory=list)
    avoid_for: List[str] = field(default_factory=list)
    verification: str = "oracle_check"
    is_loaded: bool = False                # Distinction: "available" vs "currently loaded into context"
    skill_file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "prerequisites": self.prerequisites,
            "permissions": self.permissions,
            "risk": self.risk,
            "cost": self.cost,
            "best_for": self.best_for,
            "avoid_for": self.avoid_for,
            "verification": self.verification,
            "is_loaded": self.is_loaded,
        }


@dataclass
class ExecutionCapabilityPlan:
    """Explicit capability bindings resolved for a specific task/subgoal."""
    task_id: str
    required_capabilities: List[str] = field(default_factory=list)
    selected_models: List[str] = field(default_factory=list)
    selected_tools: List[str] = field(default_factory=list)
    selected_skills: List[str] = field(default_factory=list)
    selected_plugins: List[str] = field(default_factory=list)
    selected_commands: List[str] = field(default_factory=list)
    selected_agents: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    verification: str = "oracle_check"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "capabilities": self.required_capabilities,
            "models": self.selected_models,
            "tools": self.selected_tools,
            "skills": self.selected_skills,
            "plugins": self.selected_plugins,
            "commands": self.selected_commands,
            "agents": self.selected_agents,
            "permissions": self.required_permissions,
            "verification": self.verification,
        }


# =====================================================================
# Hierarchical Capability Graph
# =====================================================================

class CapabilityGraph:
    """
    Hierarchical ontology mapping high-level cognitive domains to concrete capabilities:
    Research, Coding, Computer Use, and Autonomous Execution.
    """

    def __init__(self):
        self._hierarchy: Dict[str, List[str]] = {
            "research": [
                "research.web_search",
                "research.browser",
                "research.deep_research",
                "research.source_verification",
                "research.evidence_synthesis",
            ],
            "coding": [
                "coding.repo_analysis",
                "coding.shell",
                "coding.git",
                "coding.agent",
                "coding.test_runner",
                "coding.debugger",
            ],
            "computer_use": [
                "computer.screen",
                "computer.mouse",
                "computer.keyboard",
                "computer.browser",
                "computer.accessibility_tree",
                "computer.vision",
            ],
            "autonomous_execution": [
                "autonomy.persistent_goals",
                "autonomy.scheduler",
                "autonomy.heartbeat",
                "autonomy.background_agents",
                "autonomy.event_bus",
            ],
        }

    def get_capabilities_for_domain(self, domain: str) -> List[str]:
        return list(self._hierarchy.get(domain.lower(), []))

    def list_domains(self) -> List[str]:
        return list(self._hierarchy.keys())

    def find_domains_for_capability(self, cap_id: str) -> List[str]:
        return [dom for dom, caps in self._hierarchy.items() if cap_id in caps]


# =====================================================================
# Capability Registry
# =====================================================================

class CapabilityRegistry:
    """
    Master repository of all operational capabilities available to Hermes.
    Includes built-in models, tools, on-demand skills, plugins, and control-plane commands.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self._registry: Dict[str, CapabilityManifest] = {}
        self.graph = CapabilityGraph()
        self._register_default_capabilities()

    def _register_default_capabilities(self) -> None:
        """Populate baseline manifests for models, tools, skills, plugins, and commands."""
        # 1. Models
        self.register(CapabilityManifest(
            id="model.frontier_reasoner",
            kind=CapabilityKind.MODEL,
            name="Frontier Reasoning Model",
            description="Deep multi-step reasoning, mathematical deduction, and causal analysis",
            cost={"tokens": "high", "latency": "medium"},
            best_for=["architecture_planning", "complex_debugging", "adversarial_critique"],
            avoid_for=["simple_summaries", "low_latency_streaming"],
        ))
        self.register(CapabilityManifest(
            id="model.fast_executor",
            kind=CapabilityKind.MODEL,
            name="Fast Lightweight Model",
            description="Rapid tool routing, summarization, and data extraction",
            cost={"tokens": "low", "latency": "low"},
            best_for=["swarm_workers", "syntax_checks", "evidence_compression"],
            avoid_for=["novel_mathematics", "multi-turn_causal_plans"],
        ))

        # 2. Tools
        self.register(CapabilityManifest(
            id="tool.python_repl",
            kind=CapabilityKind.TOOL,
            name="Python REPL Kernel",
            description="Executes Python code in a persistent session with memory state",
            permissions=["write:code", "exec:python"],
            risk="medium",
            best_for=["calculations", "data_transformation", "scripted_verification"],
        ))
        self.register(CapabilityManifest(
            id="tool.bash_shell",
            kind=CapabilityKind.TOOL,
            name="System Shell",
            description="Executes CLI commands, test suites, and process management",
            permissions=["exec:shell"],
            risk="high",
            best_for=["running_tests", "git_operations", "package_management"],
            verification="exit_code_and_stderr_audit",
        ))

        # 3. Skills (On-Demand loaded)
        self.register(CapabilityManifest(
            id="skill.deep_research",
            kind=CapabilityKind.SKILL,
            name="Deep Research Skill",
            description="Multi-source web and literature investigation with cross-verification",
            inputs=["research_objective", "hypotheses"],
            outputs=["evidence_packet", "verified_claims"],
            risk="low",
            best_for=["market_analysis", "new_library_evaluation", "domain_recon"],
            avoid_for=["local_filesystem_queries"],
            is_loaded=False,
        ))
        self.register(CapabilityManifest(
            id="skill.refactor",
            kind=CapabilityKind.SKILL,
            name="Safe Refactoring Skill",
            description="AST-guided multi-file refactoring with invariant checks",
            permissions=["write:workspace"],
            risk="medium",
            best_for=["codebase_modernization", "type_annotation", "modularization"],
            is_loaded=False,
        ))

        # 4. Plugins
        self.register(CapabilityManifest(
            id="plugin.web_search",
            kind=CapabilityKind.PLUGIN,
            name="Web Search Plugin",
            description="High-throughput search engine interface with snippet ranking",
            risk="low",
            best_for=["retrieving_fresh_information", "documentation_lookup"],
        ))

        # 5. Control-Plane Commands
        commands = [
            ("/plan", "Switches into deterministic planning deliberation mode"),
            ("/research", "Triggers deep research subagent lane"),
            ("/deep-research", "Launches multi-source adversarial research swarm"),
            ("/think", "Allocates high cognitive budget to pre-action deliberation"),
            ("/fast", "Prioritizes minimal token consumption and low latency"),
            ("/autonomous", "Grants bounded autonomy under supervisory monitoring"),
            ("/goal", "Inspects or updates persistent goal contracts"),
            ("/status", "Returns execution health and checkpoint status"),
            ("/compact", "Triggers context OS partition compaction"),
            ("/refine", "Distills trajectory evidence into reusable skill"),
            ("/evaluate", "Runs holdout test suite and anti-reward-hacking checks"),
            ("/rollback", "Restores prior verified checkpoint"),
        ]
        for cmd, desc in commands:
            self.register(CapabilityManifest(
                id=f"command.{cmd.replace('/', '')}",
                kind=CapabilityKind.COMMAND,
                name=cmd,
                description=desc,
                risk="low",
                best_for=["control_plane_steering"],
            ))

    def register(self, manifest: CapabilityManifest) -> None:
        self._registry[manifest.id] = manifest
        logger.debug(f"Registered capability {manifest.id} ({manifest.kind.value})")

    def get(self, capability_id: str) -> Optional[CapabilityManifest]:
        return self._registry.get(capability_id)

    def list_capabilities(self, kind: Optional[CapabilityKind] = None) -> List[CapabilityManifest]:
        if kind:
            return [c for c in self._registry.values() if c.kind == kind]
        return list(self._registry.values())

    def load_skill_body(self, skill_id: str) -> Optional[str]:
        """
        On-demand loading: Returns full SKILL.md text only when selected.
        Maintains minimal context footprint until execution.
        """
        manifest = self.get(skill_id)
        if not manifest or manifest.kind != CapabilityKind.SKILL:
            return None

        # If a explicit file path is set, load it
        if manifest.skill_file_path and Path(manifest.skill_file_path).exists():
            manifest.is_loaded = True
            return Path(manifest.skill_file_path).read_text(encoding="utf-8")

        # Search workspace skills directory
        skill_name = skill_id.replace("skill.", "")
        candidates = [
            Path(self.workspace_root) / "skills" / skill_name / "SKILL.md",
            Path(self.workspace_root) / ".gemini" / "antigravity" / "builtin" / "skills" / skill_name / "SKILL.md",
        ]
        for c in candidates:
            if c.exists():
                manifest.is_loaded = True
                return c.read_text(encoding="utf-8")

        # Fallback synthetic skill body
        manifest.is_loaded = True
        return f"# Skill: {manifest.name}\n\n{manifest.description}\n\nBest for: {', '.join(manifest.best_for)}"


# =====================================================================
# Capability Selector (Deliberation Step)
# =====================================================================

class CapabilitySelector:
    """
    Cognitive reasoning engine that evaluates candidate capabilities
    against task requirements, risk, cost, and availability.
    """

    def __init__(self, registry: CapabilityRegistry):
        self.registry = registry

    def select_for_task(
        self,
        task_id: str,
        task_description: str,
        risk_level: str = "medium",
        allow_high_cost: bool = True,
    ) -> ExecutionCapabilityPlan:
        """
        Determine optimal tools, models, skills, plugins, and commands
        specifically tailored to the task.
        """
        desc_lower = task_description.lower()

        # 1. Model Selection
        if any(w in desc_lower for w in ["architect", "plan", "complex", "debug", "math", "verify"]):
            models = ["model.frontier_reasoner"]
        else:
            models = ["model.fast_executor"]

        # 2. Tool Selection
        tools = []
        if any(w in desc_lower for w in ["code", "script", "compute", "calculate", "python"]):
            tools.append("tool.python_repl")
        if any(w in desc_lower for w in ["test", "git", "bash", "command", "install", "run"]):
            tools.append("tool.bash_shell")

        # 3. Skill Selection (On-Demand)
        skills = []
        if any(w in desc_lower for w in ["research", "investigate", "explore", "search", "competitor"]):
            skills.append("skill.deep_research")
            # Mark loaded
            self.registry.load_skill_body("skill.deep_research")
        if any(w in desc_lower for w in ["refactor", "cleanup", "modernize", "restructure"]):
            skills.append("skill.refactor")
            self.registry.load_skill_body("skill.refactor")

        # 4. Plugin Selection
        plugins = []
        if any(w in desc_lower for w in ["search", "web", "internet", "docs"]):
            plugins.append("plugin.web_search")

        # 5. Command Selection
        commands = []
        if "research" in desc_lower:
            commands.append("command.deep-research")
        elif "autonomous" in desc_lower:
            commands.append("command.autonomous")
        else:
            commands.append("command.plan")

        # 6. Agents
        agents = ["primary_worker"]
        if len(skills) > 0 or "research" in desc_lower:
            agents.append("research_specialist")

        # Required permissions
        perms = ["read"]
        if "tool.python_repl" in tools or "tool.bash_shell" in tools:
            perms.extend(["write:code", "exec:tool"])

        # Verification requirement
        verification = "l4_independent_reproduction" if risk_level == "high" else "l2_clean_inspection"

        return ExecutionCapabilityPlan(
            task_id=task_id,
            required_capabilities=tools + skills + plugins,
            selected_models=models,
            selected_tools=tools,
            selected_skills=skills,
            selected_plugins=plugins,
            selected_commands=commands,
            selected_agents=agents,
            required_permissions=perms,
            verification=verification,
        )
