"""
Hermes Intelligence OS Package (v8 Final Architecture)
======================================================
The unified 18-Plane Intelligence Operating System:
01. Universal Event Bus & Interaction Plane
02. Identity & Authority Plane (Authority != Capability)
03. External Safety & Trust Kernel (Taint Tracking, Gating)
04. Goal / Mission Plane (Invariants, Proof Requirements)
05. Executive Control Plane (14 OS Controllers Scheduler)
06. Context OS (Dynamic Partitions, Compaction, Rebalancing)
07. Memory OS (9 Domains + Persistent Trajectory Archive)
08. World Model OS (Entities, Beliefs, Causal + Tycho Active Abstraction)
09. Research & Knowledge OS (Unknown Detection, Cross-Source Verification)
10. Cognitive OS (Reasoning Modes + Pre-Action Meta-Reasoning Turn)
11. Planning & Search OS (Meta-Planner Architecture Selection)
12. Recursive Agent Fabric (Prime Agent Subagent Bounds & Direct Messaging)
13. Tool & Computer OS (Tool Envelope, REPL Kernel, Computer Agency)
14. Verification OS (L0–L6 Independence Tiers + 3-D Earned Completion Proofs)
15. Recovery OS (Taxonomy, Counterfactual Repair, AVO Stagnation Detection)
16. Learning & Curriculum OS (Skill Distillation + Agent0 Co-Evolving Curriculum)
17. Evolution Lab (AlphaEvolve/DGM Population Evolution + Anti-Reward-Hacking)
18. Runtime & Supervisor (AVO-Style External Supervisor + 24/7 Background Daemon)
"""

