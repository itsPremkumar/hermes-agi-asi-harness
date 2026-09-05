"""Harness Runtime Kernel — State definitions for LangGraph StateGraph.

Uses TypedDict for type-safe state with LangGraph.
All state is serializable (no callables, no objects without __dict__) for checkpointing.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentPhase:
    """Agent lifecycle phases."""
    INIT = "init"
    RESEARCHING = "researching"
    THINKING = "thinking"
    GOAL_SETTING = "goal_setting"
    PLANNING = "planning"
    DISPATCHING = "dispatching"
    EXECUTING = "executing"
    RLM = "rlm"
    MONITORING = "monitoring"
    ADJUSTING = "adjusting"
    VERIFYING = "verifying"
    EVOLVING = "evolving"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentState(TypedDict):
    """Full agent state for the LangGraph StateGraph.

    All fields are TypedDict annotations for LangGraph compatibility.
    Messages accumulate via Annotated[..., operator.add] reducer.
    """
    # Identity
    agent_id: str
    run_id: str
    task_description: str

    # Lifecycle
    phase: str  # current AgentPhase
    status: str  # running | completed | failed | paused
    iteration: int
    max_iterations: int

    # Cognitive: Deep Research & Deep Thinking
    research_dossier: dict[str, Any]
    thinking_summary: dict[str, Any]
    goal_contract: dict[str, Any]
    hermes_packet: dict[str, Any]

    # Planning
    plan: list[dict[str, Any]]  # list of plan steps
    current_step: int
    total_steps: int
    strategy: str

    # Execution
    results: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]
    step_outputs: Annotated[list[Any], operator.add]

    # Monitoring & Telemetry
    score: float
    stall_count: int
    max_stalls: int
    last_progress_iteration: int
    telemetry: list[dict[str, Any]]
    completion_proof: dict[str, Any]

    # Evolution
    evolution_history: Annotated[list[dict[str, Any]], operator.add]
    strategy_stack: list[str]

    # Memory / Context
    context: dict[str, Any]
    memory: Annotated[list[str], operator.add]

    # Messages (accumulated across nodes)
    messages: Annotated[list[str], operator.add]


def create_initial_state(task_description: str, agent_id: str = "", **kwargs: Any) -> AgentState:
    """Create an initial AgentState for a new run."""
    import uuid
    return AgentState(
        agent_id=agent_id or f"agent-{uuid.uuid4().hex[:8]}",
        run_id=f"run-{uuid.uuid4().hex[:8]}",
        task_description=task_description,
        phase=AgentPhase.INIT,
        status="running",
        iteration=0,
        max_iterations=kwargs.get("max_iterations", 20),
        research_dossier={},
        thinking_summary={},
        goal_contract={},
        hermes_packet={},
        plan=[],
        current_step=0,
        total_steps=0,
        strategy="default",
        results=[],
        errors=[],
        step_outputs=[],
        score=0.0,
        stall_count=0,
        max_stalls=kwargs.get("max_stalls", 5),
        last_progress_iteration=0,
        telemetry=[],
        completion_proof={},
        evolution_history=[],
        strategy_stack=["default"],
        context=kwargs.get("context", {}),
        memory=[],
        messages=[],
    )
