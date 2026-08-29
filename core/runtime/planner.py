#!/usr/bin/env python3
"""
Rule-based Task Planner.

Turns a task string into an ordered list of step specs. Each step targets a
plugin by name and records the method + args + required permission + fallback.

No LLM is used — pure keyword / capability matching against the loaded kernel.

Step spec format:
    {
        "id": str,
        "plugin": str,          # plugin name in kernel
        "method": str,          # method name on the Plugin instance
        "args": list,
        "kwargs": dict,
        "permission": str,      # permission action to check (or None)
        "description": str,
    }
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.runtime.agent_kernel import AgentKernel


@dataclass
class PlanStep:
    id: str
    plugin: str
    method: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    permission: Optional[str] = None
    description: str = ""


@dataclass
class Plan:
    goal: str
    steps: List[PlanStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [
                {
                    "id": s.id, "plugin": s.plugin, "method": s.method,
                    "args": s.args, "kwargs": s.kwargs,
                    "permission": s.permission, "description": s.description,
                }
                for s in self.steps
            ],
        }


class TaskPlanner:
    """Maps task strings to plugin step plans."""

    def __init__(self, kernel: AgentKernel):
        self.kernel = kernel

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _extract_quoted(text: str) -> List[str]:
        return re.findall(r'"([^"]*)"', text)

    @staticmethod
    def _extract_path(text: str) -> Optional[str]:
        # Match common path patterns (relative or absolute-ish)
        m = re.search(r'(?:file|path|to)\s+([\w./\\-]+\.\w+)', text, re.IGNORECASE)
        if m:
            return m.group(1)
        # bare filename
        m = re.search(r'\b([\w./\\-]+\.\w+)', text)
        return m.group(1) if m else None

    # ── Planners per intent ──────────────────────────────────────────────

    def plan(self, goal: str) -> Plan:
        goal_l = goal.lower()
        steps: List[PlanStep] = []

        # 1) Write/Create a file
        if any(k in goal_l for k in ("write file", "create file", "save file", "write a file", "create a file")):
            path = self._extract_path(goal) or "output.txt"
            quoted = self._extract_quoted(goal)
            if quoted:
                content = quoted[-1]
            else:
                # Try "containing X" / "with content X" / "with X" / "saying X"
                m = re.search(r'(?:containing|with content|with|saying|content)\s+([^\n]+)$', goal, re.IGNORECASE)
                if m:
                    content = m.group(1).strip().strip('"').strip("'")
                else:
                    content = "Hermes agent output"
            steps.append(PlanStep(
                id="write", plugin="filesystem_tool", method="write",
                args=[path, content], permission="write_file",
                description=f"Write '{content}' to {path}",
            ))
            return Plan(goal, steps)

        # 2) Compute / math expression
        if any(k in goal_l for k in ("compute", "calculate", "what is", "evaluate", "math")):
            quoted = self._extract_quoted(goal)
            expr = quoted[0] if quoted else re.sub(r'[^0-9+\-*/()%.\s]', '', goal)
            steps.append(PlanStep(
                id="compute", plugin="python_tool", method="run",
                args=[f"result = {expr}; print(result)"], permission="run_python",
                description=f"Evaluate expression: {expr}",
            ))
            return Plan(goal, steps)

        # 3) Optimize / minimize / search optimum
        if any(k in goal_l for k in ("optimize", "minimize", "maximize", "find optimum", "best value")):
            steps.append(PlanStep(
                id="optimize", plugin="swarm_intelligence", method="initialize",
                args=[], kwargs={"dimensions": 2, "num_particles": 15, "bounds": (-5, 5)},
                permission="run_python",
                description="Initialize swarm for optimization",
            ))
            steps.append(PlanStep(
                id="run_opt", plugin="swarm_intelligence", method="optimize",
                args=[lambda x: -sum(v * v for v in x)],
                kwargs={"iterations": 30, "bounds": (-5, 5)},
                permission="run_python",
                description="Run particle swarm optimization",
            ))
            return Plan(goal, steps)

        # 4) Summarize / analyze text
        if any(k in goal_l for k in ("summarize", "analyze", "extract keywords", "summary")):
            quoted = self._extract_quoted(goal)
            text = quoted[0] if quoted else goal
            steps.append(PlanStep(
                id="summarize", plugin="document_intel", method="summarize",
                args=[text], kwargs={"sentences": 2}, permission=None,
                description="Summarize provided text",
            ))
            return Plan(goal, steps)

        # 5) Remember / store knowledge
        if any(k in goal_l for k in ("remember", "store", "memorize", "learn that", "note that")):
            quoted = self._extract_quoted(goal)
            fact = quoted[0] if quoted else goal.split("that", 1)[-1].strip()
            steps.append(PlanStep(
                id="remember", plugin="memory_curator", method="add_memory",
                args=[fact, "knowledge", 0.8, ["user-fact"]],
                permission=None,
                description=f"Store fact in memory: {fact}",
            ))
            return Plan(goal, steps)

        # 6) Search / recall from memory
        if any(k in goal_l for k in ("search memory", "recall", "what do you know about", "retrieve")):
            query = self._extract_quoted(goal)
            q = query[0] if query else goal
            steps.append(PlanStep(
                id="search", plugin="memory_curator", method="search",
                args=[q], kwargs={"top_k": 3}, permission=None,
                description=f"Search memory for: {q}",
            ))
            return Plan(goal, steps)

        # 7) Debate / decide between options
        if any(k in goal_l for k in ("debate", "decide", "argue", "pros and cons")):
            topic = self._extract_quoted(goal)
            t = topic[0] if topic else goal
            steps.append(PlanStep(
                id="debate", plugin="debate_engine", method="set_topic",
                args=[t], permission=None,
                description=f"Set debate topic: {t}",
            ))
            steps.append(PlanStep(
                id="debate_run", plugin="debate_engine", method="_run_with_perspectives",
                args=[t], permission=None,
                description="Run a pro/con debate",
            ))
            return Plan(goal, steps)

        # 8) Run a shell command
        if any(k in goal_l for k in ("run command", "execute", "shell", "run the command")):
            quoted = self._extract_quoted(goal)
            cmd = quoted[0] if quoted else goal.split("command", 1)[-1].strip()
            steps.append(PlanStep(
                id="shell", plugin="shell_tool", method="run",
                args=[cmd], permission="run_shell",
                description=f"Run shell command: {cmd}",
            ))
            return Plan(goal, steps)

        # 9) Web fetch / HTTP
        if any(k in goal_l for k in ("fetch", "http", "web", "download", "get url")):
            quoted = self._extract_quoted(goal)
            url = quoted[0] if quoted else re.search(r'https?://\S+', goal)
            url = url if isinstance(url, str) else (url.group(0) if url else "https://example.com")
            steps.append(PlanStep(
                id="fetch", plugin="http_tool", method="get",
                args=[url], permission="fetch_url",
                description=f"Fetch URL: {url}",
            ))
            return Plan(goal, steps)

        # 10) Fallback: generic python echo
        steps.append(PlanStep(
            id="echo", plugin="python_tool", method="run",
            args=[f"print({goal!r})"], permission="run_python",
            description="Echo the goal (no specific handler matched)",
        ))
        return Plan(goal, steps)