from .agent_fabric import AgentMessage, AgentRole, RecursiveAgentFabric, SubagentHandle
from .arch_search import ArchCandidate, ArchSearchEngine, SearchSpace, pareto_front
from .authority import AuthorityContext, AuthorityGate
from .capabilities import (
    CapabilityGraph,
    CapabilityKind,
    CapabilityManifest,
    CapabilityRegistry,
    CapabilitySelector,
    ExecutionCapabilityPlan,
)
from .cognitive import MetaCognitionEngine, MetaReasoningAssessment, ReasoningMode
from .cognitive_compiler import (
    CognitiveCompiler,
    ExecutionPlanIR,
    ExecutionWave,
    PlanningPhase,
    PlanningRecord,
    PlanValidityMonitor,
)
from .computer_os import ComputerOS, UIElement, UIElementType, UISnapshot
from .cron_expr import CronExpression, CronJob, CronTab
from .curriculum import CurriculumEngine, CurriculumTask, DifficultyTier
from .daemon import CheckpointSnapshot, MissionPriority, PersistentDaemonRuntime, QueuedMission
from .docker_sandbox import DockerSandbox, engine_available
from .drift import (
    DriftReport,
    DriftSeverity,
    EnvironmentDriftDetector,
    EnvironmentFingerprint,
    GoalDriftAlert,
    GoalDriftDetector,
)
from .dynamic_runtime import (
    DeepAgentsAdapter,
    DynamicStateGraph,
    GraphNode,
    IsolatedSubagentWorkspace,
    LangGraphDynamicAdapter,
)
from .eagle_adapter import EagleAdapter, EagleClaim
from .events import EventSource, HermesEvent, UniversalEventBus
from .evolution_lab import (
    AntiRewardHackingVerifier,
    ApprovalGate,
    BaselineTracker,
    HermesVariant,
    PopulationEvolutionLab,
)
from .executive import (
    AgentController,
    ContextController,
    DecisionController,
    EvolutionController,
    ExecutiveKernel,
    GoalController,
    HealthController,
    LearningController,
    MissionController,
    PlanningController,
    ResourceController,
    SafetyController,
    StateController,
    ToolController,
    VerificationController,
)
from .experiments import Experiment, ExperimentEngine
from .gateway import (
    AttentionPollResult,
    DeviceNode,
    ExternalHarnessBridge,
    ExternalHarnessType,
    HarnessSession,
    HeartbeatMonitor,
    NodeRegistry,
    NodeStatus,
    NodeType,
    OpenClawGateway,
)
from .hermes_controller import (
    HermesController,
    HermesInstance,
    ensure_hermes_on_path,
    get_hermes_home,
)
from .hermes_llm import HermesFirstLLMClient, hermes_local_available, resolve_tier
from .hooks import (
    HookAction,
    HookEventType,
    HookManager,
    HookResult,
    LifecycleHook,
    VerificationGates,
    VerificationLedger,
    HookContext,
    HookResult as VerificationHookResult,
    BlockReason,
    get_verification_gates,
    run_verification_gates,
    VerificationGateHookManager,
)
from .persona import PersonaSystem, PersonaFile, PersonaSection, get_persona_system, inject_persona_into_prompt
from .local_llm import LocalLLMRuntime, LlamaCppEngine, LLMConfig, GBNFCompiler, GBNFGrammar, create_local_llm, create_hermes_local_llm
from .engines.avo import GitLineageDAG, LineageNode, LineageNodeType, ScoreVector, StagnationSupervisor, AVOEvolutionEngine
from .invariants import INVARIANTS, verify_invariants
from .kernel import HermesIntelligenceOS
from .langsmith_exporter import (
    LangSmithConfig,
    LangSmithTelemetryExporter,
    LocalTraceSpan,
)
from .loops import LoopEngine
from .meta_planner import ExecutionArchitecture, MetaPlanner
from .mission_ir import (
    GoalGraph,
    GoalInvariant,
    GoalLifecycle,
    GoalMemory,
    GoalNode,
    MissionIR,
)
from .model_router import ModelEntry, ModelPortfolio
from .perception_store import (
    LosslessPerceptionStore,
    PerceptionModality,
    PerceptionRecord,
)
from .plane_cache import AdaptivePlaneSelector, MemoizationCache, OptimizationResult, ResultCache
from .plane_metrics import MetricsCollector, PlaneMetric
from .plugin_manifest import (
    PermissionRing,
    PluginManifest,
    check_free_gate,
    load_manifest,
    ring_allows,
)
from .process_guard import ProcessHandle, ProcessStatus, WatchdogConfig
from .process_guard import Watchdog as ProcessWatchdog
from .provenance import ProvenanceRecorder
from .recon import (
    EnvironmentReconEngine,
    EnvironmentState,
    HardwareProfile,
    WorkspaceReconProfile,
)
from .recovery import (
    AVOStagnationDetector,
    FailureCategory,
    FailureDiagnosis,
    RecoveryEngine,
    StagnationLevel,
    StagnationTelemetry,
)
from .research import CognitiveResearchEngine, VerifiedClaim
from .runtime_adapters import (
    CompositeDualSubstrateAdapter,
    DeepAgentsRuntimeAdapter,
    LangGraphRuntimeAdapter,
    OpenClawRuntimeAdapter,
    PrimeRuntimeAdapter,
)
from .runtime_router import RuntimeRouter
from .runtime_spi import (
    ExecutionResult,
    ExecutionStatus,
    RuntimeAdapter,
)
from .safety_kernel import SafetyKernel, SafetyVerdict, TaintMarker
from .scheduler import ContinuousScheduler, ScheduledJob
from .skills import SkillForge, SkillRegistry, SkillVersion
from .strategy_search import (
    PlanCritic,
    PlanReviewReport,
    SecondOpinionJudge,
    StrategyCandidate,
    StrategySearchEngine,
)
from .supervisor import (
    ExternalSupervisor,
    SupervisorTelemetry,
    SupervisoryAction,
    SupervisoryIntervention,
)
from .swarm_scaling import (
    AggregatedEvidencePacket,
    EvidenceCompressor,
    EvidenceItem,
    KimiSwarmScaler,
    SwarmTask,
    SwarmWorkerResult,
    SwarmWorkerRole,
)
from .tech_radar import RadarItem, SelfResearchEngine, TechRadar
from .tool_env import ToolDescriptor, ToolEnvironmentOS
from .tool_scoring import ToolScorecard
from .uncertainty import (
    EpistemicItem,
    EpistemicStatus,
    ResearchLaneType,
    ResearchPlan,
    ResearchQuery,
    UncertaintyAnalyzer,
)
from .watchdog import Watchdog, find_cycle

