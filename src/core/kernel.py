#!/usr/bin/env python3
"""
core/kernel.py — Plugin kernel entry point.

The spec deliverable lists this path. It re-exports the generic AgentKernel that
discovers and loads the 21 working plugins. The full implementation lives in
core/runtime/agent_kernel.py; this module exists so `import core.kernel` works
exactly as the architecture spec names it, without disturbing the pre-existing
core/runtime/kernel.py (HermesKernel) used by hermes_agi.py.
"""

from __future__ import annotations

from core.runtime.agent_kernel import (
    WORKING_PLUGINS,
    AgentKernel,
    build_kernel,
)

__all__ = ["WORKING_PLUGINS", "AgentKernel", "build_kernel"]
