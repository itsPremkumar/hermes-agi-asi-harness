"""Typed state definition for the LangGraph agent lifecycle graph."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State that flows through the agent lifecycle graph.

    Messages are accumulated via add_messages reducer (append-only).
    All other fields are overwritten by node return values.
    """

    # Identity
    run_id: str

    # Input
    goal: str

    # Planning
    plan: list[dict[str, Any]]            # [{tool, input, description}]
    current_step: int

    # Execution
    messages: Annotated[list[dict[str, Any]], add_messages]  # chat trace
    tool_results: list[dict[str, Any]]    # [{tool, input, output}]

    # Observation
    observations: list[str]               # human-readable observations

    # Reflection
    reflections: list[str]                # self-critique / improvement notes

    # Verification
    verification_passed: bool
    verification_details: dict[str, Any]   # {checks: [], errors: []}

    # Loop control
    step_count: int
    max_steps: int
    retries: int                          # retry counter for failed steps

    # Outcome
    status: str                           # running | completed | failed
    final_answer: str


def validate_state(state: AgentState) -> list[str]:
    """Validate state invariants. Returns list of error strings (empty=OK)."""
    errors = []
    if not state.get("goal"):
        errors.append("goal must be non-empty")
    if state.get("step_count", 0) < 0:
        errors.append("step_count must be >= 0")
    if state.get("max_steps", 25) < 1:
        errors.append("max_steps must be >= 1")
    if state.get("current_step", 0) < 0:
        errors.append("current_step must be >= 0")
    if state.get("retries", 0) < 0:
        errors.append("retries must be >= 0")
    status = state.get("status")
    if status and status not in ("", "running", "completed", "failed"):
        errors.append(f"invalid status: {status}")
    return errors


def initial_state(goal: str, max_steps: int = 25, run_id: str = "") -> AgentState:
    """Create a fresh AgentState for a new run."""
    import uuid
    return AgentState(
        run_id=run_id or str(uuid.uuid4())[:8],
        goal=goal,
        plan=[],
        current_step=0,
        messages=[],
        tool_results=[],
        observations=[],
        reflections=[],
        verification_passed=False,
        verification_details={},
        step_count=0,
        max_steps=max_steps,
        retries=0,
        status="running",
        final_answer="",
    )
