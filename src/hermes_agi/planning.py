"""
Planning & Thinking Engine — dynamic decision-making for Hermes features.

This module implements:
1. THINK phase: Analyze the problem, consider approaches, evaluate trade-offs
2. PLAN phase: Select optimal features, create execution strategy
3. DECIDE phase: Dynamically choose which slash commands/tools/plugins to use
4. EXECUTE phase: Orchestrate the plan with proper sequencing

Usage:
    planner = Planner()
    result = await planner.think_and_plan("Research AI agent architectures")
    # result contains: thinking, plan, decisions, execution_strategy
"""

from __future__ import annotations

import logging
import time
import uuid
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
            ("/memory", "Memory operations", ["memory", "store", "retrieve"], ["action"], ["result"]),
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
            ("browser", "Control web browser", ["web", "browser", "navigate"], ["url"], ["content"]),
            ("file_read", "Read file", ["file", "read"], ["path"], ["content"]),
            ("file_write", "Write file", ["file", "write"], ["path", "content"], ["confirmation"]),
            ("terminal", "Execute terminal commands", ["terminal", "exec"], ["command"], ["output"]),
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
            f for f in self.features.values()
            if any(capability_lower in c.lower() for c in f.capabilities)
        ]
    
    def find_by_category(self, category: FeatureCategory) -> list[Feature]:
        """Find features by category."""
        return [f for f in self.features.values() if f.category == category]
    
    def search(self, query: str) -> list[Feature]:
        """Search features by name or description."""
        query_lower = query.lower()
        return [
            f for f in self.features.values()
            if query_lower in f.name.lower() or query_lower in f.description.lower()
        ]
    
    def get_all_capabilities(self) -> set[str]:
        """Get all unique capabilities."""
        caps = set()
        for f in self.features.values():
            caps.update(f.capabilities)
        return caps


# ──────────────────────────── Planner ────────────────────────────


