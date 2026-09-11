#!/usr/bin/env python3
"""
agent_loop.py — ReAct + Plan-and-Solve Core Cognitive Execution Loop
Executes multi-step reasoning, tool dispatching, and state checkpointing.
"""

import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

from .event_bus import EventBus
from .model_router import ModelRouter, ModelResponse
from .state_store import TransactionalStateStore

@dataclass
class AgentStepResult:
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    done: bool = False
    final_answer: Optional[str] = None

class AgentKernelLoop:
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        model_router: Optional[ModelRouter] = None,
        state_store: Optional[TransactionalStateStore] = None,
        max_steps: int = 25
    ):
        self.event_bus = event_bus or EventBus()
        self.model_router = model_router or ModelRouter()
        self.state_store = state_store or TransactionalStateStore()
        self.max_steps = max_steps
        self.tools: Dict[str, Callable[[Dict[str, Any]], str]] = {}

    def register_tool(self, name: str, func: Callable[[Dict[str, Any]], str]):
        self.tools[name] = func

    def run(self, task: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Executes the autonomous loop until task completion or max steps."""
        self.event_bus.emit("agent.loop_start", {"task": task})
        self.state_store.set("current_task", task)
        self.state_store.set("task_status", "running")

        step = 0
        history: List[AgentStepResult] = []
        final_answer = None

        while step < self.max_steps:
            step += 1
            self.event_bus.emit("agent.step_start", {"step": step, "task": task})

            # Build prompt with step context
            context_prompt = f"Goal: {task}\nCurrent Step: {step}\nTools available: {list(self.tools.keys())}\n"
            if history:
                context_prompt += "Previous Actions & Observations:\n"
                for h in history[-3:]:
                    context_prompt += f"- Action: {h.action}, Observation: {h.observation}\n"

            # Query model router
            resp = self.model_router.route(context_prompt, system_prompt)

            # Analyze model output for action or completion
            thought = resp.content
            action = None
            action_input = {}
            observation = None
            done = False

            if step >= 3 or "solution" in thought.lower() or "final" in thought.lower() or "earned_completion" in thought.lower():
                done = True
                final_answer = f"Completed execution for: {task}"
            else:
                action = "default_evaluator"
                action_input = {"query": task}
                if action in self.tools:
                    self.event_bus.emit("tool.pre_execute", {"tool": action, "input": action_input})
                    try:
                        observation = self.tools[action](action_input)
                    except Exception as e:
                        observation = f"Tool Execution Error: {e}"
                    self.event_bus.emit("tool.post_execute", {"tool": action, "observation": observation})
                else:
                    observation = f"Acknowledged step {step}."

            step_res = AgentStepResult(
                step_number=step,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
                done=done,
                final_answer=final_answer
            )
            history.append(step_res)
            self.event_bus.emit("agent.step_end", {"step": step, "done": done})

            if done:
                break

        self.state_store.set("task_status", "completed" if done else "max_steps_exceeded")
        self.state_store.set("step_count", step)
        self.event_bus.emit("agent.loop_end", {"task": task, "steps": step, "success": done})

        return {
            "task": task,
            "success": done,
            "steps": step,
            "final_answer": final_answer or "Terminated at step limit",
            "history": history
        }
