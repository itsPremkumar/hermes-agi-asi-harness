"""
HERMES INTELLIGENCE OS — UNIVERSAL RUNTIME ROUTER (v9)
======================================================
Meta-planner routing engine that assigns compiled ExecutionPlanIR contracts
to the optimal runtime substrate:
- LangGraph: For durable, long-running cyclic state graphs.
- Deep Agents: For isolated filesystem subagent teams and deep research.
- Composite Dual-Substrate: The recommended synergy of LangGraph (outer DAG)
  and Deep Agents (inner worker sandboxes).
- OpenClaw: For multi-device node execution.
- Prime: For programmable persistent REPL execution.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .cognitive_compiler import ExecutionPlanIR
from .runtime_adapters import (
    CompositeDualSubstrateAdapter,
    DeepAgentsRuntimeAdapter,
    LangGraphRuntimeAdapter,
    OpenClawRuntimeAdapter,
    PrimeRuntimeAdapter,
)
from .runtime_spi import ExecutionResult, RuntimeAdapter

logger = logging.getLogger("hermes.os.runtime_router")


class RuntimeRouter:
    """
    Central registry and dynamic router for execution substrates.
    Decouples the Hermes Executive from any concrete framework.
    """

    def __init__(self, workspace_root: str = ".", exporter: Optional[Any] = None):
        self.workspace_root = workspace_root
        self.exporter = exporter
        self._adapters: Dict[str, RuntimeAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        self.register_adapter(CompositeDualSubstrateAdapter(workspace_root=self.workspace_root, exporter=self.exporter))
        self.register_adapter(LangGraphRuntimeAdapter(workspace_root=self.workspace_root, exporter=self.exporter))
        self.register_adapter(DeepAgentsRuntimeAdapter(workspace_root=self.workspace_root, exporter=self.exporter))
        self.register_adapter(OpenClawRuntimeAdapter())
        self.register_adapter(PrimeRuntimeAdapter())

    def register_adapter(self, adapter: RuntimeAdapter) -> None:
        self._adapters[adapter.runtime_id] = adapter
        logger.debug(f"Registered runtime adapter '{adapter.runtime_id}': {adapter.description}")

    def get_adapter(self, runtime_id: str) -> Optional[RuntimeAdapter]:
        return self._adapters.get(runtime_id)

    def list_adapters(self) -> List[Dict[str, str]]:
        return [
            {"runtime_id": a.runtime_id, "description": a.description}
            for a in self._adapters.values()
        ]

    def route(self, plan: ExecutionPlanIR) -> RuntimeAdapter:
        """
        Intelligently selects the optimal execution substrate based on
        plan attributes (wave depth, parallelism, topology, capabilities).
        """
        # 1. Check if specific runtime is requested in capability plan
        for cap_plan in plan.capability_plans.values():
            if "tool.python_repl" in cap_plan.selected_tools and len(plan.task_graph.list_goals()) <= 2:
                # Fast single-task REPL execution
                prime = self.get_adapter("prime")
                if prime:
                    return prime

        # 2. If multi-device nodes requested
        if any("openclaw" in str(cp) for cp in plan.capability_plans.values()):
            oc = self.get_adapter("openclaw")
            if oc:
                return oc

        # 3. Default optimal substrate: Composite Dual-Substrate
        # (LangGraph durable outer DAG + Deep Agents isolated inner sandboxes)
        dual = self.get_adapter("composite_dual_substrate")
        if dual:
            return dual

        # Fallback to langgraph or first registered
        return list(self._adapters.values())[0]

    async def execute_plan(
        self,
        plan: ExecutionPlanIR,
        runtime_id: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute plan on selected or specified runtime substrate.
        """
        if runtime_id:
            adapter = self.get_adapter(runtime_id)
            if not adapter:
                raise ValueError(f"Unknown runtime adapter '{runtime_id}'")
        else:
            adapter = self.route(plan)

        logger.info(f"Routing mission {plan.mission_id} to runtime '{adapter.runtime_id}'")
        return await adapter.execute_plan(plan)