__all__ = [
    # Master OS & Loops
    "HermesIntelligenceOS",
    "LoopEngine",
    "ExecutionArchitecture",
    "MetaPlanner",
    # Interaction & Authority
    "HermesEvent",
    "EventSource",
    "UniversalEventBus",
    "AuthorityContext",
    "AuthorityGate",
    "SafetyKernel",
    "SafetyVerdict",
    "TaintMarker",
    # Executive & Controllers
    "ExecutiveKernel",
    "GoalController",
    "MissionController",
    "StateController",
    "DecisionController",
    "ContextController",
    "PlanningController",
    "AgentController",
    "ToolController",
    "ResourceController",
    "SafetyController",
    "VerificationController",
    "LearningController",
    "EvolutionController",
    "HealthController",
    # Research & Cognition
    "CognitiveResearchEngine",
    "VerifiedClaim",
    "MetaCognitionEngine",
    "MetaReasoningAssessment",
    "ReasoningMode",
    # Agent Fabric
    "RecursiveAgentFabric",
    "AgentRole",
    "AgentMessage",
    "SubagentHandle",
    # Tools & Computer
    "ToolEnvironmentOS",
    "ToolDescriptor",
    "ComputerOS",
    "UIElement",
    "UIElementType",
    "UISnapshot",
    # Recovery & Stagnation
    "RecoveryEngine",
    "FailureCategory",
    "FailureDiagnosis",
    "AVOStagnationDetector",
    "StagnationLevel",
    "StagnationTelemetry",
    # Curriculum & Evolution
    "CurriculumEngine",
    "CurriculumTask",
    "DifficultyTier",
    "PopulationEvolutionLab",
    "HermesVariant",
    "AntiRewardHackingVerifier",
    # Runtime & Supervisor
    "ExternalSupervisor",
    "SupervisorTelemetry",
    "SupervisoryAction",
    "SupervisoryIntervention",
    "PersistentDaemonRuntime",
    "CheckpointSnapshot",
    "QueuedMission",
    "MissionPriority",
    "ContinuousScheduler",
    "ScheduledJob",
    "HermesController",
    "HermesInstance",
    "ensure_hermes_on_path",
    "get_hermes_home",
    "INVARIANTS",
    "verify_invariants",
    "PermissionRing",
    "PluginManifest",
    "check_free_gate",
    "load_manifest",
    "ring_allows",
    "ApprovalGate",
    "BaselineTracker",
    "SkillRegistry",
    "SkillForge",
    "SkillVersion",
    "ModelPortfolio",
    "ModelEntry",
    "HermesFirstLLMClient",
    "hermes_local_available",
    "resolve_tier",
    "DockerSandbox",
    "engine_available",
    "EagleAdapter",
    "EagleClaim",
    "CronExpression",
    "CronJob",
    "CronTab",
    "ProcessHandle",
    "ProcessStatus",
    "ProcessWatchdog",
    "WatchdogConfig",
    "MetricsCollector",
    "PlaneMetric",
    "AdaptivePlaneSelector",
    "MemoizationCache",
    "OptimizationResult",
    "ResultCache",
    "ExperimentEngine",
    "Experiment",
    "ArchSearchEngine",
    "SearchSpace",
    "ArchCandidate",
    "pareto_front",
    "Watchdog",
    "find_cycle",
    "TechRadar",
    "SelfResearchEngine",
    "RadarItem",
    "ProvenanceRecorder",
    "ToolScorecard",
    # Frontier Additions: Hooks
    "HookEventType",
    "HookAction",
    "HookResult",
    "LifecycleHook",
    "HookManager",
    # Frontier Additions: Gateway & Nodes
    "NodeType",
    "NodeStatus",
    "DeviceNode",
    "NodeRegistry",
    "AttentionPollResult",
    "HeartbeatMonitor",
    "ExternalHarnessType",
    "HarnessSession",
    "ExternalHarnessBridge",
    "OpenClawGateway",
    # Frontier Additions: Kimi Swarm Scaling
    "SwarmWorkerRole",
    "SwarmTask",
    "SwarmWorkerResult",
    "EvidenceItem",
    "AggregatedEvidencePacket",
    "EvidenceCompressor",
    "KimiSwarmScaler",
    # Frontier Additions: Drift Detection
    "DriftSeverity",
    "EnvironmentFingerprint",
    "DriftReport",
    "EnvironmentDriftDetector",
    "GoalDriftAlert",
    "GoalDriftDetector",
    # Frontier Additions: Perception Store
    "PerceptionModality",
    "PerceptionRecord",
    "LosslessPerceptionStore",
    # v9 Cognitive Planning OS: Mission IR & Goal Graph
    "GoalGraph",
    "GoalInvariant",
    "GoalLifecycle",
    "GoalMemory",
    "GoalNode",
    "MissionIR",
    # v9 Cognitive Planning OS: Environment Recon
    "EnvironmentReconEngine",
    "EnvironmentState",
    "HardwareProfile",
    "WorkspaceReconProfile",
    # v9 Cognitive Planning OS: Capabilities
    "CapabilityGraph",
    "CapabilityKind",
    "CapabilityManifest",
    "CapabilityRegistry",
    "CapabilitySelector",
    "ExecutionCapabilityPlan",
    # v9 Cognitive Planning OS: Uncertainty & Research
    "EpistemicItem",
    "EpistemicStatus",
    "ResearchLaneType",
    "ResearchPlan",
    "ResearchQuery",
    "UncertaintyAnalyzer",
    # v9 Cognitive Planning OS: Strategy & Critic
    "PlanCritic",
    "PlanReviewReport",
    "SecondOpinionJudge",
    "StrategyCandidate",
    "StrategySearchEngine",
    # v9 Cognitive Planning OS: Cognitive Compiler
    "CognitiveCompiler",
    "ExecutionPlanIR",
    "ExecutionWave",
    "PlanningPhase",
    "PlanningRecord",
    "PlanValidityMonitor",
    # v9 Cognitive Planning OS: Dynamic Runtime Bridges
    "DeepAgentsAdapter",
    "DynamicStateGraph",
    "GraphNode",
    "IsolatedSubagentWorkspace",
    "LangGraphDynamicAdapter",
    # v9 Runtime Substrate SPI & Adapters (Dual-Substrate LangGraph + Deep Agents)
    "RuntimeAdapter",
    "ExecutionResult",
    "ExecutionStatus",
    "LangGraphRuntimeAdapter",
    "DeepAgentsRuntimeAdapter",
    "CompositeDualSubstrateAdapter",
    "OpenClawRuntimeAdapter",
    "PrimeRuntimeAdapter",
    "RuntimeRouter",
    # LangSmith Telemetry & Observability Exporter (Plane 01 & 18)
    "LangSmithConfig",
    "LangSmithTelemetryExporter",
    "LocalTraceSpan",
    # New: Persona System (Mercury Agent pattern)
    "PersonaSystem",
    "PersonaFile",
    "PersonaSection",
    "get_persona_system",
    "inject_persona_into_prompt",
    # New: Local LLM Runtime (Atomic Agent pattern)
    "LocalLLMRuntime",
    "LlamaCppEngine",
    "LLMConfig",
    "GBNFCompiler",
    "GBNFGrammar",
    "create_local_llm",
    "create_hermes_local_llm",
    # New: Verification Gates (Fable-5 pattern)
    "VerificationGates",
    "VerificationLedger",
    "HookContext",
    "HookResult",
    "HookEventType",
    "BlockReason",
    "get_verification_gates",
    "run_verification_gates",
    "VerificationGateHookManager",
    # New: Agent Team Coordinator (Apodex pattern)
    # (imported from hermes.agi.orchestration)
    # New: AVO Lineage + Supervisor (NVIDIA pattern)
    "GitLineageDAG",
    "LineageNode",
    "LineageNodeType",
    "ScoreVector",
    "StagnationSupervisor",
    "AVOEvolutionEngine",
]
