"""Harness Runtime Kernel — LangGraph node implementations.

Each node is a pure function: AgentState -> AgentState.
Nodes handle: init, plan, dispatch, monitor, adjust, evolve, complete.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from harnix.state import AgentState, AgentPhase


# ---------------------------------------------------------------------------
# Node: init
# ---------------------------------------------------------------------------

def init_node(state: AgentState) -> AgentState:
    """Initialize agent state — set phase to PLANNING, record start."""
    state["phase"] = AgentPhase.PLANNING
    state["iteration"] += 1
    state["messages"] = [f"[init] Agent {state['agent_id']} starting for: {state['task_description']}"]
    state["memory"] = [f"Task accepted: {state['task_description']} at {time.time()}"]
    return state


# ---------------------------------------------------------------------------
# Node: plan
# ---------------------------------------------------------------------------

def plan_node(state: AgentState) -> AgentState:
    """Create a plan from the task description.

    Rule-based decomposition (no LLM required).
    Produces ordered plan steps targeting plugins/methods.
    """
    state["phase"] = AgentPhase.PLANNING
    state["iteration"] += 1

    task = state["task_description"]
    plan_steps = _decompose_task(task)

    state["plan"] = plan_steps
    state["total_steps"] = len(plan_steps)
    state["current_step"] = 0

    state["messages"] = [f"[plan] Created plan with {len(plan_steps)} steps"]
    state["memory"] = [f"Plan created: {len(plan_steps)} steps for task"]

    return state


def _decompose_task(task: str) -> list[dict[str, Any]]:
    """Rule-based task decomposition into plan steps."""
    task_lower = task.lower()
    steps: list[dict[str, Any]] = []

    # Heuristic: file operations
    if any(k in task_lower for k in ("write file", "create file", "save file")):
        import re
        m = re.search(r'(?:file|to)\s+([\w./\\-]+\.\w+)', task, re.IGNORECASE)
        path = m.group(1) if m else "output.txt"
        content_m = re.search(r'(?:containing|with|saying)\s+([^\n]+)$', task, re.IGNORECASE)
        content = content_m.group(1).strip() if content_m else "Hermes output"
        steps.append({
            "id": f"step-{uuid.uuid4().hex[:6]}",
            "action": "write_file",
            "plugin": "filesystem_tool",
            "args": [path, content],
            "description": f"Write '{content}' to {path}",
        })

    # Heuristic: computation
    elif any(k in task_lower for k in ("compute", "calculate", "what is", "evaluate")):
        import re
        expr = re.sub(r'[^0-9+\-*/().%\s]', '', task)
        steps.append({
            "id": f"step-{uuid.uuid4().hex[:6]}",
            "action": "compute",
            "plugin": "python_tool",
            "args": [f"print({expr})"],
            "description": f"Compute: {expr}",
        })

    # Heuristic: web fetch
    elif any(k in task_lower for k in ("fetch", "http", "web", "get url")):
        import re
        url_m = re.search(r'https?://\S+', task)
        url = url_m.group(0) if url_m else "https://example.com"
        steps.append({
            "id": f"step-{uuid.uuid4().hex[:6]}",
            "action": "fetch",
            "plugin": "http_tool",
            "args": [url],
            "description": f"Fetch: {url}",
        })

    # Heuristic: memory / remember
    elif any(k in task_lower for k in ("remember", "store", "memorize")):
        fact = task.split("that", 1)[-1].strip() if "that" in task_lower else task
        steps.append({
            "id": f"step-{uuid.uuid4().hex[:6]}",
            "action": "remember",
            "plugin": "memory_curator",
            "args": [fact],
            "description": f"Remember: {fact}",
        })

    # Heuristic: search
    elif any(k in task_lower for k in ("search", "recall", "find")):
        query = task
        steps.append({
            "id": f"step-{uuid.uuid4().hex[:6]}",
            "action": "search",
            "plugin": "memory_curator",
            "args": [query],
            "description": f"Search for: {query}",
        })

    # Fallback: generic execution
    else:
        steps.append({
            "id": f"step-{uuid.uuid4().hex[:6]}",
            "action": "execute",
            "plugin": "python_tool",
            "args": [f"print({task!r})"],
            "description": f"Execute: {task}",
        })

    return steps


# ---------------------------------------------------------------------------
# Node: dispatch
# ---------------------------------------------------------------------------

def dispatch_node(state: AgentState) -> AgentState:
    """Execute the current plan step."""
    state["phase"] = AgentPhase.DISPATCHING
    state["iteration"] += 1

    plan = state["plan"]
    current_step_idx = state["current_step"]

    if current_step_idx >= len(plan):
        state["messages"] = ["[dispatch] No more steps to execute"]
        return state

    step = plan[current_step_idx]
    state["messages"] = [f"[dispatch] Executing step {current_step_idx + 1}/{len(plan)}: {step['description']}"]

    # Execute the step (simulated — real execution goes through kernel)
    result = _execute_step(step)

    state["step_outputs"] = [result]
    state["results"] = [{
        "step_id": step["id"],
        "action": step["action"],
        "result": result,
        "timestamp": time.time(),
    }]

    state["current_step"] += 1
    state["memory"] = [f"Step completed: {step['description']} -> {result}"]

    return state


def _execute_step(step: dict[str, Any]) -> Any:
    """Execute a single plan step. Returns result (deterministic, no LLM)."""
    action = step.get("action", "execute")

    if action == "write_file":
        path, content = step["args"][0], step["args"][1]
        try:
            with open(path, "w") as f:
                f.write(content)
            return f"Wrote {len(content)} chars to {path}"
        except Exception as e:
            return f"File write failed: {e}"

    elif action == "compute":
        expr = step["args"][0].replace("print(", "").rstrip(")")
        try:
            result = eval(expr, {"__builtins__": {}}, {})
            return f"Result: {result}"
        except Exception as e:
            return f"Compute failed: {e}"

    elif action == "fetch":
        url = step["args"][0]
        return f"Simulated fetch: {url}"

    elif action == "remember":
        fact = step["args"][0]
        return f"Stored: {fact}"

    elif action == "search":
        query = step["args"][0]
        return f"Simulated search for: {query}"

    else:
        return f"Executed: {step.get('description', action)}"


# ---------------------------------------------------------------------------
# Node: monitor
# ---------------------------------------------------------------------------

def monitor_node(state: AgentState) -> AgentState:
    """Check progress, detect stalls, update score."""
    state["phase"] = AgentPhase.MONITORING
    state["iteration"] += 1

    total = state["total_steps"]
    current = state["current_step"]

    # Score = fraction of plan completed
    new_score = current / total if total > 0 else 0.0
    old_score = state["score"]

    # Detect stall: no score improvement
    if abs(new_score - old_score) < 0.001:
        state["stall_count"] += 1
    else:
        state["stall_count"] = 0
        state["last_progress_iteration"] = state["iteration"]

    state["score"] = new_score

    # Determine if complete
    is_complete = current >= total
    if is_complete:
        state["status"] = "completed"
        state["phase"] = AgentPhase.COMPLETING

    state["messages"] = [
        f"[monitor] Progress: {current}/{total} steps, score={new_score:.2f}, stalls={state['stall_count']}"
    ]

    return state


# ---------------------------------------------------------------------------
# Node: adjust
# ---------------------------------------------------------------------------

def adjust_node(state: AgentState) -> AgentState:
    """Re-plan or change strategy when stalled."""
    state["phase"] = AgentPhase.ADJUSTING
    state["iteration"] += 1

    strategies = ["default", "explore_first", "decompose", "research_first"]
    current_strategy = state["strategy"]
    current_idx = strategies.index(current_strategy) if current_strategy in strategies else 0
    new_strategy = strategies[(current_idx + 1) % len(strategies)]

    state["strategy"] = new_strategy
    state["strategy_stack"] = state["strategy_stack"] + [new_strategy]
    state["stall_count"] = 0

    # Re-plan: add extra steps based on new strategy
    task = state["task_description"]
    additional_steps = _strategy_steps(new_strategy, task)

    if additional_steps:
        state["plan"] = state["plan"] + additional_steps
        state["total_steps"] = len(state["plan"])

    state["messages"] = [f"[adjust] Strategy changed to: {new_strategy}"]
    state["memory"] = [f"Strategy adjusted to {new_strategy} after stall"]

    return state


def _strategy_steps(strategy: str, task: str) -> list[dict[str, Any]]:
    """Generate additional plan steps based on strategy."""
    if strategy == "explore_first":
        return [{
            "id": f"step-{uuid.uuid4().hex[:6]}",
            "action": "search",
            "plugin": "memory_curator",
            "args": [f"context for: {task}"],
            "description": f"Explore context for: {task}",
        }]
    elif strategy == "decompose":
        return [{
            "id": f"step-{uuid.uuid4().hex[:6]}",
            "action": "execute",
            "plugin": "python_tool",
            "args": [f"print('Decomposing: {task}')"],
            "description": f"Decompose task: {task}",
        }]
    elif strategy == "research_first":
        return [{
            "id": f"step-{uuid.uuid4().hex[:6]}",
            "action": "fetch",
            "plugin": "http_tool",
            "args": ["https://example.com"],
            "description": f"Research: {task}",
        }]
    return []


# ---------------------------------------------------------------------------
# Node: evolve
# ---------------------------------------------------------------------------

def evolve_node(state: AgentState) -> AgentState:
    """Generate evolved approach when multiple stalls detected."""
    state["phase"] = AgentPhase.EVOLVING
    state["iteration"] += 1

    evolution = {
        "id": f"evo-{uuid.uuid4().hex[:6]}",
        "iteration": state["iteration"],
        "previous_strategy": state["strategy"],
        "new_strategy": f"evolved_{state['iteration']}",
        "timestamp": time.time(),
        "trigger": "max_stalls_reached",
    }
    state["evolution_history"] = state["evolution_history"] + [evolution]
    state["strategy"] = evolution["new_strategy"]
    state["stall_count"] = 0
    state["current_step"] = 0

    # Evolve the plan: try different decomposition
    task = state["task_description"]
    evolved_steps = [{
        "id": f"step-{uuid.uuid4().hex[:6]}",
        "action": "execute",
        "plugin": "python_tool",
        "args": [f"print('Evolved approach for: {task}')"],
        "description": f"Evolved: {task}",
    }]
    state["plan"] = evolved_steps
    state["total_steps"] = len(evolved_steps)

    state["messages"] = [f"[evolve] Strategy evolved to: {state['strategy']}"]
    state["memory"] = [f"Strategy evolved to {state['strategy']}"]

    return state


# ---------------------------------------------------------------------------
# Node: complete
# ---------------------------------------------------------------------------

def complete_node(state: AgentState) -> AgentState:
    """Finalize the run."""
    state["phase"] = AgentPhase.COMPLETED
    state["status"] = "completed"
    state["iteration"] += 1

    summary = (
        f"[complete] Run {state['run_id']} finished: "
        f"score={state['score']:.2f}, steps={state['current_step']}/{state['total_steps']}, "
        f"iterations={state['iteration']}, status={state['status']}"
    )
    state["messages"] = [summary]
    state["memory"] = [summary]

    return state


# ---------------------------------------------------------------------------
# Edge routing
# ---------------------------------------------------------------------------

def route_after_dispatch(state: AgentState) -> str:
    """Route after dispatch: always go to monitor."""
    return "monitor"


def route_after_monitor(state: AgentState) -> str:
    """Route after monitor based on progress and stalls."""
    # If complete
    if state["status"] == "completed" and state["current_step"] >= state["total_steps"]:
        return "complete"

    # If max stalls reached → evolve
    if state["stall_count"] >= state["max_stalls"]:
        return "evolve"

    # If stalled → adjust
    if state["stall_count"] >= 2:
        return "adjust"

    # If more steps remain → dispatch
    if state["current_step"] < state["total_steps"]:
        return "dispatch"

    # If no more steps → complete
    return "complete"


def route_after_adjust(state: AgentState) -> str:
    """Route after adjust: always go to dispatch."""
    return "dispatch"


def route_after_evolve(state: AgentState) -> str:
    """Route after evolve: always go to dispatch."""
    return "dispatch"


# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------

NODE_REGISTRY: dict[str, Any] = {
    "init": init_node,
    "plan": plan_node,
    "dispatch": dispatch_node,
    "monitor": monitor_node,
    "adjust": adjust_node,
    "evolve": evolve_node,
    "complete": complete_node,
}
