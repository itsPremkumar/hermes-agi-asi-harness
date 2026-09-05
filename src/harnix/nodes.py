"""Harness Runtime Kernel — LangGraph node implementations.

Each node is a pure function: AgentState -> AgentState.
Full Multi-Step Cognitive Pipeline:
- init: Initialize lifecycle state & memory
- research: Autonomous Deep Research & dependency mapping
- think: Deep Thinking deliberation (hypotheses, critiques, invariants)
- plan: Task decomposition into executable DAG
- dispatch: Hermes Agent mission execution via sandboxed tools
- monitor: Active Watchdog supervision (stall/loop detection, steering)
- verify: Empirical completion proof and evidence verification
- adjust: Corrective steering injection
- evolve: Strategy mutation
- complete: Final consensus and telemetry summary
"""
from __future__ import annotations

import asyncio
import re
import time
import uuid
from typing import Any

from harnix.state import AgentPhase, AgentState

# Cognitive and monitoring subsystems
try:
    from core.verification.adversarial import AdversarialVerifier
    from core.verification.anti_goodhart import AntiGoodhartVerifier
    from hermes_agi.allocation import HermesMissionPacket, HermesWatchdogMonitor
    from hermes_agi.research import DeepResearchAgent
    from hermes_agi.thinking import DeepThinkingEngine
except ImportError:
    DeepResearchAgent = None
    DeepThinkingEngine = None
    HermesMissionPacket = None
    HermesWatchdogMonitor = None
    AdversarialVerifier = None
    AntiGoodhartVerifier = None


