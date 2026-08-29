"""AgentOS — Operating System for AI Agents.

A runtime platform for orchestrating, scheduling, and governing
autonomous AI agents with resource control, sandboxing, and
multi-tenancy.

Modules:
    scheduler — Priority-based agent scheduling with preemption
    governor — Resource governor (CPU, memory, API rate limits)
    sandbox — Sandboxed execution environment
    bus — Inter-agent communication bus (pub/sub, RPC)
    state — Persistent state management (SQLite + WAL)
    plugins — WASM-based plugin system
    observability — OpenTelemetry traces and metrics
    tenancy — Multi-tenancy with resource quotas
    cli — Command-line interface
    dashboard — Web dashboard
"""

__version__ = "1.0.0"
__author__ = "Prem Kumar"
__license__ = "MIT"

from .scheduler import Agent, Priority, Scheduler, ScheduleResult
from .governor import ResourceGovernor, ResourceLimits, ResourceUsage
from .state import StateManager, StateError
from .bus import Message, Bus, BusError

__all__ = [
    "Agent",
    "Priority",
    "Scheduler",
    "ScheduleResult",
    "ResourceGovernor",
    "ResourceLimits",
    "ResourceUsage",
    "StateManager",
    "StateError",
    "Message",
    "Bus",
    "BusError",
    "__version__",
]
