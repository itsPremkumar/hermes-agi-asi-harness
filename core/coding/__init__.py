"""Coding Intelligence Package."""
from .repository_twin import RepositoryDigitalTwin, FileNode, Symbol, Edge, Confidence, SymbolType, EdgeType
from .code_graph import CodeGraph, GraphNode, GraphEdge, BlastRadius, NodeType, RelationType
from .semantic_index import SemanticCodeIndex, CodeChunk, SearchQuery, SearchResult, IndexLevel
from .recon import RepositoryRecon, ReconResult, ReconStage
from .history_memory import HistoricalMemory, HistoryEntry, BugPattern, HistoryType
from .requirements import RequirementsCompiler, CompiledRequirements, Requirement, RequirementType, Priority
from .requirement_trace import RequirementTraceGraph, TraceNode, TraceEdge, TraceNodeType, TraceStatus
from .architecture import ArchitectureSynthesizer, ArchitectureCandidate, ArchitectureStyle
from .adr import ADRRegistry, ADR, ADRStatus
from .architecture_risk import ArchitectureRiskAnalyzer, Risk, RiskCategory, RiskSeverity
from .strategy_search import StrategySearcher, Strategy, StrategyEvaluation, StrategyType
from .task_graph import TaskGraph, Task, TaskStatus
from .dynamic_parallelism import ParallelScheduler
from .agent_specialization import AgentSpecialist, AgentSpec, AgentRole
from .worker_contract import ContractManager, WorkerContract
from .worktree_isolation import WorktreeManager, Worktree
from .artifact_registry import ArtifactRegistry, Artifact, ArtifactType
from .code_generation import CodeGenerationLoop, GenerationResult, GenerationStage
from .test_first import TestFirstPlanner
from .test_pyramid import TestPyramid, TestSuite, TestLayer
from .test_oracle import OracleManager, TestOracle, OracleType
from .security_loop import SecurityLoop, SecurityFinding, SecurityStage
from .skill_forge import SkillForge, Skill
from .curriculum import EngineeringCurriculum, Capability
from .transfer_learning import TransferLearning
from .coding_rsi import CodingRSI, RSIRResult, RSIRCandidateType
from .population_evolution import PopulationEvolution, Candidate
from .meta_rsi import MetaRSI
from .evaluation_pyramid import EvaluationPyramid, EvalLevel
from .quality_gates import QualityGates, Gate
from .merge_controller import MergeController
from .cross_repo import CrossRepoReasoning
from .api_contract import APIContractManager, APIContract
from .database_change import DatabaseChangeManager, MigrationPhase
from .performance_loop import PerformanceLoop
from .context_engineering import ContextEngineer
from .blackboard import Blackboard

__all__ = [
    "RepositoryDigitalTwin", "FileNode", "Symbol", "Edge", "Confidence", "SymbolType", "EdgeType",
    "CodeGraph", "GraphNode", "GraphEdge", "BlastRadius", "NodeType", "RelationType",
    "SemanticCodeIndex", "CodeChunk", "SearchQuery", "SearchResult", "IndexLevel",
    "RepositoryRecon", "ReconResult", "ReconStage",
    "HistoricalMemory", "HistoryEntry", "BugPattern", "HistoryType",
    "RequirementsCompiler", "CompiledRequirements", "Requirement", "RequirementType", "Priority",
    "RequirementTraceGraph", "TraceNode", "TraceEdge", "TraceNodeType", "TraceStatus",
    "ArchitectureSynthesizer", "ArchitectureCandidate", "ArchitectureStyle", "TradeoffAnalysis",
    "ADRRegistry", "ADR", "ADRStatus",
    "ArchitectureRiskAnalyzer", "Risk", "RiskCategory", "RiskSeverity",
    "StrategySearcher", "Strategy", "StrategyEvaluation", "StrategyType",
    "TaskGraph", "Task", "TaskStatus",
    "ParallelScheduler",
    "AgentSpecialist", "AgentSpec", "AgentRole",
    "ContractManager", "WorkerContract",
    "WorktreeManager", "Worktree",
    "ArtifactRegistry", "Artifact", "ArtifactType",
    "CodeGenerationLoop", "GenerationResult", "GenerationStage",
    "TestFirstPlanner",
    "TestPyramid", "TestSuite", "TestLayer",
    "OracleManager", "TestOracle", "OracleType",
    "SecurityLoop", "SecurityFinding", "SecurityStage",
    "SkillForge", "Skill",
    "EngineeringCurriculum", "Capability",
    "TransferLearning",
    "CodingRSI", "RSIRResult", "RSIRCandidateType",
    "PopulationEvolution", "Candidate",
    "MetaRSI",
    "EvaluationPyramid", "EvalLevel",
    "QualityGates", "Gate",
    "MergeController",
    "CrossRepoReasoning",
    "APIContractManager", "APIContract",
    "DatabaseChangeManager", "MigrationPhase",
    "PerformanceLoop",
    "ContextEngineer",
    "Blackboard",
]
