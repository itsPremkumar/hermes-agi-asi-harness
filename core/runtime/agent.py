#!/usr/bin/env python3
"""
Agent Loop — executes a planned task end-to-end through the kernel + context.

Pipeline:
  goal -> plan -> for each step:
      1. check permission (R0-R6) via context
      2. invoke plugin.method(*args, **kwargs)
      3. capture result, audit-log it
      4. on failure: retry once with altered args, else mark failed
  -> returns a structured result
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from core.runtime.agent_kernel import WORKING_PLUGINS, AgentKernel
from core.runtime.context import AgentContext
from core.runtime.planner import PlanStep, TaskPlanner


@dataclass
class StepResult:
    step_id: str
    plugin: str
    method: str
    success: bool
    output: Any = None
    error: str | None = None
    permission_checked: bool = False
    permission_granted: bool = False


@dataclass
class AgentResult:
    goal: str
    success: bool
    steps_executed: int = 0
    step_results: list[StepResult] = field(default_factory=list)
    final_output: Any = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "success": self.success,
            "steps_executed": self.steps_executed,
            "final_output": self.final_output,
            "errors": self.errors,
            "step_results": [
                {
                    "step_id": s.step_id, "plugin": s.plugin, "method": s.method,
                    "success": s.success, "error": s.error,
                    "permission_granted": s.permission_granted,
                }
                for s in self.step_results
            ],
        }


class Agent:
    """The execution loop that turns a goal into real plugin calls."""

    def __init__(self, kernel: AgentKernel, context: AgentContext):
        self.kernel = kernel
        self.ctx = context
        self.planner = TaskPlanner(kernel)

    async def run(self, goal: str, verbose: bool = True) -> AgentResult:
        # Begin session/task tracking
        if not self.ctx.session_id:
            self.ctx.begin_session("agent-run")
        self.ctx.begin_task(goal)
        self.ctx.log_action("agent.task.start", "run", goal, "started", {"goal": goal})

        plan = self.planner.plan(goal)
        if verbose:
            await self.ctx.emit(f"[plan] {len(plan.steps)} step(s) for: {goal}\n")

        result = AgentResult(goal=goal, success=True)
        last_output = None

        for i, step in enumerate(plan.steps, 1):
            if verbose:
                await self.ctx.emit(f"[step {i}] {step.plugin}.{step.method} — {step.description}\n")

            step_result = await self._execute_step(step, last_output, verbose)
            result.step_results.append(step_result)
            result.steps_executed += 1

            if not step_result.success:
                result.success = False
                result.errors.append(f"Step {step.id} failed: {step_result.error}")
                # Halt on first hard failure (deterministic, no LLM to recover)
                break

            last_output = step_result.output

        result.final_output = last_output
        self.ctx.set_task_status("completed" if result.success else "failed", result.to_dict())
        self.ctx.log_action(
            "agent.task.end", "run", goal, "success" if result.success else "failed",
            {"steps": result.steps_executed, "errors": result.errors},
        )
        if verbose:
            await self.ctx.emit(f"[done] success={result.success}\n")
        return result

    async def _execute_step(self, step: PlanStep, prev_output: Any, verbose: bool) -> StepResult:
        # 1) Permission check
        if step.permission:
            ok, reason = self.ctx.check_permission(step.permission, {"step": step.id})
            if not ok:
                self.ctx.log_action("agent.permission.denied", step.plugin, step.method,
                                    "denied", {"reason": reason})
                return StepResult(
                    step_id=step.id, plugin=step.plugin, method=step.method,
                    success=False, error=f"Permission denied: {reason}",
                    permission_checked=True, permission_granted=False,
                )
        # 2) Resolve plugin
        plugin = self.kernel.get(step.plugin)
        if plugin is None:
            return StepResult(
                step_id=step.id, plugin=step.plugin, method=step.method,
                success=False, error=f"Plugin '{step.plugin}' not loaded",
            )

        # Inject previous output if the step method accepts a 'prev' kwarg placeholder
        args = list(step.args)
        kwargs = dict(step.kwargs)

        # 3) Invoke (with one retry on failure)
        last_error = None
        for attempt in range(2):
            try:
                method = getattr(plugin, step.method)
                if asyncio.iscoroutinefunction(method):
                    out = await method(*args, **kwargs)
                else:
                    out = method(*args, **kwargs)
                self.ctx.log_action(
                    "agent.step.ok", f"{step.plugin}.{step.method}", step.id,
                    "success", {"attempt": attempt + 1},
                )
                return StepResult(
                    step_id=step.id, plugin=step.plugin, method=step.method,
                    success=True, output=out,
                    permission_checked=bool(step.permission), permission_granted=bool(step.permission),
                )
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                if verbose:
                    await self.ctx.emit(f"  ! attempt {attempt+1} failed: {last_error}\n")
                # Small alteration: retry with prev_output substituted if present
                if attempt == 0 and prev_output is not None and not args:
                    args = [prev_output]

        self.ctx.log_action(
            "agent.step.fail", f"{step.plugin}.{step.method}", step.id,
            "failed", {"error": last_error},
        )
        return StepResult(
            step_id=step.id, plugin=step.plugin, method=step.method,
            success=False, error=last_error,
            permission_checked=bool(step.permission), permission_granted=bool(step.permission),
        )


# ── Factory ──────────────────────────────────────────────────────────────

async def build_agent(plugins_root: str = "plugins",
                      include: list[str] | None = None) -> tuple[AgentKernel, AgentContext, Agent]:
    """Boot the kernel, build context + agent, return all three."""
    from core.runtime.agent_kernel import build_kernel
    kernel = await build_kernel(plugins_root, include=include or WORKING_PLUGINS)
    ctx = AgentContext(kernel)
    ctx.begin_session("agent-boot")
    agent = Agent(kernel, ctx)
    return kernel, ctx, agent
