#!/usr/bin/env python3
"""
supervisor.py — Executive-to-Specialist Orchestration Supervisor
Dispatches subtasks across specialized cognitive roles (Researcher, Planner, Coder, Critic, Evaluator).
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..kernel.event_bus import EventBus
from ..kernel.model_router import ModelRouter
from ..kernel.agent_loop import AgentKernelLoop
from .goal_engine import GoalEngine, Goal, SubTask, TaskStatus

class SpecialistRole:
    RESEARCHER = "researcher"
    PLANNER = "planner"
    CODER = "coder"
    CRITIC = "critic"
    EVALUATOR = "evaluator"

@dataclass
class SubagentContext:
    task_id: str
    role: str
    task_description: str
    system_prompt: str
    result: Optional[str] = None

class AgentSupervisor:
    ROLE_PROMPTS = {
        SpecialistRole.RESEARCHER: (
            "You are the Lead Research Specialist. Perform rigorous analysis, extract facts, "
            "and map dependencies. Output clear, verified findings."
        ),
        SpecialistRole.PLANNER: (
            "You are the Lead Systems Architect. Formulate technical architectures, state invariants, "
            "and step-by-step implementation blueprints."
        ),
        SpecialistRole.CODER: (
            "You are the Senior Implementation Engineer. Write clean, deterministic, robust Python code "
            "adhering to strict safety contracts and clean interfaces."
        ),
        SpecialistRole.CRITIC: (
            "You are the Red Team Critic. Identify edge cases, race conditions, security vulnerabilities, "
            "and boundary failure modes."
        ),
        SpecialistRole.EVALUATOR: (
            "You are the Verification & QA Gatekeeper. Execute test suites, verify proofs, and enforce "
            "earned-completion criteria before promotion."
        ),
    }

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        model_router: Optional[ModelRouter] = None,
        goal_engine: Optional[GoalEngine] = None
    ):
        self.event_bus = event_bus or EventBus()
        self.model_router = model_router or ModelRouter()
        self.goal_engine = goal_engine or GoalEngine()

    def execute_subtask(self, subtask: SubTask, context_info: Optional[str] = None) -> str:
        """Executes a single subtask with its specialized role prompt."""
        role = subtask.role
        sys_prompt = self.ROLE_PROMPTS.get(role, "You are a specialized Hermes autonomous agent.")
        prompt = f"Subtask: {subtask.title}\nDescription: {subtask.description}\n"
        if context_info:
            prompt += f"Context from previous steps:\n{context_info}\n"

        self.event_bus.emit("orchestration.subtask_start", {"task_id": subtask.id, "role": role})

        # Run kernel loop with specialist prompt
        loop = AgentKernelLoop(event_bus=self.event_bus, model_router=self.model_router)
        res = loop.run(task=prompt, system_prompt=sys_prompt)

        output = res.get("final_answer", "Completed")
        self.event_bus.emit("orchestration.subtask_end", {"task_id": subtask.id, "result": output})
        return output

    def execute_goal(self, goal: Goal) -> Dict[str, Any]:
        """Topologically executes all subtasks in the goal until completion."""
        self.event_bus.emit("orchestration.goal_start", {"goal_id": goal.goal_id, "title": goal.title})

        max_iterations = 20
        iteration = 0
        execution_trace = []

        while not self.goal_engine.is_goal_complete(goal) and iteration < max_iterations:
            iteration += 1
            ready_tasks = self.goal_engine.get_ready_tasks(goal)
            if not ready_tasks:
                break

            for task in ready_tasks:
                task.status = TaskStatus.IN_PROGRESS
                # Collect results from dependencies as context
                dep_contexts = []
                for dep_id in task.dependencies:
                    dep_task = goal.subtasks.get(dep_id)
                    if dep_task and dep_task.result:
                        dep_contexts.append(f"[{dep_task.title}]: {dep_task.result}")
                context_str = "\n".join(dep_contexts)

                # Execute with specialist agent
                result = self.execute_subtask(task, context_info=context_str)
                self.goal_engine.complete_task(goal, task.id, result=result)
                execution_trace.append({"task_id": task.id, "role": task.role, "result": result})

        is_done = self.goal_engine.is_goal_complete(goal)
        self.event_bus.emit("orchestration.goal_end", {"goal_id": goal.goal_id, "success": is_done})

        return {
            "goal_id": goal.goal_id,
            "title": goal.title,
            "success": is_done,
            "iterations": iteration,
            "trace": execution_trace
        }