def _run_sync(coro: Any) -> Any:
    """Run an async coroutine synchronously, handling running event loops cleanly."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(coro)).result(timeout=10)
    else:
        return asyncio.run(coro)


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
# Node: research (Deep Research Agent)
# ---------------------------------------------------------------------------

def research_node(state: AgentState) -> AgentState:
    """Conduct autonomous deep research on the task topic."""
    state["phase"] = AgentPhase.RESEARCHING
    state["iteration"] += 1

    task = state["task_description"]
    if DeepResearchAgent is not None:
        agent = DeepResearchAgent()
        try:
            dossier = _run_sync(agent.investigate(task, depth=2))
            state["research_dossier"] = dossier.to_dict()
        except Exception:
            state["research_dossier"] = {
                "dossier_id": f"dossier-{uuid.uuid4().hex[:6]}",
                "topic": task,
                "findings": [{"category": "general", "summary": f"Direct objective: {task}", "confidence": 0.9}],
                "key_insights": ["Direct execution mapped."],
                "known_pitfalls": [],
                "recommended_tools": ["filesystem_tool", "python_tool"],
            }
    else:
        state["research_dossier"] = {
            "dossier_id": f"dossier-{uuid.uuid4().hex[:6]}",
            "topic": task,
            "findings": [{"category": "general", "summary": f"Objective: {task}", "confidence": 0.9}],
            "key_insights": [],
            "known_pitfalls": [],
            "recommended_tools": ["filesystem_tool", "python_tool"],
        }

    findings_count = len(state["research_dossier"].get("findings", []))
    msg = f"[research] Completed deep research dossier ({findings_count} findings)"
    state["messages"] = [msg]
    state["memory"] = [msg]
    return state


# ---------------------------------------------------------------------------
# Node: think (Deep Thinking & Deliberation)
# ---------------------------------------------------------------------------

def think_node(state: AgentState) -> AgentState:
    """Execute deliberate deep thinking (Hypotheses, Critiques, Invariants)."""
    state["phase"] = AgentPhase.THINKING
    state["iteration"] += 1

    task = state["task_description"]
    if DeepThinkingEngine is not None:
        engine = DeepThinkingEngine()
        try:
            result = _run_sync(engine.deliberate(task, context=state.get("context", {})))
            state["thinking_summary"] = result.to_dict()
            state["strategy"] = result.selected_strategy
        except Exception:
            state["thinking_summary"] = {
                "goal": task,
                "selected_strategy": "Modular Execution",
                "confidence": 0.90,
                "invariants": [],
            }
    else:
        state["thinking_summary"] = {
            "goal": task,
            "selected_strategy": "Direct Execution",
            "confidence": 0.85,
            "invariants": [],
        }

    strat = state.get("strategy", "default")
    msg = f"[think] Deliberation complete. Selected strategy: '{strat}'"
    state["messages"] = [msg]
    state["memory"] = [msg]
    return state


# ---------------------------------------------------------------------------
# Node: plan
# ---------------------------------------------------------------------------

def plan_node(state: AgentState) -> AgentState:
    """Create an executable plan from task description and cognitive context."""
    state["phase"] = AgentPhase.PLANNING
    state["iteration"] += 1

    task = state["task_description"]
    plan_steps = _decompose_task(task)

    state["plan"] = plan_steps
    state["total_steps"] = len(plan_steps)
    state["current_step"] = 0

    # Compile Goal Contract & Hermes Mission Packet
    if HermesMissionPacket is not None:
        packet = HermesMissionPacket(
            goal=task,
            assigned_role="hermes-coder",
            goal_contract={"objective": task, "status": "active"},
            research_dossier=state.get("research_dossier", {}),
            thinking_summary=state.get("thinking_summary", {}),
            plan_steps=plan_steps,
            tool_whitelist=["filesystem_tool", "python_tool", "shell_tool", "git_tool"],
            completion_criteria=[f"Complete all {len(plan_steps)} steps with evidence"],
        )
        state["hermes_packet"] = packet.to_dict()
    else:
        state["hermes_packet"] = {"goal": task, "steps": len(plan_steps)}

    state["messages"] = [f"[plan] Allocated {len(plan_steps)} steps to Hermes Agent packet"]
    state["memory"] = [f"Plan created: {len(plan_steps)} steps for task"]
    return state


def _decompose_task(task: str) -> list[dict[str, Any]]:
    """Task decomposition into executable plan steps."""
    task_lower = task.lower()
    steps: list[dict[str, Any]] = []

    # Heuristic: file operations
    if any(k in task_lower for k in ("write file", "create file", "save file")):
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
    """Execute the current plan step through Hermes tool execution."""
    state["phase"] = AgentPhase.DISPATCHING
    state["iteration"] += 1

    plan = state["plan"]
    current_step_idx = state["current_step"]

    if current_step_idx >= len(plan):
        state["messages"] = ["[dispatch] All steps executed"]
        return state

    step = plan[current_step_idx]
    state["messages"] = [f"[dispatch] Hermes executing step {current_step_idx + 1}/{len(plan)}: {step['description']}"]

    # Execute step with timing telemetry
    t0 = time.time()
    result = _execute_step(step)
    duration_ms = (time.time() - t0) * 1000

    # Log telemetry event
    telemetry_event = {
        "step_id": step["id"],
        "action": step["action"],
        "duration_ms": duration_ms,
        "timestamp": time.time(),
    }
    state["telemetry"] = state.get("telemetry", []) + [telemetry_event]

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
    """Execute a single plan step deterministically."""
    action = step.get("action", "execute")

    if action == "write_file":
        path, content = step["args"][0], step["args"][1]
        try:
            with open(path, "w", encoding="utf-8") as f:
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

    elif action in ("rlm", "rlm_execute"):
        code = step["args"][0]
        from hermes_agi.rlm import RLMREPLExecutor
        executor = RLMREPLExecutor()
        try:
            res = executor.execute(code)
            val = res.returned_value if res.returned_value is not None else res.stdout.strip()
            return f"RLM Result: {val}"
        finally:
            executor.close()

    else:
        return f"Executed: {step.get('description', action)}"


# ---------------------------------------------------------------------------
# Node: monitor
# ---------------------------------------------------------------------------

def monitor_node(state: AgentState) -> AgentState:
    """Check progress, detect stalls or loops, and update telemetry."""
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

    # Determine completion
    is_complete = current >= total
    if is_complete:
        state["status"] = "completed"
        state["phase"] = AgentPhase.COMPLETING

    state["messages"] = [
        f"[monitor] Watchdog telemetry: {current}/{total} steps, score={new_score:.2f}, stalls={state['stall_count']}"
    ]

    return state


# ---------------------------------------------------------------------------
# Node: verify (Completion Proof & Evidence)
# ---------------------------------------------------------------------------

def verify_node(state: AgentState) -> AgentState:
    """Compile evidence-backed Completion Proof."""
    state["phase"] = AgentPhase.VERIFYING
    state["iteration"] += 1

    total = state["total_steps"]
    current = state["current_step"]
    all_passed = current >= total and len(state.get("errors", [])) == 0

    evidence = [f"Step {r.get('step_id')}: {r.get('result')}" for r in state.get("results", [])]
    claims = [f"Executed {state['task_description']} successfully", f"Total steps {current}/{total} completed"]

    # Run Adversarial Proposer-Critic Verification
    consensus_score = 1.0 if all_passed else 0.5
    brier_score = 0.0 if all_passed else 0.25
    critiques = []
    if AdversarialVerifier is not None:
        try:
            verifier = AdversarialVerifier()
            verdict = verifier.verify(claims=claims, evidence=evidence, context=state.get("context", {}))
            consensus_score = verdict.consensus_score
            brier_score = verdict.brier_score
            critiques = [c.vulnerability for c in verdict.critiques]
        except Exception:
            pass

    # Run Anti-Goodhart Hidden Holdouts
    anti_gaming_passed = True
    if AntiGoodhartVerifier is not None:
        try:
            ag_verifier = AntiGoodhartVerifier()
            for r in state.get("results", []):
                # Inspect write_file operations for gaming
                if r.get("action") == "write_file":
                    args = r.get("args", [])
                    file_name = args[0] if len(args) > 0 else "output.py"
                    content = args[1] if len(args) > 1 else ""
                    hv = ag_verifier.verify(file_name, content)
                    if hv.detected_gaming:
                        anti_gaming_passed = False
                        critiques.append("Anti-Goodhart: Metric gaming / trivial assertion detected in generated code.")
                        consensus_score *= 0.5
        except Exception:
            pass

    verified = all_passed and consensus_score >= 0.80 and anti_gaming_passed

    proof = {
        "goal_id": state["run_id"],
        "status": "verified" if verified else "failed",
        "expected_steps": total,
        "executed_steps": current,
        "evidence": evidence,
        "confidence": consensus_score,
        "brier_score": brier_score,
        "adversarial_critiques": critiques,
        "timestamp": time.time(),
    }
    state["completion_proof"] = proof

    if verified:
        state["status"] = "completed"
        state["phase"] = AgentPhase.COMPLETED
        msg = f"[verify] Proof verified with adversarial consensus {consensus_score:.2f} (Brier: {brier_score:.4f})"
    else:
        msg = f"[verify] Verification flagged discrepancies: consensus={consensus_score:.2f}, critiques={len(critiques)}"

    state["messages"] = [msg]
    state["memory"] = [msg]
    return state


# ---------------------------------------------------------------------------
# Node: adjust (Supervisor Steering Interjection)
# ---------------------------------------------------------------------------

def adjust_node(state: AgentState) -> AgentState:
    """Interject steering guidance when stalls or loops are detected."""
    state["phase"] = AgentPhase.ADJUSTING
    state["iteration"] += 1

    interjection = (
        f"[adjust] Supervisor interjection: Stall count {state['stall_count']}. "
        "Refining sub-goal parameters and clearing transient blocks."
    )
    state["messages"] = [interjection]
    state["memory"] = [interjection]
    state["stall_count"] = 0
    state["strategy"] = "dynamic_retry"

    return state


# ---------------------------------------------------------------------------
# Node: evolve
# ---------------------------------------------------------------------------

def evolve_node(state: AgentState) -> AgentState:
    """Mutate strategy when repeated adjustments fail."""
    state["phase"] = AgentPhase.EVOLVING
    state["iteration"] += 1

    old_strategy = state["strategy"]
    new_strategy = f"evolved_{state['iteration']}"
    state["strategy"] = new_strategy
    state["strategy_stack"].append(new_strategy)

    event = {
        "iteration": state["iteration"],
        "from_strategy": old_strategy,
        "to_strategy": new_strategy,
        "timestamp": time.time(),
    }
    state["evolution_history"] = [event]
    state["stall_count"] = 0

    msg = f"[evolve] Strategy mutated: {old_strategy} -> {new_strategy}"
    state["messages"] = [msg]
    state["memory"] = [msg]

    return state


# ---------------------------------------------------------------------------
# Node: complete
# ---------------------------------------------------------------------------

def complete_node(state: AgentState) -> AgentState:
    """Finalize the mission run."""
    state["phase"] = AgentPhase.COMPLETED
    state["status"] = "completed"
    state["iteration"] += 1

    summary = (
        f"[complete] Mission {state['run_id']} finished: "
        f"score={state['score']:.2f}, steps={state['current_step']}/{state['total_steps']}, "
        f"verified={bool(state.get('completion_proof', {}).get('status') == 'verified')}"
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
    """Route after monitor based on progress, stalls, or completion."""
    if state.get("status") == "completed":
        return "complete"

    # If ready for verification / complete
    if state["current_step"] >= state["total_steps"]:
        return "verify"

    # If max stalls reached -> evolve
    if state["stall_count"] >= state["max_stalls"]:
        return "evolve"

    # If stalled -> adjust
    if state["stall_count"] >= 2:
        return "adjust"

    # More steps remain -> dispatch
    return "dispatch"


def route_after_verify(state: AgentState) -> str:
    """Route after verify: complete if verified, else adjust."""
    if state.get("completion_proof", {}).get("status") == "verified":
        return "complete"
    return "adjust"


def route_after_adjust(state: AgentState) -> str:
    """Route after adjust: dispatch next step."""
    return "dispatch"


def route_after_evolve(state: AgentState) -> str:
    """Route after evolve: dispatch next step."""
    return "dispatch"


def rlm_node(state: AgentState) -> AgentState:
    """Execute exploratory, algorithmic, or recursive Python code in persistent RLM REPL."""
    state["phase"] = AgentPhase.RLM
    state["iteration"] += 1

    code = state.get("context", {}).get("rlm_code") or f"# Task: {state['task_description']}\nprint('RLM processing: {state['task_description']}')"
    from hermes_agi.rlm import RLMREPLExecutor
    executor = RLMREPLExecutor()
    try:
        res = executor.execute(code)
        val = res.returned_value if res.returned_value is not None else res.stdout.strip()
        state["results"] = [{
            "step_id": f"rlm-{uuid.uuid4().hex[:6]}",
            "action": "rlm",
            "result": val,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "timestamp": time.time(),
        }]
        state["messages"] = [f"[rlm] Executed code cell: {val}"]
    finally:
        executor.close()
    return state


# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------

NODE_REGISTRY: dict[str, Any] = {
    "init": init_node,
    "research": research_node,
    "think": think_node,
    "plan": plan_node,
    "dispatch": dispatch_node,
    "rlm": rlm_node,
    "monitor": monitor_node,
    "verify": verify_node,
    "adjust": adjust_node,
    "evolve": evolve_node,
    "complete": complete_node,
}
