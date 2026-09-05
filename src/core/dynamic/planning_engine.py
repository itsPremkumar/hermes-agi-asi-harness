"""
Advanced Planning Phase Engine — Generate dynamic plans based on scenario analysis.

Uses the ScenarioProfile to:
1. Generate dynamic workflow steps
2. Select appropriate modules for each step
3. Determine agent topology and parallelism
4. Create checkpoints and quality gates
5. Estimate resources and timeline
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.dynamic.scenario_analyzer import (
    ScenarioProfile,
    ScenarioType,
)


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(str, Enum):
    ANALYSIS = "analysis"
    RESEARCH = "research"
    DESIGN = "design"
    SYNTHESIS = "synthesis"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    REVIEW = "review"
    DEPLOYMENT = "deployment"
    LEARNING = "learning"
    DECISION = "decision"
    GATE = "gate"
    PARALLEL = "parallel"


@dataclass
class PlanStep:
    """A single step in the dynamic plan."""
    id: str
    name: str
    step_type: StepType
    description: str
    status: StepStatus = StepStatus.PENDING
    
    # Dynamic configuration
    required_modules: list[str] = field(default_factory=list)
    agent_role: str = "executor"
    agent_count: int = 1
    
    # Dependencies
    depends_on: list[str] = field(default_factory=list)
    parallel_with: list[str] = field(default_factory=list)
    
    # Quality
    quality_gates: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    
    # Estimation
    estimated_duration_min: int = 0
    
    # Results
    output_artifacts: list[str] = field(default_factory=list)
    result: Any = None
    
    # Dynamic decisions
    decision_points: list[dict[str, Any]] = field(default_factory=list)
    alternatives: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DynamicPlan:
    """Complete dynamic plan for a scenario."""
    id: str
    goal: str
    scenario_profile: ScenarioProfile
    
    # Plan structure
    steps: list[PlanStep] = field(default_factory=list)
    
    # Topology
    topology: str = "single"
    max_parallelism: int = 1
    
    # Timeline
    estimated_total_min: int = 0
    
    # Resources
    required_capabilities: list[str] = field(default_factory=list)
    required_modules: list[str] = field(default_factory=list)
    
    # Quality
    global_quality_gates: list[str] = field(default_factory=list)
    
    # Adaptation
    adaptation_points: list[dict[str, Any]] = field(default_factory=list)
    contingency_plans: list[dict[str, Any]] = field(default_factory=list)


class AdvancedPlanningEngine:
    """
    Advanced Planning Phase Engine.
    
    Generates dynamic, scenario-aware plans that use the orchestrator's
    full capacity. Every plan is unique and adapted to the specific scenario.
    """
    
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.plan_templates = self._load_plan_templates()
    
    def generate_plan(self, profile: ScenarioProfile) -> DynamicPlan:
        """
        Generate a complete dynamic plan for the given scenario profile.
        
        This is the core planning method — it examines the profile and
        generates an optimal plan using all available orchestrator capacity.
        """
        plan = DynamicPlan(
            id=str(uuid.uuid4()),
            goal=profile.goal,
            scenario_profile=profile,
            topology=profile.recommended_topology,
            required_modules=profile.required_modules,
        )
        
        # Generate steps based on scenario type
        steps = self._generate_steps(profile)
        plan.steps = steps
        
        # Configure parallelism
        plan.max_parallelism = self._calculate_parallelism(profile)
        
        # Add quality gates
        plan.global_quality_gates = self._generate_global_gates(profile)
        
        # Add adaptation points
        plan.adaptation_points = self._identify_adaptation_points(profile, steps)
        
        # Add contingency plans
        plan.contingency_plans = self._generate_contingencies(profile)
        
        # Calculate total estimate
        plan.estimated_total_min = sum(s.estimated_duration_min for s in steps)
        
        return plan
    
    def _generate_steps(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate plan steps based on scenario type."""
        workflow = profile.recommended_workflow
        
        step_generators = {
            "architecture_first": self._gen_architecture_first,
            "understand_implement_test": self._gen_understand_implement_test,
            "reproduce_diagnose_fix": self._gen_reproduce_diagnose_fix,
            "analyze_design_implement": self._gen_analyze_design_implement,
            "explore_synthesize_report": self._gen_explore_synthesize_report,
            "test_stage_canary_production": self._gen_test_stage_canary_production,
            "scan_analyze_remediate": self._gen_scan_analyze_remediate,
            "profile_hypothesize_benchmark": self._gen_profile_hypothesize_benchmark,
            "analyze_plan_execute_verify": self._gen_analyze_plan_execute_verify,
            "read_structure_write": self._gen_read_structure_write,
            "analyze_write_execute": self._gen_analyze_write_execute,
            "reproduce_localize_fix": self._gen_reproduce_localize_fix,
            "read_analyze_report": self._gen_read_analyze_report,
            "assess_execute_verify": self._gen_assess_execute_verify,
        }
        
        generator = step_generators.get(workflow, self._gen_understand_implement_test)
        return generator(profile)
    
    def _gen_architecture_first(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for new project (architecture-first approach)."""
        return [
            self._create_step("Requirements Analysis", StepType.ANALYSIS,
                            "Compile and analyze requirements", profile, 10,
                            ["requirements_compiler"], "analyst"),
            self._create_step("Research & Discovery", StepType.RESEARCH,
                            "Research technologies and best practices", profile, 15,
                            ["strategy_search", "cross_repo"], "researcher"),
            self._create_step("Architecture Synthesis", StepType.DESIGN,
                            "Generate and evaluate architecture candidates", profile, 20,
                            ["architecture_synthesizer", "adr_registry"], "architect"),
            self._create_step("Risk Analysis", StepType.ANALYSIS,
                            "Analyze architectural risks", profile, 10,
                            ["architecture_risk"], "analyst"),
            self._create_step("Decision Gate", StepType.GATE,
                            "Review and approve architecture", profile, 5,
                            ["quality_gates"], "manager",
                            depends_on=["Architecture Synthesis", "Risk Analysis"]),
            self._create_step("Task Decomposition", StepType.SYNTHESIS,
                            "Break architecture into implementable tasks", profile, 10,
                            ["task_graph"], "architect",
                            depends_on=["Decision Gate"]),
            self._create_step("Implementation", StepType.PARALLEL,
                            "Implement components in parallel", profile,
                            profile.estimated_time_minutes // 2,
                            ["code_generation", "worktree_isolation"],
                            "coder", agent_count=4,
                            depends_on=["Task Decomposition"]),
            self._create_step("Integration Testing", StepType.VERIFICATION,
                            "Test integrated components", profile, 20,
                            ["test_pyramid", "test_oracle"], "test_engineer",
                            depends_on=["Implementation"]),
            self._create_step("System Review", StepType.REVIEW,
                            "Review the complete system", profile, 15,
                            ["review_architecture"], "reviewer",
                            depends_on=["Integration Testing"]),
            self._create_step("Deployment Planning", StepType.DESIGN,
                            "Plan deployment strategy", profile, 10,
                            ["quality_gates"], "devops",
                            depends_on=["System Review"]),
            self._create_step("Documentation", StepType.ANALYSIS,
                            "Generate project documentation", profile, 15,
                            [], "writer",
                            depends_on=["System Review"],
                            parallel_with=["Deployment Planning"]),
        ]
    
    def _gen_understand_implement_test(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for feature addition (understand → implement → test)."""
        return [
            self._create_step("Repository Analysis", StepType.ANALYSIS,
                            "Build repository digital twin", profile, 10,
                            ["repository_twin", "code_graph", "semantic_index"],
                            "repository_analyst"),
            self._create_step("Requirements Compilation", StepType.ANALYSIS,
                            "Compile requirements from goal", profile, 10,
                            ["requirements_compiler"], "analyst"),
            self._create_step("Impact Analysis", StepType.ANALYSIS,
                            "Analyze blast radius of changes", profile, 10,
                            ["code_graph"], "analyst",
                            depends_on=["Repository Analysis"]),
            self._create_step("Test Strategy", StepType.DESIGN,
                            "Design test strategy", profile, 10,
                            ["test_pyramid", "test_first_planner"], "test_engineer",
                            depends_on=["Requirements Compilation"]),
            self._create_step("Implementation", StepType.IMPLEMENTATION,
                            "Implement the feature", profile,
                            profile.estimated_time_minutes,
                            ["code_generation", "worktree_isolation"], "coder",
                            depends_on=["Impact Analysis", "Test Strategy"]),
            self._create_step("Unit Testing", StepType.VERIFICATION,
                            "Run unit tests", profile, 10,
                            ["test_oracle"], "test_engineer",
                            depends_on=["Implementation"]),
            self._create_step("Integration Testing", StepType.VERIFICATION,
                            "Run integration tests", profile, 15,
                            ["test_pyramid"], "test_engineer",
                            depends_on=["Unit Testing"]),
            self._create_step("Code Review", StepType.REVIEW,
                            "Review code changes", profile, 15,
                            ["review_architecture"], "reviewer",
                            depends_on=["Integration Testing"]),
            self._create_step("Quality Gate", StepType.GATE,
                            "Final quality checks before merge", profile, 5,
                            ["quality_gates", "merge_controller"], "manager",
                            depends_on=["Code Review"]),
        ]
    
    def _gen_reproduce_diagnose_fix(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for bug fix (reproduce → diagnose → fix)."""
        return [
            self._create_step("Repository Analysis", StepType.ANALYSIS,
                            "Build repository model", profile, 10,
                            ["repository_twin", "code_graph"], "repository_analyst"),
            self._create_step("Reproduce Issue", StepType.ANALYSIS,
                            "Create reproduction case", profile, 15,
                            [], "debugger"),
            self._create_step("Failure Localization", StepType.ANALYSIS,
                            "Localize root cause", profile, 15,
                            ["failure_localization", "hypothesis_debug"],
                            "debugger", depends_on=["Reproduce Issue"]),
            self._create_step("Hypothesis Generation", StepType.RESEARCH,
                            "Generate fix hypotheses", profile, 10,
                            ["hypothesis_debug"], "debugger",
                            depends_on=["Failure Localization"]),
            self._create_step("Patch Generation", StepType.IMPLEMENTATION,
                            "Generate candidate patches", profile, 15,
                            ["code_generation"], "coder",
                            depends_on=["Hypothesis Generation"]),
            self._create_step("Patch Verification", StepType.VERIFICATION,
                            "Verify patch fixes issue without regressions", profile, 10,
                            ["regression_firewall", "test_pyramid"], "test_engineer",
                            depends_on=["Patch Generation"]),
            self._create_step("Code Review", StepType.REVIEW,
                            "Review the fix", profile, 10,
                            ["review_architecture"], "reviewer",
                            depends_on=["Patch Verification"]),
            self._create_step("Quality Gate", StepType.GATE,
                            "Final quality checks", profile, 5,
                            ["quality_gates"], "manager",
                            depends_on=["Code Review"]),
        ]
    
    def _gen_reproduce_localize_fix(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Alias for bug fix workflow."""
        return self._gen_reproduce_diagnose_fix(profile)
    
    def _gen_analyze_design_implement(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for refactor."""
        return [
            self._create_step("Deep Repository Analysis", StepType.ANALYSIS,
                            "Complete codebase analysis", profile, 15,
                            ["repository_twin", "code_graph", "semantic_index"],
                            "repository_analyst"),
            self._create_step("Refactor Design", StepType.DESIGN,
                            "Design refactoring approach", profile, 20,
                            ["architecture_synthesizer", "architecture_risk"],
                            "architect"),
            self._create_step("Impact Analysis", StepType.ANALYSIS,
                            "Analyze refactor blast radius", profile, 10,
                            ["code_graph", "change_impact"], "analyst",
                            depends_on=["Deep Repository Analysis"]),
            self._create_step("Test Baseline", StepType.VERIFICATION,
                            "Establish test baseline", profile, 15,
                            ["test_pyramid"], "test_engineer",
                            depends_on=["Deep Repository Analysis"]),
            self._create_step("Refactoring", StepType.IMPLEMENTATION,
                            "Execute refactoring", profile,
                            profile.estimated_time_minutes,
                            ["code_generation"], "coder",
                            depends_on=["Refactor Design", "Test Baseline"]),
            self._create_step("Behavioral Verification", StepType.VERIFICATION,
                            "Verify behavior unchanged", profile, 15,
                            ["test_pyramid", "test_oracle"], "test_engineer",
                            depends_on=["Refactoring"]),
            self._create_step("Quality Gate", StepType.GATE,
                            "Final quality checks", profile, 5,
                            ["quality_gates"], "manager",
                            depends_on=["Behavioral Verification"]),
        ]
    
    def _gen_explore_synthesize_report(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for research."""
        return [
            self._create_step("Repository Analysis", StepType.ANALYSIS,
                            "Understand current codebase", profile, 10,
                            ["repository_twin"], "repository_analyst"),
            self._create_step("Research", StepType.RESEARCH,
                            "Conduct research", profile, 30,
                            ["strategy_search", "cross_repo"], "researcher"),
            self._create_step("Synthesis", StepType.SYNTHESIS,
                            "Synthesize findings", profile, 20,
                            ["architecture_synthesizer"], "architect",
                            depends_on=["Research"]),
            self._create_step("Report Generation", StepType.ANALYSIS,
                            "Generate research report", profile, 15,
                            [], "writer", depends_on=["Synthesis"]),
            self._create_step("Peer Review", StepType.REVIEW,
                            "Review findings", profile, 10,
                            ["review_architecture"], "reviewer",
                            depends_on=["Report Generation"]),
        ]
    
    def _gen_test_stage_canary_production(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for deployment."""
        return [
            self._create_step("Repository Analysis", StepType.ANALYSIS,
                            "Analyze deployment target", profile, 10,
                            ["repository_twin"], "devops"),
            self._create_step("Test Suite", StepType.VERIFICATION,
                            "Run full test suite", profile, 20,
                            ["test_pyramid"], "test_engineer"),
            self._create_step("Security Scan", StepType.VERIFICATION,
                            "Run security checks", profile, 15,
                            ["security_loop"], "security_engineer",
                            depends_on=["Test Suite"]),
            self._create_step("Staging Deployment", StepType.DEPLOYMENT,
                            "Deploy to staging", profile, 15,
                            ["deployment_intel"], "devops",
                            depends_on=["Security Scan"]),
            self._create_step("Smoke Tests", StepType.VERIFICATION,
                            "Run staging smoke tests", profile, 10,
                            ["test_pyramid"], "test_engineer",
                            depends_on=["Staging Deployment"]),
            self._create_step("Canary Deployment", StepType.DEPLOYMENT,
                            "Deploy canary to production", profile, 15,
                            ["deployment_intel"], "devops",
                            depends_on=["Smoke Tests"]),
            self._create_step("Canary Monitoring", StepType.ANALYSIS,
                            "Monitor canary health", profile, 10,
                            ["runtime_feedback"], "devops",
                            depends_on=["Canary Deployment"]),
            self._create_step("Full Rollout", StepType.DEPLOYMENT,
                            "Roll out to full production", profile, 15,
                            ["deployment_intel"], "devops",
                            depends_on=["Canary Monitoring"]),
            self._create_step("Production Verification", StepType.VERIFICATION,
                            "Verify production health", profile, 10,
                            ["runtime_feedback", "quality_gates"], "devops",
                            depends_on=["Full Rollout"]),
        ]
    
    def _gen_scan_analyze_remediate(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for security audit."""
        return [
            self._create_step("Repository Analysis", StepType.ANALYSIS,
                            "Analyze codebase for security", profile, 10,
                            ["repository_twin"], "security_engineer"),
            self._create_step("Static Analysis", StepType.ANALYSIS,
                            "Run static security analysis", profile, 15,
                            ["security_loop"], "security_engineer"),
            self._create_step("Dependency Audit", StepType.ANALYSIS,
                            "Audit dependencies for vulnerabilities", profile, 15,
                            ["dependency_intel"], "security_engineer"),
            self._create_step("Secret Scan", StepType.ANALYSIS,
                            "Scan for exposed secrets", profile, 10,
                            ["security_loop"], "security_engineer"),
            self._create_step("Penetration Testing", StepType.VERIFICATION,
                            "Test for exploitable vulnerabilities", profile, 20,
                            ["security_loop"], "security_engineer"),
            self._create_step("Remediation Plan", StepType.DESIGN,
                            "Design remediation approach", profile, 15,
                            ["architecture_synthesizer"], "security_engineer"),
            self._create_step("Remediation", StepType.IMPLEMENTATION,
                            "Fix vulnerabilities", profile,
                            profile.estimated_time_minutes,
                            ["code_generation"], "coder",
                            depends_on=["Remediation Plan"]),
            self._create_step("Verification", StepType.VERIFICATION,
                            "Verify fixes", profile, 15,
                            ["security_loop"], "security_engineer",
                            depends_on=["Remediation"]),
        ]
    
    def _gen_profile_hypothesize_benchmark(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for performance optimization."""
        return [
            self._create_step("Repository Analysis", StepType.ANALYSIS,
                            "Analyze codebase performance", profile, 10,
                            ["repository_twin", "code_graph"], "performance_engineer"),
            self._create_step("Profiling", StepType.ANALYSIS,
                            "Profile current performance", profile, 15,
                            ["performance_loop"], "performance_engineer"),
            self._create_step("Bottleneck Analysis", StepType.ANALYSIS,
                            "Identify bottlenecks", profile, 15,
                            ["performance_loop"], "performance_engineer",
                            depends_on=["Profiling"]),
            self._create_step("Optimization Design", StepType.DESIGN,
                            "Design optimizations", profile, 15,
                            ["architecture_synthesizer"], "performance_engineer",
                            depends_on=["Bottleneck Analysis"]),
            self._create_step("Implementation", StepType.IMPLEMENTATION,
                            "Implement optimizations", profile,
                            profile.estimated_time_minutes,
                            ["code_generation"], "coder",
                            depends_on=["Optimization Design"]),
            self._create_step("Benchmarking", StepType.VERIFICATION,
                            "Benchmark improvements", profile, 15,
                            ["performance_loop"], "performance_engineer",
                            depends_on=["Implementation"]),
            self._create_step("Regression Testing", StepType.VERIFICATION,
                            "Verify no regressions", profile, 15,
                            ["test_pyramid"], "test_engineer",
                            depends_on=["Implementation"]),
        ]
    
    def _gen_analyze_plan_execute_verify(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for migration."""
        return [
            self._create_step("Source Analysis", StepType.ANALYSIS,
                            "Analyze source system", profile, 15,
                            ["repository_twin", "code_graph"], "repository_analyst"),
            self._create_step("Target Research", StepType.RESEARCH,
                            "Research target system", profile, 15,
                            ["strategy_search"], "researcher"),
            self._create_step("Migration Plan", StepType.DESIGN,
                            "Design migration approach", profile, 20,
                            ["architecture_synthesizer", "database_change"],
                            "architect"),
            self._create_step("Backup Strategy", StepType.DESIGN,
                            "Plan backup and rollback", profile, 10,
                            ["database_change"], "devops"),
            self._create_step("Migration Execution", StepType.IMPLEMENTATION,
                            "Execute migration", profile,
                            profile.estimated_time_minutes,
                            ["code_generation"], "coder",
                            depends_on=["Migration Plan", "Backup Strategy"]),
            self._create_step("Data Verification", StepType.VERIFICATION,
                            "Verify data integrity", profile, 15,
                            ["test_oracle"], "test_engineer",
                            depends_on=["Migration Execution"]),
            self._create_step("Rollback Test", StepType.VERIFICATION,
                            "Test rollback procedure", profile, 10,
                            ["database_change"], "devops",
                            depends_on=["Migration Execution"]),
        ]
    
    def _gen_read_structure_write(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for documentation."""
        return [
            self._create_step("Repository Analysis", StepType.ANALYSIS,
                            "Analyze codebase structure", profile, 10,
                            ["repository_twin", "code_graph"], "analyst"),
            self._create_step("Documentation Planning", StepType.DESIGN,
                            "Plan documentation structure", profile, 10,
                            [], "writer"),
            self._create_step("Documentation Writing", StepType.IMPLEMENTATION,
                            "Write documentation", profile,
                            profile.estimated_time_minutes,
                            [], "writer"),
            self._create_step("Review", StepType.REVIEW,
                            "Review documentation", profile, 10,
                            ["review_architecture"], "reviewer",
                            depends_on=["Documentation Writing"]),
        ]
    
    def _gen_analyze_write_execute(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for testing."""
        return [
            self._create_step("Repository Analysis", StepType.ANALYSIS,
                            "Analyze codebase for testing", profile, 10,
                            ["repository_twin", "code_graph"], "test_engineer"),
            self._create_step("Test Planning", StepType.DESIGN,
                            "Design test strategy", profile, 15,
                            ["test_pyramid", "test_first_planner"], "test_engineer"),
            self._create_step("Test Implementation", StepType.IMPLEMENTATION,
                            "Write tests", profile,
                            profile.estimated_time_minutes,
                            ["code_generation"], "test_engineer",
                            depends_on=["Test Planning"]),
            self._create_step("Test Execution", StepType.VERIFICATION,
                            "Run test suite", profile, 15,
                            ["test_oracle"], "test_engineer",
                            depends_on=["Test Implementation"]),
            self._create_step("Coverage Analysis", StepType.ANALYSIS,
                            "Analyze test coverage", profile, 10,
                            ["test_pyramid"], "test_engineer",
                            depends_on=["Test Execution"]),
        ]
    
    def _gen_read_analyze_report(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for code review."""
        return [
            self._create_step("Code Reading", StepType.ANALYSIS,
                            "Read and understand code", profile, 10,
                            ["semantic_index"], "reviewer"),
            self._create_step("Static Analysis", StepType.ANALYSIS,
                            "Run static analysis tools", profile, 10,
                            [], "reviewer"),
            self._create_step("Security Analysis", StepType.ANALYSIS,
                            "Check for security issues", profile, 10,
                            ["security_loop"], "reviewer"),
            self._create_step("Pattern Analysis", StepType.ANALYSIS,
                            "Check for anti-patterns", profile, 10,
                            [], "reviewer"),
            self._create_step("Report Generation", StepType.SYNTHESIS,
                            "Generate review report", profile, 15,
                            [], "reviewer"),
        ]
    
    def _gen_assess_execute_verify(self, profile: ScenarioProfile) -> list[PlanStep]:
        """Generate steps for maintenance."""
        return [
            self._create_step("Repository Analysis", StepType.ANALYSIS,
                            "Assess codebase health", profile, 10,
                            ["repository_twin"], "analyst"),
            self._create_step("Issue Identification", StepType.ANALYSIS,
                            "Identify maintenance needs", profile, 15,
                            [], "analyst"),
            self._create_step("Execution", StepType.IMPLEMENTATION,
                            "Perform maintenance", profile,
                            profile.estimated_time_minutes,
                            ["code_generation"], "coder"),
            self._create_step("Verification", StepType.VERIFICATION,
                            "Verify changes", profile, 10,
                            ["test_pyramid"], "test_engineer",
                            depends_on=["Execution"]),
        ]
    
    def _create_step(self, name: str, step_type: StepType,
                     description: str, profile: ScenarioProfile,
                     duration: int, modules: list[str],
                     agent_role: str, agent_count: int = 1,
                     depends_on: list[str] | None = None,
                     parallel_with: list[str] | None = None) -> PlanStep:
        """Create a plan step."""
        return PlanStep(
            id=str(uuid.uuid4()),
            name=name,
            step_type=step_type,
            description=description,
            required_modules=modules,
            agent_role=agent_role,
            agent_count=agent_count,
            estimated_duration_min=duration,
            depends_on=depends_on or [],
            parallel_with=parallel_with or [],
        )
    
    def _calculate_parallelism(self, profile: ScenarioProfile) -> int:
        """Calculate maximum parallelism for the scenario."""
        topology_map = {
            "single": 1,
            "sequential": 1,
            "parallel": 4,
            "hierarchical": 8,
        }
        return topology_map.get(profile.recommended_topology, 1)
    
    def _generate_global_gates(self, profile: ScenarioProfile) -> list[str]:
        """Generate global quality gates."""
        gates = ["requirements_verified"]
        
        if profile.requires_testing:
            gates.append("tests_pass")
        
        if profile.requires_security_review:
            gates.append("security_pass")
        
        if profile.requires_review:
            gates.append("review_pass")
        
        gates.append("documentation_complete")
        
        return gates
    
    def _identify_adaptation_points(self, profile: ScenarioProfile,
                                     steps: list[PlanStep]) -> list[dict[str, Any]]:
        """Identify points where the plan can adapt based on results."""
        points = []
        
        for step in steps:
            if step.step_type == StepType.ANALYSIS:
                points.append({
                    "step_id": step.id,
                    "step_name": step.name,
                    "description": f"After {step.name}, reassess plan based on findings",
                    "can_change": ["complexity", "scope", "modules"],
                })
            elif step.step_type == StepType.VERIFICATION:
                points.append({
                    "step_id": step.id,
                    "step_name": step.name,
                    "description": f"After {step.name}, decide to proceed or iterate",
                    "can_change": ["backtrack_to_implementation", "add_steps", "skip_steps"],
                })
        
        return points
    
    def _generate_contingencies(self, profile: ScenarioProfile) -> list[dict[str, Any]]:
        """Generate contingency plans for risk mitigation."""
        contingencies = []
        
        if profile.risk_score > 0.5:
            contingencies.append({
                "trigger": "risk_score > 0.5",
                "action": "Add additional review gates",
            })
        
        if profile.requires_deployment:
            contingencies.append({
                "trigger": "deployment_failure",
                "action": "Automatic rollback to previous version",
            })
        
        if profile.scenario_type == ScenarioType.MIGRATION:
            contingencies.append({
                "trigger": "data_integrity_failure",
                "action": "Restore from backup and abort migration",
            })
        
        return contingencies
    
    def _load_plan_templates(self) -> dict[str, Any]:
        """Load plan templates for different scenario types."""
        return {}
    
    def get_state(self) -> dict[str, Any]:
        return {"id": self.id}
