"""
Dynamic Scenario Analyzer — Understand what kind of work is needed.

Analyzes goals, projects, and requirements to dynamically determine:
- Scenario type (new project, feature, bug fix, refactor, research, etc.)
- Complexity level (simple, moderate, high, extreme)
- Required capabilities and modules
- Optimal workflow and strategy
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ScenarioType(str, Enum):
    NEW_PROJECT = "new_project"
    FEATURE_ADDITION = "feature_addition"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    RESEARCH = "research"
    DEPLOYMENT = "deployment"
    CODE_REVIEW = "code_review"
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    MIGRATION = "migration"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DEBUGGING = "debugging"
    MAINTENANCE = "maintenance"


class ComplexityLevel(str, Enum):
    SIMPLE = "simple"           # Single file, single concern
    MODERATE = "moderate"       # Multiple files, clear dependencies
    HIGH = "high"               # Multiple components, unclear dependencies
    EXTREME = "extreme"         # System-wide changes, architectural decisions


class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ScenarioProfile:
    """Complete profile of a scenario."""
    id: str
    goal: str
    scenario_type: ScenarioType
    complexity: ComplexityLevel
    priority: PriorityLevel
    
    # Detected attributes
    requires_repository_model: bool = False
    requires_architecture_synthesis: bool = False
    requires_research: bool = False
    requires_testing: bool = False
    requires_security_review: bool = False
    requires_deployment: bool = False
    requires_review: bool = False
    requires_debugging: bool = False
    
    # Detected technologies
    detected_languages: List[str] = field(default_factory=list)
    detected_frameworks: List[str] = field(default_factory=list)
    detected_databases: List[str] = field(default_factory=list)
    detected_infrastructure: List[str] = field(default_factory=list)
    
    # Estimated effort
    estimated_files_affected: int = 0
    estimated_time_minutes: int = 0
    
    # Required modules
    required_modules: List[str] = field(default_factory=list)
    
    # Strategy
    recommended_workflow: str = ""
    recommended_topology: str = "single"
    
    # Risk
    risk_score: float = 0.5
    risk_factors: List[str] = field(default_factory=list)


class DynamicScenarioAnalyzer:
    """Analyze any goal and dynamically determine the optimal approach."""
    
    def __init__(self):
        self.id = str(uuid.uuid4())
    
    def analyze(self, goal: str, project_context: Dict[str, Any] = None) -> ScenarioProfile:
        """
        Perform complete analysis of a goal/project.
        
        This is the core entry point — it examines everything and produces
        a complete scenario profile that drives all subsequent decisions.
        """
        profile = ScenarioProfile(
            id=str(uuid.uuid4()),
            goal=goal,
            scenario_type=ScenarioType.FEATURE_ADDITION,
            complexity=ComplexityLevel.MODERATE,
            priority=PriorityLevel.MEDIUM,
        )
        
        # Step 1: Classify scenario type
        profile.scenario_type = self._classify_scenario(goal, project_context)
        
        # Step 2: Assess complexity
        profile.complexity = self._assess_complexity(goal, project_context)
        
        # Step 3: Determine priority
        profile.priority = self._determine_priority(goal, project_context)
        
        # Step 4: Detect technologies
        tech = self._detect_technologies(goal, project_context)
        profile.detected_languages = tech.get("languages", [])
        profile.detected_frameworks = tech.get("frameworks", [])
        profile.detected_databases = tech.get("databases", [])
        profile.detected_infrastructure = tech.get("infrastructure", [])
        
        # Step 5: Determine required capabilities
        self._determine_required_capabilities(profile)
        
        # Step 6: Estimate effort
        profile.estimated_files_affected = self._estimate_files(profile)
        profile.estimated_time_minutes = self._estimate_time(profile)
        
        # Step 7: Select modules and strategy
        profile.required_modules = self._select_modules(profile)
        profile.recommended_workflow = self._select_workflow(profile)
        profile.recommended_topology = self._select_topology(profile)
        
        # Step 8: Assess risk
        risk = self._assess_risk(profile)
        profile.risk_score = risk.get("score", 0.5)
        profile.risk_factors = risk.get("factors", [])
        
        return profile
    
    def _classify_scenario(self, goal: str,
                           project_context: Dict[str, Any] = None) -> ScenarioType:
        """Classify the scenario type from the goal text."""
        goal_lower = goal.lower()
        
        # Bug fix patterns
        if any(p in goal_lower for p in [
            "fix", "bug", "broken", "not working", "error", "crash", "issue",
            "defect", "failing", "incorrect", "wrong", "unexpected"
        ]):
            return ScenarioType.BUG_FIX
        
        # Research patterns
        if any(p in goal_lower for p in [
            "research", "investigate", "explore", "analyze", "understand",
            "study", "survey", "compare", "evaluate options"
        ]):
            return ScenarioType.RESEARCH
        
        # Refactor patterns
        if any(p in goal_lower for p in [
            "refactor", "restructure", "reorganize", "clean up", "cleanup",
            "simplify", "modernize", "migrate from", "upgrade"
        ]):
            return ScenarioType.REFACTOR
        
        # Deployment patterns
        if any(p in goal_lower for p in [
            "deploy", "release", "ship", "publish", "roll out", "rollout",
            "production", "staging", "ci/cd", "pipeline"
        ]):
            return ScenarioType.DEPLOYMENT
        
        # Security patterns (check before feature patterns since "auth" is in "authentication")
        if any(p in goal_lower for p in [
            "security", "vulnerability", "audit", "penetration", "exploit",
            "secure ", " encrypt", "xss", "sql injection"
        ]):
            # Only classify as security if it's primarily about security
            security_terms = ["security", "vulnerability", "audit", "penetration", "exploit", "secure ", " encrypt"]
            if sum(1 for t in security_terms if t in goal_lower) >= 2:
                return ScenarioType.SECURITY_AUDIT
        
        # Feature patterns (new project)
        
        # Performance patterns
        if any(p in goal_lower for p in [
            "performance", "optimize", "speed", "slow", "latency", "cache",
            "benchmark", "scale", "throughput", "memory"
        ]):
            return ScenarioType.PERFORMANCE_OPTIMIZATION
        
        # Testing patterns
        if any(p in goal_lower for p in [
            "test", "coverage", "unit test", "integration test", "e2e",
            "spec", "assertion", "mock"
        ]):
            return ScenarioType.TESTING
        
        # Documentation patterns
        if any(p in goal_lower for p in [
            "document", "docs", "readme", "comment", "guide", "tutorial",
            "api docs", "changelog"
        ]):
            return ScenarioType.DOCUMENTATION
        
        # Migration patterns
        if any(p in goal_lower for p in [
            "migrate", "migration", "move from", "convert", "transition",
            "port", "upgrade", "database migration"
        ]):
            return ScenarioType.MIGRATION
        
        # Code review patterns
        if any(p in goal_lower for p in [
            "review", "pull request", "pr", "code review", "feedback",
            "suggest improvements", "critique"
        ]):
            return ScenarioType.CODE_REVIEW
        
        # New project patterns
        if any(p in goal_lower for p in [
            "create", "new project", "scaffold", "setup", "initialize",
            "build a", "make a", "develop a", "start a"
        ]):
            return ScenarioType.NEW_PROJECT
        
        # Default: feature addition
        return ScenarioType.FEATURE_ADDITION
    
    def _assess_complexity(self, goal: str,
                           project_context: Dict[str, Any] = None) -> ComplexityLevel:
        """Assess the complexity of the scenario."""
        goal_lower = goal.lower()
        complexity_score = 0
        
        # Word count indicator
        word_count = len(goal.split())
        if word_count > 50:
            complexity_score += 2
        elif word_count > 20:
            complexity_score += 1
        
        # Scope indicators
        high_scope = ["system", "architecture", "all", "every", "complete", "full", "entire"]
        for term in high_scope:
            if term in goal_lower:
                complexity_score += 2
                break
        
        # Technology diversity
        tech_terms = ["database", "api", "frontend", "backend", "service", "microservice"]
        tech_count = sum(1 for t in tech_terms if t in goal_lower)
        complexity_score += tech_count
        
        # Dependency indicators
        if any(p in goal_lower for p in ["depends on", "integration", "connected", "related"]):
            complexity_score += 1
        
        # Project size from context
        if project_context:
            file_count = project_context.get("file_count", 0)
            if file_count > 100:
                complexity_score += 2
            elif file_count > 20:
                complexity_score += 1
        
        if complexity_score >= 6:
            return ComplexityLevel.EXTREME
        elif complexity_score >= 4:
            return ComplexityLevel.HIGH
        elif complexity_score >= 2:
            return ComplexityLevel.MODERATE
        return ComplexityLevel.SIMPLE
    
    def _determine_priority(self, goal: str,
                            project_context: Dict[str, Any] = None) -> PriorityLevel:
        """Determine priority from goal text."""
        goal_lower = goal.lower()
        
        if any(p in goal_lower for p in ["critical", "urgent", "emergency", "production down", "data loss"]):
            return PriorityLevel.CRITICAL
        elif any(p in goal_lower for p in ["high priority", "important", "asap", "blocking", "deadline"]):
            return PriorityLevel.HIGH
        elif any(p in goal_lower for p in ["low priority", "nice to have", "eventually", "when possible"]):
            return PriorityLevel.LOW
        return PriorityLevel.MEDIUM
    
    def _detect_technologies(self, goal: str,
                             project_context: Dict[str, Any] = None) -> Dict[str, List[str]]:
        """Detect technologies mentioned or present in the project."""
        detected = {"languages": [], "frameworks": [], "databases": [], "infrastructure": []}
        
        # Language detection
        language_map = {
            "python": ["python", "py", "django", "flask", "fastapi"],
            "javascript": ["javascript", "js", "node", "nodejs", "npm"],
            "typescript": ["typescript", "ts", "tsx"],
            "java": ["java", "spring", "maven", "gradle"],
            "go": ["golang", "go ", "goroutine"],
            "rust": ["rust", "cargo", "crate"],
            "ruby": ["ruby", "rails", "gem"],
            "php": ["php", "laravel", "composer"],
            "swift": ["swift", "swiftui", "ios"],
            "kotlin": ["kotlin", "android"],
            "sql": ["sql", "mysql", "postgresql", "sqlite"],
            "html": ["html", "css", "web"],
        }
        
        goal_lower = goal.lower()
        for lang, keywords in language_map.items():
            if any(kw in goal_lower for kw in keywords):
                detected["languages"].append(lang)
        
        # Framework detection
        framework_map = {
            "react": ["react", "reactjs"],
            "vue": ["vue", "vuejs"],
            "angular": ["angular"],
            "django": ["django"],
            "flask": ["flask"],
            "fastapi": ["fastapi"],
            "express": ["express"],
            "spring": ["spring", "spring boot"],
            "nextjs": ["next", "nextjs"],
            "docker": ["docker", "container"],
            "kubernetes": ["kubernetes", "k8s"],
        }
        
        for fw, keywords in framework_map.items():
            if any(kw in goal_lower for kw in keywords):
                detected["frameworks"].append(fw)
        
        # Database detection
        db_keywords = {
            "postgresql": ["postgres", "postgresql"],
            "mysql": ["mysql"],
            "mongodb": ["mongo", "mongodb"],
            "redis": ["redis"],
            "sqlite": ["sqlite"],
            "elasticsearch": ["elastic", "elasticsearch"],
        }
        
        for db, keywords in db_keywords.items():
            if any(kw in goal_lower for kw in keywords):
                detected["databases"].append(db)
        
        # Infrastructure detection
        infra_keywords = {
            "aws": ["aws", "amazon"],
            "gcp": ["gcp", "google cloud"],
            "azure": ["azure", "microsoft"],
            "github-actions": ["github actions", "ci/cd"],
            "terraform": ["terraform", "iac"],
        }
        
        for infra, keywords in infra_keywords.items():
            if any(kw in goal_lower for kw in keywords):
                detected["infrastructure"].append(infra)
        
        # If project context has file info, use it
        if project_context and project_context.get("languages"):
            for lang in project_context["languages"]:
                if lang not in detected["languages"]:
                    detected["languages"].append(lang)
        
        return detected
    
    def _determine_required_capabilities(self, profile: ScenarioProfile):
        """Determine which capabilities are required for this scenario."""
        st = profile.scenario_type
        
        if st == ScenarioType.NEW_PROJECT:
            profile.requires_repository_model = False
            profile.requires_architecture_synthesis = True
            profile.requires_research = False
            profile.requires_testing = True
            profile.requires_security_review = False
            profile.requires_deployment = False
            profile.requires_review = True
            profile.requires_debugging = False
        
        elif st == ScenarioType.FEATURE_ADDITION:
            profile.requires_repository_model = True
            profile.requires_architecture_synthesis = profile.complexity in (ComplexityLevel.HIGH, ComplexityLevel.EXTREME)
            profile.requires_research = False
            profile.requires_testing = True
            profile.requires_security_review = False
            profile.requires_deployment = False
            profile.requires_review = True
            profile.requires_debugging = False
        
        elif st == ScenarioType.BUG_FIX:
            profile.requires_repository_model = True
            profile.requires_architecture_synthesis = False
            profile.requires_research = True
            profile.requires_testing = True
            profile.requires_security_review = False
            profile.requires_deployment = False
            profile.requires_review = True
            profile.requires_debugging = True
        
        elif st == ScenarioType.REFACTOR:
            profile.requires_repository_model = True
            profile.requires_architecture_synthesis = True
            profile.requires_research = False
            profile.requires_testing = True
            profile.requires_security_review = False
            profile.requires_deployment = False
            profile.requires_review = True
            profile.requires_debugging = False
        
        elif st == ScenarioType.RESEARCH:
            profile.requires_repository_model = True
            profile.requires_architecture_synthesis = False
            profile.requires_research = True
            profile.requires_testing = False
            profile.requires_security_review = False
            profile.requires_deployment = False
            profile.requires_review = True
            profile.requires_debugging = False
        
        elif st == ScenarioType.DEPLOYMENT:
            profile.requires_repository_model = True
            profile.requires_architecture_synthesis = False
            profile.requires_research = False
            profile.requires_testing = True
            profile.requires_security_review = True
            profile.requires_deployment = True
            profile.requires_review = True
            profile.requires_debugging = False
        
        elif st == ScenarioType.SECURITY_AUDIT:
            profile.requires_repository_model = True
            profile.requires_architecture_synthesis = False
            profile.requires_research = True
            profile.requires_testing = True
            profile.requires_security_review = True
            profile.requires_deployment = False
            profile.requires_review = True
            profile.requires_debugging = False
        
        elif st == ScenarioType.PERFORMANCE_OPTIMIZATION:
            profile.requires_repository_model = True
            profile.requires_architecture_synthesis = False
            profile.requires_research = True
            profile.requires_testing = True
            profile.requires_security_review = False
            profile.requires_deployment = False
            profile.requires_review = True
            profile.requires_debugging = True
        
        elif st == ScenarioType.TESTING:
            profile.requires_repository_model = True
            profile.requires_architecture_synthesis = False
            profile.requires_research = False
            profile.requires_testing = True
            profile.requires_security_review = False
            profile.requires_deployment = False
            profile.requires_review = True
            profile.requires_debugging = False
        
        elif st == ScenarioType.MIGRATION:
            profile.requires_repository_model = True
            profile.requires_architecture_synthesis = True
            profile.requires_research = True
            profile.requires_testing = True
            profile.requires_security_review = False
            profile.requires_deployment = True
            profile.requires_review = True
            profile.requires_debugging = False
        
        elif st == ScenarioType.CODE_REVIEW:
            profile.requires_repository_model = True
            profile.requires_architecture_synthesis = False
            profile.requires_research = False
            profile.requires_testing = False
            profile.requires_security_review = True
            profile.requires_deployment = False
            profile.requires_review = True
            profile.requires_debugging = False
    
    def _estimate_files(self, profile: ScenarioProfile) -> int:
        """Estimate number of files affected."""
        estimates = {
            ScenarioType.NEW_PROJECT: 10,
            ScenarioType.FEATURE_ADDITION: 5,
            ScenarioType.BUG_FIX: 2,
            ScenarioType.REFACTOR: 15,
            ScenarioType.RESEARCH: 0,
            ScenarioType.DEPLOYMENT: 3,
            ScenarioType.CODE_REVIEW: 5,
            ScenarioType.SECURITY_AUDIT: 20,
            ScenarioType.PERFORMANCE_OPTIMIZATION: 8,
            ScenarioType.MIGRATION: 25,
            ScenarioType.DOCUMENTATION: 5,
            ScenarioType.TESTING: 10,
            ScenarioType.DEBUGGING: 3,
            ScenarioType.MAINTENANCE: 5,
        }
        base = estimates.get(profile.scenario_type, 5)
        
        complexity_multiplier = {
            ComplexityLevel.SIMPLE: 0.5,
            ComplexityLevel.MODERATE: 1.0,
            ComplexityLevel.HIGH: 2.0,
            ComplexityLevel.EXTREME: 4.0,
        }
        
        return int(base * complexity_multiplier.get(profile.complexity, 1.0))
    
    def _estimate_time(self, profile: ScenarioProfile) -> int:
        """Estimate time in minutes."""
        base_time = profile.estimated_files_affected * 10  # 10 min per file base
        
        complexity_multiplier = {
            ComplexityLevel.SIMPLE: 0.5,
            ComplexityLevel.MODERATE: 1.0,
            ComplexityLevel.HIGH: 2.0,
            ComplexityLevel.EXTREME: 5.0,
        }
        
        return int(base_time * complexity_multiplier.get(profile.complexity, 1.0))
    
    def _select_modules(self, profile: ScenarioProfile) -> List[str]:
        """Dynamically select which modules are needed."""
        modules = []
        
        # Core modules always needed
        modules.extend([
            "requirements_compiler",
            "task_graph",
            "artifact_registry",
        ])
        
        # Conditional modules based on capabilities
        if profile.requires_repository_model:
            modules.extend(["repository_twin", "code_graph", "semantic_index", "recon"])
        
        if profile.requires_architecture_synthesis:
            modules.extend(["architecture_synthesizer", "adr_registry", "architecture_risk"])
        
        if profile.requires_research:
            modules.extend(["strategy_search", "cross_repo"])
        
        if profile.requires_testing:
            modules.extend(["test_first_planner", "test_pyramid", "test_oracle"])
        
        if profile.requires_security_review:
            modules.append("security_loop")
        
        if profile.requires_deployment:
            modules.extend(["quality_gates", "merge_controller"])
        
        if profile.requires_review:
            modules.append("review_architecture")
        
        if profile.requires_debugging:
            modules.extend(["debugging", "hypothesis_debug", "failure_localization"])
        
        # Always include these for quality
        modules.extend([
            "quality_gates",
            "merge_controller",
            "evaluation_pyramid",
        ])
        
        return list(set(modules))
    
    def _select_workflow(self, profile: ScenarioProfile) -> str:
        """Select the optimal workflow pattern."""
        workflows = {
            ScenarioType.NEW_PROJECT: "architecture_first",
            ScenarioType.FEATURE_ADDITION: "understand_implement_test",
            ScenarioType.BUG_FIX: "reproduce_diagnose_fix",
            ScenarioType.REFACTOR: "analyze_design_implement",
            ScenarioType.RESEARCH: "explore_synthesize_report",
            ScenarioType.DEPLOYMENT: "test_stage_canary_production",
            ScenarioType.SECURITY_AUDIT: "scan_analyze_remediate",
            ScenarioType.PERFORMANCE_OPTIMIZATION: "profile_hypothesize_benchmark",
            ScenarioType.MIGRATION: "analyze_plan_execute_verify",
            ScenarioType.DOCUMENTATION: "read_structure_write",
            ScenarioType.TESTING: "analyze_write_execute",
            ScenarioType.DEBUGGING: "reproduce_localize_fix",
            ScenarioType.CODE_REVIEW: "read_analyze_report",
            ScenarioType.MAINTENANCE: "assess_execute_verify",
        }
        return workflows.get(profile.scenario_type, "understand_implement_test")
    
    def _select_topology(self, profile: ScenarioProfile) -> str:
        """Select the optimal agent topology."""
        if profile.complexity == ComplexityLevel.SIMPLE:
            return "single"
        elif profile.complexity == ComplexityLevel.MODERATE:
            return "sequential"
        elif profile.complexity == ComplexityLevel.HIGH:
            return "parallel"
        elif profile.complexity == ComplexityLevel.EXTREME:
            return "hierarchical"
        return "sequential"
    
    def _assess_risk(self, profile: ScenarioProfile) -> Dict[str, Any]:
        """Assess risk factors."""
        factors = []
        score = 0.0
        
        if profile.complexity == ComplexityLevel.EXTREME:
            factors.append("Extreme complexity - many unknowns")
            score += 0.3
        elif profile.complexity == ComplexityLevel.HIGH:
            factors.append("High complexity - unclear dependencies")
            score += 0.2
        
        if profile.requires_deployment:
            factors.append("Deployment to production environment")
            score += 0.2
        
        if profile.requires_security_review:
            factors.append("Security-sensitive changes")
            score += 0.15
        
        if profile.scenario_type == ScenarioType.MIGRATION:
            factors.append("Data migration risk")
            score += 0.2
        
        if profile.scenario_type == ScenarioType.REFACTOR:
            factors.append("Behavioral changes during refactor")
            score += 0.1
        
        if profile.estimated_files_affected > 20:
            factors.append("Large blast radius")
            score += 0.1
        
        return {"score": min(1.0, score), "factors": factors}
    
    def get_state(self) -> Dict[str, Any]:
        return {"id": self.id}
