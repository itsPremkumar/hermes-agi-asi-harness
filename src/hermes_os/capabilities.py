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

        # 2. Tools (Standard & Developer Agency Suite)
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
        self.register(CapabilityManifest(
            id="tool.write_file",
            kind=CapabilityKind.TOOL,
            name="Write File Tool",
            description="Write or overwrite a file in the workspace",
            permissions=["write:workspace"],
            risk="medium",
            best_for=["creating_files", "overwriting_files", "scaffolding"],
        ))
        self.register(CapabilityManifest(
            id="tool.edit_file",
            kind=CapabilityKind.TOOL,
            name="Edit File Tool",
            description="Surgically replace target content in an existing file",
            permissions=["write:workspace"],
            risk="medium",
            best_for=["targeted_code_edits", "bug_fixes", "refactoring"],
        ))
        self.register(CapabilityManifest(
            id="tool.list_dir",
            kind=CapabilityKind.TOOL,
            name="List Directory Tool",
            description="List directory contents with file metadata",
            permissions=["read:workspace"],
            risk="low",
            best_for=["directory_exploration", "file_enumeration"],
        ))
        self.register(CapabilityManifest(
            id="tool.grep_search",
            kind=CapabilityKind.TOOL,
            name="Grep Search Tool",
            description="Ripgrep-style pattern matching across files",
            permissions=["read:workspace"],
            risk="low",
            best_for=["code_search", "pattern_matching", "symbol_lookup"],
        ))
        self.register(CapabilityManifest(
            id="tool.find_by_name",
            kind=CapabilityKind.TOOL,
            name="Find By Name Tool",
            description="Find files matching a glob pattern",
            permissions=["read:workspace"],
            risk="low",
            best_for=["locating_files", "glob_search"],
        ))
        self.register(CapabilityManifest(
            id="tool.execute_shell",
            kind=CapabilityKind.TOOL,
            name="Execute Shell Tool",
            description="Execute shell command safely under SafetyKernel policy",
            permissions=["exec:shell"],
            risk="high",
            best_for=["running_tests", "running_scripts", "environment_inspection"],
        ))
        self.register(CapabilityManifest(
            id="tool.git_status",
            kind=CapabilityKind.TOOL,
            name="Git Status Tool",
            description="Get workspace git status",
            permissions=["read:workspace"],
            risk="low",
            best_for=["vcs_inspection", "modified_files_check"],
        ))
        self.register(CapabilityManifest(
            id="tool.git_diff",
            kind=CapabilityKind.TOOL,
            name="Git Diff Tool",
            description="Get workspace git diff",
            permissions=["read:workspace"],
            risk="low",
            best_for=["patch_review", "diff_generation"],
        ))
        self.register(CapabilityManifest(
            id="tool.apply_patch",
            kind=CapabilityKind.TOOL,
            name="Apply Patch Tool",
            description="Apply a unified git diff patch to the workspace",
            permissions=["write:workspace"],
            risk="high",
            best_for=["applying_patches", "swe_bench_solutions"],
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

    def register_mcp_tools(self, tools: List[Dict[str, Any]], server_name: str = "mcp") -> List[CapabilityManifest]:
        """
        Dynamically register MCP tools into the Capability Awareness OS.
        """
        registered = []
        for tool in tools:
            name = tool.get("name", "unknown")
            cap_id = f"mcp.{server_name}.{name}"
            inputs = []
            schema = tool.get("input_schema", {})
            if isinstance(schema, dict) and "properties" in schema:
                inputs = list(schema["properties"].keys())
            manifest = CapabilityManifest(
                id=cap_id,
                kind=CapabilityKind.MCP,
                name=f"{server_name}:{name}",
                description=tool.get("description", "Dynamic MCP tool"),
                inputs=inputs,
                risk=tool.get("risk", "low"),
                cost={"tokens": "low", "latency": "medium"},
                best_for=["dynamic_mcp_execution", f"{server_name}_operations"],
                metadata={"server": server_name, "input_schema": schema},
            )
            self.register(manifest)
            registered.append(manifest)
        return registered



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

    def select_with_scores(
        self,
        task_id: str,
        task_description: str,
        risk_level: str = "medium",
    ) -> ExecutionCapabilityPlan:
        """Utility-ranked selection: outcome − cost − risk (scorecard-backed)."""
        plan = self.select_for_task(task_id, task_description, risk_level)
        try:
            from .tool_scoring import ToolScorecard
            sc = ToolScorecard(workspace_root=self.registry.workspace_root)
            cands = [{"name": t.replace("tool.", ""), "risk": "medium", "est_tokens": 500}
                     for t in plan.selected_tools]
            # Map short names back to tool.* ids for ranking
            ranked = sc.rank([{"name": t, "risk": "medium", "est_tokens": 500} for t in plan.selected_tools])
            plan.selected_tools = [r["name"] for r in ranked] or plan.selected_tools
            plan.required_capabilities = plan.selected_tools + plan.selected_skills + plan.selected_plugins
        except Exception:
            pass
        return plan

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
