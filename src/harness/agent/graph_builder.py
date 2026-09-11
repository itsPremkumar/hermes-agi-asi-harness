"""Build the LangGraph agent lifecycle graph.

Two variants:
- build_agent_graph(): linear pipeline with conditional retry loop
- build_cyclic_agent_graph(): full cycle with observe → reflect → verify loop

Both return a compiled LangGraph graph ready for invoke/stream.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .lifecycle_nodes import (
    act_node,
    observe_node,
    plan_node,
    reflect_node,
    route_after_act,
    route_after_verify,
    verify_node,
)
from .state import AgentState

logger = logging.getLogger(__name__)


def build_agent_graph(
    *,
    name: str = "hermes_agent_lifecycle",
    max_steps: int = 25,
    checkpointer: Any | None = None,
) -> Any:
    """Build the standard agent lifecycle graph.

    Topology:
        START → plan → act → observe → verify → END
                     ↑    ↓          │
                     │  reflect      │
                     │    ↓          │
                     └────┴──────────┘ (retry loop via conditional edges)

    Args:
        name: Graph name for logging/debugging.
        max_steps: Maximum execution steps before forced termination.
        checkpointer: Optional LangGraph checkpointer (MemorySaver if None).

    Returns:
        Compiled LangGraph StateGraph.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────
    builder.add_node("plan", plan_node)
    builder.add_node("act", act_node)
    builder.add_node("observe", observe_node)
    builder.add_node("reflect", reflect_node)
    builder.add_node("verify", verify_node)

    # ── Edges ──────────────────────────────────────────────────────────
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "act")

    # After act: go to observe (success) or reflect (failure)
    builder.add_conditional_edges(
        "act",
        route_after_act,
        {
            "observe": "observe",
            "reflect": "reflect",
        },
    )

    # After observe: go to verify
    builder.add_edge("observe", "verify")

    # After reflect: go back to act (retry)
    builder.add_edge("reflect", "act")

    # After verify: END (done), act (more steps), or reflect (retry)
    builder.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "__end__": END,
            "act": "act",
            "reflect": "reflect",
        },
    )

    graph = builder.compile(checkpointer=checkpointer)
    logger.info("Built agent graph: %s (nodes=%s)", name, list(builder.nodes.keys()))
    return graph


def build_cyclic_agent_graph(
    *,
    name: str = "hermes_cyclic_agent",
    max_steps: int = 25,
    checkpointer: Any | None = None,
) -> Any:
    """Build a cyclic agent graph with full observe → reflect → verify loop.

    This variant always goes through observe → reflect → verify after each act,
    providing more thorough self-monitoring at the cost of extra steps.

    Topology:
        START → plan → act → observe → reflect → verify → END
                     ↑                        │
                     └────────────────────────┘ (retry loop)

    Args:
        name: Graph name.
        max_steps: Maximum execution steps.
        checkpointer: Optional checkpointer.

    Returns:
        Compiled LangGraph StateGraph.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(AgentState)

    builder.add_node("plan", plan_node)
    builder.add_node("act", act_node)
    builder.add_node("observe", observe_node)
    builder.add_node("reflect", reflect_node)
    builder.add_node("verify", verify_node)

    builder.add_edge(START, "plan")
    builder.add_edge("plan", "act")
    builder.add_edge("act", "observe")
    builder.add_edge("observe", "reflect")
    builder.add_edge("reflect", "verify")

    builder.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "__end__": END,
            "act": "act",
            "reflect": "reflect",
        },
    )

    graph = builder.compile(checkpointer=checkpointer)
    logger.info("Built cyclic agent graph: %s", name)
    return graph


def run_agent(
    goal: str,
    *,
    graph: Any | None = None,
    max_steps: int = 25,
    run_id: str = "",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience function: build graph, run goal, return final state.

    Args:
        goal: The task/goal to execute.
        graph: Pre-built graph (builds default if None).
        max_steps: Maximum steps.
        run_id: Optional run identifier.
        config: Optional LangGraph config (e.g., {"configurable": {"thread_id": "..."}}).

    Returns:
        Final AgentState as a dict.
    """
    from .state import initial_state

    if graph is None:
        graph = build_agent_graph(max_steps=max_steps)

    state = initial_state(goal=goal, max_steps=max_steps, run_id=run_id)

    if config is None:
        config = {"configurable": {"thread_id": state["run_id"]}}

    result = graph.invoke(state, config=config)
    return dict(result)
