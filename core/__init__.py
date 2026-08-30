"""
Hermes AGI/ASI Harness — Core Package v7.0

Contains the trusted kernel and all core subsystems.
Import individual modules directly for advanced features.
"""

# Core runtime
from .runtime.kernel import HermesKernel, KernelConfig, KernelState, Task
from .runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState

# Events and state
from .events.event_bus import EventBus, Event, EventType
from .state.state_manager import StateManager

# Brain and memory
from .brain import HermesBrain, EchoBrain, BrainError, PlannerBrain, ModelResponse
from .memory import MemoryStore, semantic_search, retrieve

# Evaluation and planning
from .evaluator import EvalResult, evaluate
from .frontier import select_next_parent, STRATEGIES
from .agents import AgentRegistry, spawn, terminate, active
from .selfheal import self_heal, RetryPolicy
from .supervisor import supervisor_redirect
from .governance import plan_hash, check_plan, require_goal, supervise, round_budget_ok

# Soul and mission
from .soul import Mission, Claim, RiskTier, EpistemicStatus, CognitiveMode
from .mission_compiler import MissionCompiler
from .world_model import WorldModel, Entity, CausalModel, WorldTransition, Confidence
from .cognition import CognitiveRouter, CognitiveState
from .research_engine import ResearchEngine
from .planning import PlanningEngine
from .context_os import ContextOS
