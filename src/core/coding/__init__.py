"""Coding Intelligence Package."""
from .adr import ADR, ADRRegistry, ADRStatus
from .agent_specialization import AgentRole, AgentSpec, AgentSpecialist
from .api_contract import APIContract, APIContractManager
from .architecture import ArchitectureCandidate, ArchitectureStyle, ArchitectureSynthesizer
from .architecture_risk import ArchitectureRiskAnalyzer, Risk, RiskCategory, RiskSeverity
from .artifact_registry import Artifact, ArtifactRegistry, ArtifactType
from .blackboard import Blackboard
from .code_generation import CodeGenerationLoop, GenerationResult, GenerationStage
from .code_graph import BlastRadius, CodeGraph, GraphEdge, GraphNode, NodeType, RelationType
from .coding_rsi import CodingRSI, RSIRCandidateType, RSIRResult
from .context_engineering import ContextEngineer
from .cross_repo import CrossRepoReasoning
from .curriculum import Capability, EngineeringCurriculum
from .database_change import DatabaseChangeManager, MigrationPhase
from .dynamic_parallelism import ParallelScheduler
from .evaluation_pyramid import EvalLevel, EvaluationPyramid
from .history_memory import BugPattern, HistoricalMemory, HistoryEntry, HistoryType
from .merge_controller import MergeController
from .meta_rsi import MetaRSI
from .oracle_strategy import OracleManager, OracleType, TestOracle
from .performance_loop import PerformanceLoop
from .population_evolution import Candidate, PopulationEvolution
from .pyramid_planner import TestLayer, TestPyramid, TestSuite
from .quality_gates import Gate, QualityGates
from .recon import ReconResult, ReconStage, RepositoryRecon
from .repository_twin import (
    Confidence,
    Edge,
    EdgeType,
    FileNode,
    RepositoryDigitalTwin,
    Symbol,
    SymbolType,
)
from .requirement_trace import (
    RequirementTraceGraph,
    TraceEdge,
    TraceNode,
    TraceNodeType,
    TraceStatus,
)
from .requirements import (
    CompiledRequirements,
    Priority,
    Requirement,
    RequirementsCompiler,
    RequirementType,
)
from .security_loop import SecurityFinding, SecurityLoop, SecurityStage
from .semantic_index import CodeChunk, IndexLevel, SearchQuery, SearchResult, SemanticCodeIndex
from .skill_forge import Skill, SkillForge
from .strategy_search import Strategy, StrategyEvaluation, StrategySearcher, StrategyType
from .task_graph import Task, TaskGraph, TaskStatus
from .tdd_planner import TestFirstPlanner
from .transfer_learning import TransferLearning
from .worker_contract import ContractManager, WorkerContract
from .worktree_isolation import Worktree, WorktreeManager

__all__ = [
    "ADR",
    "ADRRegistry",
    "ADRStatus",
    "APIContract",
    "APIContractManager",
    "AgentRole",
    "AgentSpec",
    "AgentSpecialist",
    "ArchitectureCandidate",
    "ArchitectureRiskAnalyzer",
    "ArchitectureStyle",
    "ArchitectureSynthesizer",
    "Artifact",
    "ArtifactRegistry",
    "ArtifactType",
    "Blackboard",
    "BlastRadius",
    "BugPattern",
    "Candidate",
    "Capability",
    "CodeChunk",
    "CodeGenerationLoop",
    "CodeGraph",
    "CodingRSI",
    "CompiledRequirements",
    "Confidence",
    "ContextEngineer",
    "ContractManager",
    "CrossRepoReasoning",
    "DatabaseChangeManager",
    "Edge",
    "EdgeType",
    "EngineeringCurriculum",
    "EvalLevel",
    "EvaluationPyramid",
    "FileNode",
    "Gate",
    "GenerationResult",
    "GenerationStage",
    "GraphEdge",
    "GraphNode",
    "HistoricalMemory",
    "HistoryEntry",
    "HistoryType",
    "IndexLevel",
    "MergeController",
    "MetaRSI",
    "MigrationPhase",
    "NodeType",
    "OracleManager",
    "OracleType",
    "ParallelScheduler",
    "PerformanceLoop",
    "PopulationEvolution",
    "Priority",
    "QualityGates",
    "RSIRCandidateType",
    "RSIRResult",
    "ReconResult",
    "ReconStage",
    "RelationType",
    "RepositoryDigitalTwin",
    "RepositoryRecon",
    "Requirement",
    "RequirementTraceGraph",
    "RequirementType",
    "RequirementsCompiler",
    "Risk",
    "RiskCategory",
    "RiskSeverity",
    "SearchQuery",
    "SearchResult",
    "SecurityFinding",
    "SecurityLoop",
    "SecurityStage",
    "SemanticCodeIndex",
    "Skill",
    "SkillForge",
    "Strategy",
    "StrategyEvaluation",
    "StrategySearcher",
    "StrategyType",
    "Symbol",
    "SymbolType",
    "Task",
    "TaskGraph",
    "TaskStatus",
    "TestFirstPlanner",
    "TestLayer",
    "TestOracle",
    "TestPyramid",
    "TestSuite",
    "TraceEdge",
    "TraceNode",
    "TraceNodeType",
    "TraceStatus",
    "TradeoffAnalysis",
    "TransferLearning",
    "WorkerContract",
    "Worktree",
    "WorktreeManager",
]