class Planner:
    """
    Dynamic planning engine that thinks, plans, decides, and executes.
    
    Usage:
        planner = Planner()
        plan = await planner.think_and_plan("Research AI agent architectures")
        # plan contains: thoughts, decisions, steps, execution_strategy
    """
    
    def __init__(self):
        self.registry = FeatureRegistry()
    
    async def think_and_plan(self, goal: str, context: dict | None = None) -> ExecutionPlan:
        """
        Main entry point: think → plan → decide → create execution plan.
        """
        # Phase 1: THINK
        thoughts = await self._think(goal, context)
        
        # Phase 2: PLAN
        plan_structure = await self._plan(goal, thoughts)
        
        # Phase 3: DECIDE
        decisions = await self._decide(goal, thoughts, plan_structure)
        
        # Phase 4: Create execution steps
        steps = await self._create_steps(decisions, plan_structure)
        
        # Calculate estimates
        total_time = sum(d.estimated_time for d in decisions)
        total_cost = sum(d.estimated_cost for d in decisions)
        
        # Risk assessment
        risks = self._assess_risks(thoughts, decisions)
        
        return ExecutionPlan(
            plan_id=str(uuid.uuid4())[:8],
            goal=goal,
            thoughts=thoughts,
            decisions=decisions,
            steps=steps,
            estimated_total_time=total_time,
            estimated_total_cost=total_cost,
            risk_assessment=risks,
            created_at=time.time(),
        )
    
    async def _think(self, goal: str, context: dict | None) -> list[Thought]:
        """
        THINK phase: Analyze the problem, consider approaches, evaluate trade-offs.
        """
        thoughts = []
        
        # Thought 1: Problem decomposition
        sub_goals = self._decompose_goal(goal)
        thoughts.append(Thought(
            thought_id="t1",
            content=f"Decomposed goal into {len(sub_goals)} sub-goals: {sub_goals}",
            reasoning="Breaking complex goals into manageable sub-tasks enables parallel execution and better tracking.",
            confidence=0.9,
            alternatives=["Execute as single task", "Decompose further"],
            risks=["Sub-goal dependencies may create bottlenecks"],
        ))
        
        # Thought 2: Feature identification
        relevant_features = self._identify_relevant_features(goal)
        thoughts.append(Thought(
            thought_id="t2",
            content=f"Identified {len(relevant_features)} relevant features across {len(set(f.category for f in relevant_features))} categories",
            reasoning="Matching goal requirements to available capabilities ensures optimal tool selection.",
            confidence=0.85,
            alternatives=["Use minimal feature set", "Use all available features"],
            risks=["Feature overload may increase complexity"],
        ))
        
        # Thought 3: Approach selection
        approaches = self._identify_approaches(goal, relevant_features)
        thoughts.append(Thought(
            thought_id="t3",
            content=f"Evaluated {len(approaches)} approaches: {approaches}",
            reasoning="Comparing approaches by cost, time, and reliability selects the best strategy.",
            confidence=0.8,
            alternatives=approaches,
            risks=["Selected approach may not handle edge cases"],
        ))
        
        # Thought 4: Risk analysis
        risks = self._identify_risks(goal, relevant_features)
        thoughts.append(Thought(
            thought_id="t4",
            content=f"Identified {len(risks)} risks: {risks}",
            reasoning="Proactive risk identification enables mitigation planning.",
            confidence=0.75,
            risks=["Unknown unknowns may exist"],
        ))
        
        # Thought 5: Resource estimation
        thoughts.append(Thought(
            thought_id="t5",
            content=f"Estimated resources: {len(relevant_features)} features, {len(sub_goals)} sub-goals",
            reasoning="Resource estimation enables proper scheduling and cost control.",
            confidence=0.7,
            alternatives=["Over-provision resources", "Under-provision resources"],
            risks=["Estimates may be inaccurate"],
        ))
        
        return thoughts
    
    async def _plan(self, goal: str, thoughts: list[Thought]) -> dict[str, Any]:
        """
        PLAN phase: Create the high-level plan structure.
        """
        sub_goals = self._decompose_goal(goal)
        relevant_features = self._identify_relevant_features(goal)
        
        # Group features by phase
        plan_structure = {
            "goal": goal,
            "sub_goals": sub_goals,
            "phases": {
                "research": [],
                "analysis": [],
                "implementation": [],
                "verification": [],
                "documentation": [],
            },
            "features_by_phase": {},
            "parallel_groups": [],
            "critical_path": [],
        }
        
        # Assign features to phases
        for feature in relevant_features:
            if any(c in feature.capabilities for c in ["search", "research", "web"]):
                plan_structure["phases"]["research"].append(feature)
            elif any(c in feature.capabilities for c in ["analyze", "evaluate", "benchmark"]):
                plan_structure["phases"]["analysis"].append(feature)
            elif any(c in feature.capabilities for c in ["code", "implement", "build", "generate"]):
                plan_structure["phases"]["implementation"].append(feature)
            elif any(c in feature.capabilities for c in ["verify", "test", "validate", "prove"]):
                plan_structure["phases"]["verification"].append(feature)
            elif any(c in feature.capabilities for c in ["document", "docs", "report"]):
                plan_structure["phases"]["documentation"].append(feature)
        
        # Identify parallel groups (features with no dependencies)
        parallel_candidates = [f for f in relevant_features if not f.dependencies]
        if parallel_candidates:
            plan_structure["parallel_groups"].append([f.name for f in parallel_candidates[:5]])
        
        # Identify critical path (features with most dependencies)
        dependent_features = sorted(relevant_features, key=lambda f: len(f.dependencies), reverse=True)
        plan_structure["critical_path"] = [f.name for f in dependent_features[:3]]
        
        return plan_structure
    
    async def _decide(self, goal: str, thoughts: list[Thought], plan_structure: dict) -> list[Decision]:
        """
        DECIDE phase: Dynamically decide which features to use.
        """
        decisions = []
        relevant_features = self._identify_relevant_features(goal)
        
        for feature in relevant_features:
            # Calculate priority based on goal relevance
            priority = self._calculate_priority(feature, goal)
            
            # Check dependencies
            deps_satisfied = all(
                dep in [f.name for f in relevant_features]
                for dep in feature.dependencies
            )
            
            # Estimate cost and time
            cost = self._estimate_cost(feature)
            time = self._estimate_time(feature)
            
            # Generate reason
            reason = self._generate_reason(feature, goal)
            
            decisions.append(Decision(
                decision_id=f"d{len(decisions)+1}",
                feature=feature,
                reason=reason,
                priority=priority,
                dependencies_satisfied=deps_satisfied,
                estimated_cost=cost,
                estimated_time=time,
            ))
        
        # Sort by priority
        priority_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
        decisions.sort(key=lambda d: priority_order.get(d.priority, 99))
        
        return decisions
    
    async def _create_steps(self, decisions: list[Decision], plan_structure: dict) -> list[PlanStep]:
        """
        Create ordered execution steps from decisions.
        """
        steps = []
        phase_order = ["research", "analysis", "implementation", "verification", "documentation"]
        
        for phase in phase_order:
            phase_features = plan_structure["phases"].get(phase, [])
            for i, feature in enumerate(phase_features):
                # Find matching decision
                matching_decisions = [d for d in decisions if d.feature.name == feature.name]
                if not matching_decisions:
                    continue
                decision = matching_decisions[0]
                
                steps.append(PlanStep(
                    step_id=f"s{len(steps)+1}",
                    name=f"{phase}_{feature.name}",
                    description=f"Use {feature.name} ({feature.category.value}) for {phase}",
                    feature=feature,
                    dependencies=[f"s{j}" for j in range(max(0, len(steps)-2), len(steps))],
                    inputs={inp: f"<{inp}>" for inp in feature.inputs},
                    expected_output=feature.outputs[0] if feature.outputs else "result",
                    fallback=f"Skip {feature.name} if unavailable",
                ))
        
        return steps
    
    def _decompose_goal(self, goal: str) -> list[str]:
        """Decompose a goal into sub-goals."""
        goal_lower = goal.lower()
        sub_goals = []
        
        if any(w in goal_lower for w in ["research", "study", "investigate", "analyze"]):
            sub_goals.extend(["Search for information", "Collect sources", "Synthesize findings", "Write report"])
        if any(w in goal_lower for w in ["implement", "build", "create", "develop", "code"]):
            sub_goals.extend(["Design architecture", "Write code", "Test implementation", "Document solution"])
        if any(w in goal_lower for w in ["test", "verify", "validate", "benchmark"]):
            sub_goals.extend(["Define test cases", "Run tests", "Analyze results", "Report findings"])
        if any(w in goal_lower for w in ["plan", "strategy", "roadmap", "design"]):
            sub_goals.extend(["Define objectives", "Identify resources", "Create timeline", "Assign tasks"])
        if any(w in goal_lower for w in ["fix", "debug", "repair", "resolve"]):
            sub_goals.extend(["Reproduce issue", "Identify root cause", "Implement fix", "Verify fix"])
        
        if not sub_goals:
            sub_goals = ["Analyze requirements", "Execute task", "Verify result"]
        
        return sub_goals
    
    def _identify_relevant_features(self, goal: str) -> list[Feature]:
        """Identify features relevant to the goal."""
        goal_lower = goal.lower()
        relevant = []
        
        # Map keywords to capabilities
        keyword_map = {
            "research": ["search", "research", "web", "evidence"],
            "search": ["search", "web", "browser"],
            "code": ["code", "implement", "build", "generate"],
            "test": ["test", "verify", "validate", "benchmark"],
            "plan": ["plan", "strategy", "roadmap"],
            "analyze": ["analyze", "evaluate", "benchmark"],
            "document": ["document", "docs", "report"],
            "fix": ["debug", "fix", "repair"],
            "deploy": ["deploy", "release", "publish"],
            "memory": ["memory", "store", "retrieve"],
            "security": ["security", "audit", "scan"],
            "git": ["git", "github", "commit", "pr"],
            "browser": ["browser", "web", "navigate"],
            "image": ["vision", "image", "visual"],
            "audio": ["audio", "stt", "tts"],
            "agent": ["agents", "swarm", "coordinate"],
            "mcp": ["mcp", "call", "server"],
            "model": ["model", "provider", "routing"],
        }
        
        matched_capabilities = set()
        for keyword, capabilities in keyword_map.items():
            if keyword in goal_lower:
                matched_capabilities.update(capabilities)
        
        # Find features matching any capability
        for feature in self.registry.features.values():
            if any(cap in matched_capabilities for cap in feature.capabilities):
                relevant.append(feature)
        
        # If no matches, return core features
        if not relevant:
            relevant = [
                self.registry.features.get("web_search"),
                self.registry.features.get("file_read"),
                self.registry.features.get("terminal"),
            ]
            relevant = [f for f in relevant if f]
        
        return relevant
    
    def _identify_approaches(self, goal: str, features: list[Feature]) -> list[str]:
        """Identify possible approaches."""
        approaches = []
        
        if len(features) > 5:
            approaches.append("Parallel execution (multiple features simultaneously)")
        if any(f.category == FeatureCategory.BOT for f in features):
            approaches.append("Bot swarm (delegate to specialized bots)")
        if any(f.category == FeatureCategory.WORKFLOW for f in features):
            approaches.append("Workflow automation (predefined sequence)")
        if any(f.category == FeatureCategory.MCP_SERVER for f in features):
            approaches.append("MCP delegation (external tool calls)")
        
        approaches.append("Sequential execution (one feature at a time)")
        approaches.append("Single feature (simplest approach)")
        
        return approaches
    
    def _identify_risks(self, goal: str, features: list[Feature]) -> list[str]:
        """Identify potential risks."""
        risks = []
        
        if len(features) > 10:
            risks.append("High complexity from many features")
        if any(f.category == FeatureCategory.MCP_SERVER for f in features):
            risks.append("MCP server may be unavailable")
        if any(f.category == FeatureCategory.BOT for f in features):
            risks.append("Bot may produce unexpected output")
        if "security" in goal.lower():
            risks.append("Security implications require careful review")
        if "deploy" in goal.lower():
            risks.append("Deployment may affect production systems")
        
        risks.append("General: estimates may be inaccurate")
        
        return risks
    
    def _calculate_priority(self, feature: Feature, goal: str) -> Priority:
        """Calculate feature priority for this goal."""
        goal_lower = goal.lower()
        
        # Direct capability match
        for cap in feature.capabilities:
            if cap.lower() in goal_lower:
                return Priority.HIGH
        
        # Category-based priority
        if feature.category == FeatureCategory.TOOL:
            return Priority.HIGH
        if feature.category == FeatureCategory.SLASH_COMMAND:
            return Priority.MEDIUM
        if feature.category == FeatureCategory.PLUGIN:
            return Priority.MEDIUM
        
        return Priority.LOW
    
    def _estimate_cost(self, feature: Feature) -> float:
        """Estimate cost (in USD) for using this feature."""
        if feature.category == FeatureCategory.TOOL:
            return 0.01  # API call cost
        if feature.category == FeatureCategory.MCP_SERVER:
            return 0.05  # MCP call cost
        if feature.category == FeatureCategory.BOT:
            return 0.10  # Bot execution cost
        return 0.0
    
    def _estimate_time(self, feature: Feature) -> float:
        """Estimate time (in seconds) for using this feature."""
        if feature.category == FeatureCategory.TOOL:
            return 2.0
        if feature.category == FeatureCategory.MCP_SERVER:
            return 5.0
        if feature.category == FeatureCategory.BOT:
            return 30.0
        if feature.category == FeatureCategory.WORKFLOW:
            return 60.0
        return 1.0
    
    def _generate_reason(self, feature: Feature, goal: str) -> str:
        """Generate reason for selecting this feature."""
        matching_caps = [c for c in feature.capabilities if c.lower() in goal.lower()]
        if matching_caps:
            return f"Selected for capabilities: {', '.join(matching_caps)}"
        return f"Selected as supporting {feature.category.value}"
    
    def _assess_risks(self, thoughts: list[Thought], decisions: list[Decision]) -> dict[str, Any]:
        """Assess overall risks."""
        all_risks = []
        for thought in thoughts:
            all_risks.extend(thought.risks)
        
        unsatisfied = [d for d in decisions if not d.dependencies_satisfied]
        
        return {
            "total_risks": len(all_risks),
            "risks": all_risks,
            "unsatisfied_dependencies": len(unsatisfied),
            "unsatisfied_features": [d.feature.name for d in unsatisfied],
            "overall_risk_level": "high" if len(all_risks) > 5 else "medium" if len(all_risks) > 2 else "low",
        }


# ──────────────────────────── Convenience Functions ────────────────────────────


async def plan(goal: str, context: dict | None = None) -> ExecutionPlan:
    """Convenience function: create a plan for a goal."""
    planner = Planner()
    return await planner.think_and_plan(goal, context)


def get_all_features() -> dict[str, Feature]:
    """Get all available features."""
    registry = FeatureRegistry()
    return registry.features


def get_all_capabilities() -> set[str]:
    """Get all available capabilities."""
    registry = FeatureRegistry()
    return registry.get_all_capabilities()


def search_features(query: str) -> list[Feature]:
    """Search for features."""
    registry = FeatureRegistry()
    return registry.search(query)


def find_by_capability(capability: str) -> list[Feature]:
    """Find features by capability."""
    registry = FeatureRegistry()
    return registry.find_by_capability(capability)
