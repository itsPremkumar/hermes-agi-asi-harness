"""Harness Runtime Kernel — LangGraph StateGraph Builder.

Builds a real LangGraph StateGraph using the langgraph library (v1.0.1+).
Full Cognitive Loop:
START -> init -> research -> think -> plan -> dispatch -> monitor -> verify -> complete -> END
                                          ^                     |
                                          |---- adjust <--------|
                                          |---- evolve <--------|
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from langgraph.graph import StateGraph, START, END

from harnix.state import AgentState, AgentPhase
from harnix.nodes import (
    init_node,
    research_node,
    think_node,
    plan_node,
    dispatch_node,
    rlm_node,
    monitor_node,
    verify_node,
    adjust_node,
    evolve_node,
    complete_node,
    route_after_dispatch,
    route_after_monitor,
    route_after_verify,
    route_after_adjust,
    route_after_evolve,
)

logger = logging.getLogger("hermes.runtime_kernel")


class HarnessRuntimeKernel:
    """Harness Runtime Kernel — LangGraph StateGraph + Multi-Step ASI Lifecycle.

    Usage:
        kernel = HarnessRuntimeKernel()
        result = kernel.run("write file demo.txt containing HELLO")
    """

    def __init__(
        self,
        max_iterations: int = 20,
        max_stalls: int = 5,
        checkpoint_saver: Any = None,
    ):
        self._max_iterations = max_iterations
        self._max_stalls = max_stalls
        self._checkpoint_saver = checkpoint_saver
        self._graph = None
        self._app = None

    def build(self) -> "HarnessRuntimeKernel":
        """Build the LangGraph StateGraph."""
        builder = StateGraph(AgentState)

        # Add nodes
        builder.add_node("init", init_node)
        builder.add_node("research", research_node)
        builder.add_node("think", think_node)
        builder.add_node("plan", plan_node)
        builder.add_node("dispatch", dispatch_node)
        builder.add_node("rlm", rlm_node)
        builder.add_node("monitor", monitor_node)
        builder.add_node("verify", verify_node)
        builder.add_node("adjust", adjust_node)
        builder.add_node("evolve", evolve_node)
        builder.add_node("complete", complete_node)

        # Linear cognitive intake pipeline
        builder.add_edge(START, "init")
        builder.add_edge("init", "research")
        builder.add_edge("research", "think")
        builder.add_edge("think", "plan")
        builder.add_edge("plan", "dispatch")
        builder.add_edge("dispatch", "monitor")
        builder.add_edge("rlm", "monitor")

        # Conditional edges from monitor
        builder.add_conditional_edges(
            "monitor",
            route_after_monitor,
            {
                "dispatch": "dispatch",
                "adjust": "adjust",
                "evolve": "evolve",
                "verify": "verify",
                "complete": "complete",
            },
        )

        # Conditional edges from verify
        builder.add_conditional_edges(
            "verify",
            route_after_verify,
            {
                "complete": "complete",
                "adjust": "adjust",
            },
        )

        # Conditional edges from adjust
        builder.add_conditional_edges(
            "adjust",
            route_after_adjust,
            {"dispatch": "dispatch"},
        )

        # Conditional edges from evolve
        builder.add_conditional_edges(
            "evolve",
            route_after_evolve,
            {"dispatch": "dispatch"},
        )

        builder.add_edge("complete", END)

        # Compile with optional checkpointing
        if self._checkpoint_saver:
            self._app = builder.compile(checkpointer=self._checkpoint_saver)
        else:
            self._app = builder.compile()

        self._graph = builder
        logger.info("HarnessRuntimeKernel built successfully with full cognitive pipeline")
        return self

    def run(self, task_description: str, **kwargs: Any) -> AgentState:
        """Run the kernel on a task."""
        if self._app is None:
            self.build()

        from harnix.state import create_initial_state

        initial_state = create_initial_state(
            task_description=task_description,
            max_iterations=self._max_iterations,
            max_stalls=self._max_stalls,
            **kwargs,
        )

        result = self._app.invoke(initial_state)
        return result

    def get_graph(self):
        """Return the compiled graph."""
        if self._app is None:
            self.build()
        return self._app
