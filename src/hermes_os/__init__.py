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
from .authority import AuthorityContext, AuthorityGate
from .cognitive import MetaCognitionEngine, MetaReasoningAssessment, ReasoningMode
from .computer_os import ComputerOS, UIElement, UIElementType, UISnapshot
from .curriculum import CurriculumEngine, CurriculumTask, DifficultyTier
from .daemon import CheckpointSnapshot, MissionPriority, PersistentDaemonRuntime, QueuedMission
from .events import EventSource, HermesEvent, UniversalEventBus
from .evolution_lab import AntiRewardHackingVerifier, HermesVariant, PopulationEvolutionLab
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
from .kernel import HermesIntelligenceOS
from .loops import LoopEngine
from .meta_planner import ExecutionArchitecture, MetaPlanner
from .recovery import (
    AVOStagnationDetector,
    FailureCategory,
    FailureDiagnosis,
    RecoveryEngine,
    StagnationLevel,
    StagnationTelemetry,
)
from .research import CognitiveResearchEngine, VerifiedClaim
from .safety_kernel import SafetyKernel, SafetyVerdict, TaintMarker
from .supervisor import (
    ExternalSupervisor,
    SupervisoryAction,
    SupervisoryIntervention,
    SupervisorTelemetry,
)
from .tool_env import ToolDescriptor, ToolEnvironmentOS
from .hooks import (
    HookAction,
    HookEventType,
    HookManager,
    HookResult,
    LifecycleHook,
)
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
from .swarm_scaling import (
    AggregatedEvidencePacket,
    EvidenceCompressor,
    EvidenceItem,
    KimiSwarmScaler,
    SwarmTask,
    SwarmWorkerResult,
    SwarmWorkerRole,
)
from .drift import (
    DriftReport,
    DriftSeverity,
    EnvironmentDriftDetector,
    EnvironmentFingerprint,
    GoalDriftAlert,
    GoalDriftDetector,
)
from .perception_store import (
    LosslessPerceptionStore,
    PerceptionModality,
    PerceptionRecord,
)
from .mission_ir import (
    GoalGraph,
    GoalInvariant,
    GoalLifecycle,
    GoalMemory,
    GoalNode,
    MissionIR,
)
from .recon import (
    EnvironmentReconEngine,
    EnvironmentState,
    HardwareProfile,
    WorkspaceReconProfile,
)
from .capabilities import (
    CapabilityGraph,
    CapabilityKind,
    CapabilityManifest,
    CapabilityRegistry,
    CapabilitySelector,
    ExecutionCapabilityPlan,
)
from .uncertainty import (
    EpistemicItem,
    EpistemicStatus,
    ResearchLaneType,
    ResearchPlan,
    ResearchQuery,
    UncertaintyAnalyzer,
)
from .strategy_search import (
    PlanCritic,
    PlanReviewReport,
    SecondOpinionJudge,
    StrategyCandidate,
    StrategySearchEngine,
)
from .cognitive_compiler import (
    CognitiveCompiler,
    ExecutionPlanIR,
    ExecutionWave,
    PlanningPhase,
    PlanningRecord,
    PlanValidityMonitor,
)
from .dynamic_runtime import (
    DeepAgentsAdapter,
    DynamicStateGraph,
    GraphNode,
    IsolatedSubagentWorkspace,
    LangGraphDynamicAdapter,
)

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
]
