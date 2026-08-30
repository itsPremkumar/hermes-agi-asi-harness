"""Lifecycle nodes for the LangGraph agent graph.

Each node takes an AgentState and returns a partial dict of updates.
The LangGraph runtime merges these into the state via the reducers.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from .state import AgentState

logger = logging.getLogger(__name__)

# ── Tool Registry ─────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, dict[str, Any]] = {}


def register_tool(name: str, func, description: str = ""):
    """Register a callable tool."""
    TOOL_REGISTRY[name] = {"func": func, "description": description}


def get_tool(name: str):
    """Look up a tool by name."""
    return TOOL_REGISTRY.get(name)


def list_tools() -> list[str]:
    return list(TOOL_REGISTRY.keys())


def _dispatch_tool(tool_name: str, input_data: dict[str, Any]) -> dict[str, Any]:
    """Execute a registered tool and return a structured result."""
    tool = get_tool(tool_name)
    if tool is None:
        return {"ok": False, "output": "", "error": f"Unknown tool: {tool_name}"}
    try:
        result = tool["func"](input_data)
        return {"ok": True, "output": str(result), "error": ""}
    except Exception as e:
        return {"ok": False, "output": "", "error": str(e)}


# ── Built-in tools ────────────────────────────────────────────────────

def _tool_echo(input_data: dict[str, Any]) -> str:
    return input_data.get("text", "")


def _tool_uppercase(input_data: dict[str, Any]) -> str:
    return input_data.get("text", "").upper()


def _tool_python_exec(input_data: dict[str, Any]) -> str:
    """Execute simple Python code (sandboxed: only arithmetic / string ops)."""
    code = input_data.get("code", "")
    allowed = re.compile(r"^[\d\s\+\-\*\/\(\)\.\,\'\"\]\[\]\:\=\<\>\!\%]+$")
    if allowed.match(code):
        try:
            result = eval(code, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Error: {e}"
    return "Code blocked: only arithmetic expressions allowed"


def _tool_file_write(input_data: dict[str, Any]) -> str:
    """Simulated file write — returns the path."""
    path = input_data.get("path", "output.txt")
    content = input_data.get("content", "")
    return f"Wrote {len(content)} chars to {path}"


def _tool_search(input_data: dict[str, Any]) -> str:
    query = input_data.get("query", "")
    return f"Search results for '{query}': [result_1, result_2]"


# Register built-in tools
register_tool("echo", _tool_echo, "Echo back the input text")
register_tool("uppercase", _tool_uppercase, "Convert text to uppercase")
register_tool("python_exec", _tool_python_exec, "Execute simple Python arithmetic")
register_tool("file_write", _tool_file_write, "Write content to a file")
register_tool("search", _tool_search, "Search for information")


# ── Node: plan ────────────────────────────────────────────────────────

def plan_node(state: AgentState) -> dict[str, Any]:
    """Analyze the goal and produce an execution plan."""
    goal = state["goal"]
    logger.info("[plan] goal=%s", goal)

    plan = _heuristic_plan(goal)

    return {
        "plan": plan,
        "current_step": 0,
        "step_count": state["step_count"] + 1,
        "messages": [
            {
                "role": "assistant",
                "content": f"Planned {len(plan)} steps for goal: {goal}",
            }
        ],
    }


def _heuristic_plan(goal: str) -> list[dict[str, Any]]:
    """Generate a plan from the goal using keyword heuristics."""
    goal_lower = goal.lower()
    plan = []

    if "write" in goal_lower and ("file" in goal_lower or ".txt" in goal_lower):
        path = "output.txt"
        content = goal
        if "containing" in goal_lower:
            parts = goal.split("containing", 1)
            if len(parts) > 1:
                content = parts[1].strip()
                words = parts[0].strip().split()
                for w in words:
                    if w.endswith((".txt", ".py", ".md")):
                        path = w
                        break
        plan.append({
            "tool": "file_write",
            "input": {"path": path, "content": content},
            "description": f"Write content to {path}",
        })
        plan.append({
            "tool": "echo",
            "input": {"text": f"Completed: wrote to {path}"},
            "description": "Acknowledge completion",
        })
    elif any(w in goal_lower for w in ["compute", "calculate", "math", "what is", "eval"]):
        plan.append({
            "tool": "python_exec",
            "input": {"code": goal},
            "description": "Execute computation",
        })
    elif "search" in goal_lower or "find" in goal_lower:
        plan.append({
            "tool": "search",
            "input": {"query": goal},
            "description": "Search for information",
        })
    elif "uppercase" in goal_lower or "capital" in goal_lower:
        plan.append({
            "tool": "uppercase",
            "input": {"text": goal},
            "description": "Convert to uppercase",
        })
    else:
        plan.append({
            "tool": "echo",
            "input": {"text": f"Processed: {goal}"},
            "description": "Default echo action",
        })

    return plan


# ── Node: act ─────────────────────────────────────────────────────────

def act_node(state: AgentState) -> dict[str, Any]:
    """Execute the current plan step (dispatch to tool).
    
    If the previous step was verified (verification_passed=True), advance
    to the next step first. If verification failed, retry the current step.
    """
    plan = state["plan"]
    step = state["current_step"]
    verified = state.get("verification_passed", False)

    # Advance step if previous was verified and we have more steps
    if verified and step < len(plan) - 1:
        step = step + 1

    if step >= len(plan):
        return {
            "status": "completed",
            "final_answer": "All steps executed",
            "step_count": state["step_count"] + 1,
        }

    current = plan[step]
    tool_name = current.get("tool", "echo")
    tool_input = current.get("input", {})

    logger.info("[act] step=%d tool=%s", step, tool_name)

    result = _dispatch_tool(tool_name, tool_input)

    tool_result = {
        "tool": tool_name,
        "input": tool_input,
        "output": result.get("output", ""),
        "ok": result.get("ok", False),
        "error": result.get("error", ""),
    }

    return {
        "current_step": step,
        "tool_results": [tool_result],
        "verification_passed": False,  # reset for next verify
        "messages": [
            {
                "role": "assistant",
                "content": f"Executed {tool_name}: {result.get('output', '')[:200]}",
            }
        ],
        "step_count": state["step_count"] + 1,
    }


def route_after_act(state: AgentState) -> str:
    """Decide where to go after act: observe (if step succeeded) or reflect (if failed)."""
    results = state.get("tool_results", [])
    if results and not results[-1].get("ok", False):
        return "reflect"
    return "observe"


# ── Node: observe ─────────────────────────────────────────────────────

def observe_node(state: AgentState) -> dict[str, Any]:
    """Record an observation about the tool output."""
    results = state.get("tool_results", [])
    if not results:
        return {"observations": ["No tool results to observe"]}

    last = results[-1]
    obs = f"Tool '{last['tool']}' returned: {last.get('output', '')[:500]}"
    if last.get("error"):
        obs += f" (error: {last['error']})"

    return {
        "observations": [obs],
        "messages": [{"role": "user", "content": obs}],
        "step_count": state["step_count"] + 1,
    }


# ── Node: reflect ─────────────────────────────────────────────────────

def reflect_node(state: AgentState) -> dict[str, Any]:
    """Reflect on failures and propose corrections."""
    results = state.get("tool_results", [])
    plan = state.get("plan", [])
    step = state.get("current_step", 0)
    retries = state.get("retries", 0)

    reflection = ""
    if results and not results[-1].get("ok", False):
        err = results[-1].get("error", "unknown error")
        tool = results[-1].get("tool", "unknown")
        reflection = f"Tool '{tool}' failed: {err}. Will retry with adjusted input."
        # Auto-correct: if the tool doesn't exist, replace with echo
        if "Unknown tool" in err and step < len(plan):
            plan[step]["tool"] = "echo"
            plan[step]["input"] = {"text": f"Fallback for: {plan[step].get('description', '')}"}
    else:
        reflection = "Step completed successfully. Proceeding."

    return {
        "reflections": [reflection],
        "plan": plan,
        "retries": retries + 1,
        "messages": [{"role": "assistant", "content": reflection}],
        "step_count": state["step_count"] + 1,
    }


# ── Node: verify ──────────────────────────────────────────────────────

def verify_node(state: AgentState) -> dict[str, Any]:
    """Verify if the current step succeeded and whether all steps are done."""
    results = state.get("tool_results", [])
    step = state.get("current_step", 0)
    plan = state.get("plan", [])

    details: dict[str, Any] = {"checks": [], "errors": []}

    # Check 1: did the last tool succeed?
    last_ok = results[-1].get("ok", False) if results else False
    details["checks"].append({"name": "tool_success", "passed": last_ok})

    # Check 2: is there output?
    has_output = bool(results and results[-1].get("output", ""))
    details["checks"].append({"name": "has_output", "passed": has_output})

    passed = all(c["passed"] for c in details["checks"])

    # Check 3: all steps done? (for status, not for passed)
    all_steps = step >= len(plan) - 1 if plan else True
    details["checks"].append({"name": "all_steps_done", "passed": all_steps})

    # Set status based on verification result
    status = "running"
    final_answer = ""
    if passed and all_steps:
        status = "completed"
        outputs = [r.get("output", "") for r in results if r.get("output")]
        final_answer = "; ".join(outputs) if outputs else "Goal achieved"
    elif passed:
        status = "running"  # more steps to go
    elif state.get("retries", 0) >= 3:
        status = "failed"
        final_answer = "Verification failed after max retries"

    return {
        "verification_passed": passed,
        "verification_details": details,
        "status": status,
        "final_answer": final_answer,
        "step_count": state["step_count"] + 1,
        "messages": [
            {
                "role": "assistant",
                "content": f"Verification {'PASSED' if passed else 'FAILED'}: {details}",
            }
        ],
    }


def route_after_verify(state: AgentState) -> str:
    """Route after verification:
    - passed AND all steps done → END
    - passed AND more steps → act (advance happens in act_node)
    - failed AND retries left → reflect
    - failed AND no retries → END (fail)
    """
    if state["verification_passed"]:
        next_step = state["current_step"] + 1
        if next_step >= len(state.get("plan", [])):
            return "__end__"
        return "act"
    # Verification failed — retry if we haven't exceeded max retries
    retries = state.get("retries", 0)
    if retries < 3:
        return "reflect"
    return "__end__"
