"""
Hermes AGI/ASI Harness — Core Package v7.0

Contains the trusted kernel and all core subsystems.
Import individual modules directly for advanced features.
"""

# Core runtime
from .agents import AgentRegistry, active, spawn, terminate

# Brain and memory
from .brain import BrainError, EchoBrain, HermesBrain, ModelResponse, PlannerBrain
from .cognition import CognitiveRouter, CognitiveState
from .context_os import ContextOS

# Evaluation and planning
from .evaluator import EvalResult, evaluate

# Events and state
from .events.event_bus import Event, EventBus, EventType
from .frontier import STRATEGIES, select_next_parent
from .governance import check_plan, plan_hash, require_goal, round_budget_ok, supervise
from .memory import MemoryStore, retrieve, semantic_search
from .mission_compiler import MissionCompiler
from .planning import PlanningEngine
from .research_engine import ResearchEngine
from .runtime.kernel import HermesKernel, KernelConfig, KernelState, Task
from .runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
from .selfheal import RetryPolicy, self_heal

# Soul and mission
from .soul import Claim, CognitiveMode, EpistemicStatus, Mission, RiskTier
from .state.state_manager import StateManager
from .supervisor import supervisor_redirect
from .world_model import CausalModel, Confidence, Entity, WorldModel, WorldTransition
