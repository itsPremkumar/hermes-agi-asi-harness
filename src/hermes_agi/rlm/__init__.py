"""
Hermes AGI/ASI Harness — Recursive Language Model (RLM) Package.

Ported & Enhanced from Prime Agent (prime-agent-runtime/src/rlm/):
- Persistent CPython REPL with top-level `await`
- Recursive subagent spawning (`await rlm.run()`)
- Parallel fan-out (`await asyncio.gather(...)`)
- Memory heap snapshots and restorations
"""

from .environment import (
    RLMREPLExecutor,
    REPLExecutionResult,
)
from .bridge import (
    RLMBridge,
    RLMSpawnHandle,
)

__all__ = [
    "RLMREPLExecutor",
    "REPLExecutionResult",
    "RLMBridge",
    "RLMSpawnHandle",
]
