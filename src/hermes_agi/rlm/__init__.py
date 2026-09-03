"""
Hermes AGI/ASI Harness — Recursive Language Model (RLM) Package.

Inspired by Prime Agent:
- Persistent in-memory Python REPL execution
- Exposing subagents as callable Python functions
- Programmatic manipulation of massive context variables
"""

from .environment import (
    RLMREPLExecutor,
    AgentContextBridge,
    REPLExecutionResult,
)

__all__ = [
    "RLMREPLExecutor",
    "AgentContextBridge",
    "REPLExecutionResult",
]
