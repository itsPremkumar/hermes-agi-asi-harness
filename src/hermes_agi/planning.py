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

import time
import uuid
from typing import Any

from .planning_registry import (
    Decision,
    ExecutionPlan,
    Feature,
    FeatureCategory,
    FeatureRegistry,
    Phase,
    PlanStep,
    Priority,
    Thought,
)

__all__ = [
    "Phase",
    "Priority",
    "FeatureCategory",
    "Feature",
    "Thought",
    "Decision",
    "PlanStep",
    "ExecutionPlan",
    "FeatureRegistry",
]


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
        thoughts.append(
            Thought(
                thought_id="t1",
                content=f"Decomposed goal into {len(sub_goals)} sub-goals: {sub_goals}",
                reasoning="Breaking complex goals into manageable sub-tasks enables parallel execution and better tracking.",
                confidence=0.9,
                alternatives=["Execute as single task", "Decompose further"],
                risks=["Sub-goal dependencies may create bottlenecks"],
            )
        )

        # Thought 2: Feature identification
        relevant_features = self._identify_relevant_features(goal)
        thoughts.append(
            Thought(
                thought_id="t2",
                content=f"Identified {len(relevant_features)} relevant features across {len(set(f.category for f in relevant_features))} categories",
                reasoning="Matching goal requirements to available capabilities ensures optimal tool selection.",
                confidence=0.85,
                alternatives=["Use minimal feature set", "Use all available features"],
                risks=["Feature overload may increase complexity"],
            )
        )

        # Thought 3: Approach selection
        approaches = self._identify_approaches(goal, relevant_features)
        thoughts.append(
            Thought(
                thought_id="t3",
                content=f"Evaluated {len(approaches)} approaches: {approaches}",
                reasoning="Comparing approaches by cost, time, and reliability selects the best strategy.",
                confidence=0.8,
                alternatives=approaches,
                risks=["Selected approach may not handle edge cases"],
            )
        )

        # Thought 4: Risk analysis
        risks = self._identify_risks(goal, relevant_features)
        thoughts.append(
            Thought(
                thought_id="t4",
                content=f"Identified {len(risks)} risks: {risks}",
                reasoning="Proactive risk identification enables mitigation planning.",
                confidence=0.75,
                risks=["Unknown unknowns may exist"],
            )
        )

        # Thought 5: Resource estimation
        thoughts.append(
            Thought(
                thought_id="t5",
                content=f"Estimated resources: {len(relevant_features)} features, {len(sub_goals)} sub-goals",
                reasoning="Resource estimation enables proper scheduling and cost control.",
                confidence=0.7,
                alternatives=["Over-provision resources", "Under-provision resources"],
                risks=["Estimates may be inaccurate"],
            )
        )

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
        dependent_features = sorted(
            relevant_features, key=lambda f: len(f.dependencies), reverse=True
        )
        plan_structure["critical_path"] = [f.name for f in dependent_features[:3]]

        return plan_structure

    async def _decide(
        self, goal: str, thoughts: list[Thought], plan_structure: dict
    ) -> list[Decision]:
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
                dep in [f.name for f in relevant_features] for dep in feature.dependencies
            )

            # Estimate cost and time
            cost = self._estimate_cost(feature)
            time = self._estimate_time(feature)

            # Generate reason
            reason = self._generate_reason(feature, goal)

            decisions.append(
                Decision(
                    decision_id=f"d{len(decisions) + 1}",
                    feature=feature,
                    reason=reason,
                    priority=priority,
                    dependencies_satisfied=deps_satisfied,
                    estimated_cost=cost,
                    estimated_time=time,
                )
            )

        # Sort by priority
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        decisions.sort(key=lambda d: priority_order.get(d.priority, 99))

        return decisions

    async def _create_steps(
        self, decisions: list[Decision], plan_structure: dict
    ) -> list[PlanStep]:
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

                steps.append(
                    PlanStep(
                        step_id=f"s{len(steps) + 1}",
                        name=f"{phase}_{feature.name}",
                        description=f"Use {feature.name} ({feature.category.value}) for {phase}",
                        feature=feature,
                        dependencies=[f"s{j}" for j in range(max(0, len(steps) - 2), len(steps))],
                        inputs={inp: f"<{inp}>" for inp in feature.inputs},
                        expected_output=feature.outputs[0] if feature.outputs else "result",
                        fallback=f"Skip {feature.name} if unavailable",
                    )
                )

        return steps

    def _decompose_goal(self, goal: str) -> list[str]:
        """Decompose a goal into sub-goals."""
        goal_lower = goal.lower()
        sub_goals = []

        if any(w in goal_lower for w in ["research", "study", "investigate", "analyze"]):
            sub_goals.extend(
                ["Search for information", "Collect sources", "Synthesize findings", "Write report"]
            )
        if any(w in goal_lower for w in ["implement", "build", "create", "develop", "code"]):
            sub_goals.extend(
                ["Design architecture", "Write code", "Test implementation", "Document solution"]
            )
        if any(w in goal_lower for w in ["test", "verify", "validate", "benchmark"]):
            sub_goals.extend(
                ["Define test cases", "Run tests", "Analyze results", "Report findings"]
            )
        if any(w in goal_lower for w in ["plan", "strategy", "roadmap", "design"]):
            sub_goals.extend(
                ["Define objectives", "Identify resources", "Create timeline", "Assign tasks"]
            )
        if any(w in goal_lower for w in ["fix", "debug", "repair", "resolve"]):
            sub_goals.extend(
                ["Reproduce issue", "Identify root cause", "Implement fix", "Verify fix"]
            )

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
            "overall_risk_level": "high"
            if len(all_risks) > 5
            else "medium"
            if len(all_risks) > 2
            else "low",
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
