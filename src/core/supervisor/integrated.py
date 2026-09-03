"""Integration Layer — Connects LangGraph nodes to DeepAgents.

Each LangGraph node dispatches a DeepAgent for cognitive work.
LangGraph handles: branching, looping, checkpointing.
DeepAgents handle: reasoning, planning, memory, sub-agent spawning.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.supervisor.langgraph_skeleton import (
    LangGraphSkeleton, SupervisorState, NodeName, EdgeCondition,
    build_default_graph,
)
from core.supervisor.deepagent import DeepAgent, Plan, PlanStep
from core.supervisor.world_model import WorldModel, EntityType


# ---------------------------------------------------------------------------
# Node handlers (each dispatches a DeepAgent)
# ---------------------------------------------------------------------------

def plan_node(state: SupervisorState) -> SupervisorState:
    """Plan node — DeepAgent analyzes goal and creates plan."""
    agent = DeepAgent(name="planner", role="planning")

    # Inner monologue
    agent.monologue.observe(f"Goal: {state.goal_description}")
    agent.monologue.reason("Analyzing goal requirements")

    # Create plan
    plan = agent.plan(state.goal_description, state.context)

    # Store in state
    state.plan = {
        "id": plan.id,
        "title": plan.title,
        "steps": [
            {"id": step.id, "title": step.title, "status": step.status}
            for step in plan.steps
        ],
        "total_steps": len(plan.steps),
    }
    state.total_steps = len(plan.steps)
    state.current_step = 0

    # Store in VFS
    agent.vfs.write("/plan/current.json", str(plan.__dict__))

    # Reflect
    agent.monologue.reflect(f"Plan created with {len(plan.steps)} steps")

    return state


def dispatch_node(state: SupervisorState) -> SupervisorState:
    """Dispatch node — DeepAgent executes current plan step."""
    agent = DeepAgent(name="executor", role="execution")

    # Get current step
    steps = state.plan.get("steps", [])
    if state.current_step < len(steps):
        step = steps[state.current_step]

        # Create a plan for the agent if not exists
        if not agent._current_plan:
            agent._current_plan = Plan(title="dispatch")
            agent._current_plan.steps = [
                PlanStep(id=s["id"], title=s["title"]) for s in steps
            ]

        # Inner monologue
        agent.monologue.observe(f"Executing step: {step['title']}")
        agent.monologue.reason("Determining best execution approach")

        # Execute
        plan_step = PlanStep(id=step["id"], title=step["title"])
        result = agent.execute_plan_step(plan_step)

        # Update state
        step["status"] = "completed"
        step["result"] = result
        state.results.append({"step": step["title"], "result": result})
        state.current_step += 1

        # Store in VFS
        agent.vfs.append("/results/log.txt", f"Completed: {step['title']}\n")

    return state


def monitor_node(state: SupervisorState) -> SupervisorState:
    """Monitor node — DeepAgent checks progress and detects stalls."""
    agent = DeepAgent(name="monitor", role="monitoring")

    # Inner monologue
    agent.monologue.observe(f"Progress: {state.current_step}/{state.total_steps}")
    agent.monologue.reason("Checking for stalls or issues")

    # Check progress
    if state.total_steps > 0:
        progress = state.current_step / state.total_steps
    else:
        progress = 0.0

    # Detect stall
    if state.current_step == 0 and state.iterations > 3:
        state.stall_count += 1
        agent.monologue.reason("Stall detected: no progress in 3+ iterations")
    elif state.current_step > 0:
        state.stall_count = 0

    # Update score
    state.score = progress

    agent.monologue.reflect(f"Score: {state.score:.2f}, Stalls: {state.stall_count}")

    return state


def adjust_node(state: SupervisorState) -> SupervisorState:
    """Adjust node — DeepAgent re-plans or changes strategy."""
    agent = DeepAgent(name="adjuster", role="adjustment")

    # Inner monologue
    agent.monologue.observe("Stall detected, need to adjust")
    agent.monologue.reason("Analyzing failure and generating new approach")

    # Change strategy
    strategies = ["default", "explore_first", "decompose", "research_first"]
    current_idx = strategies.index(state.strategy) if state.strategy in strategies else 0
    state.strategy = strategies[(current_idx + 1) % len(strategies)]

    # Reset stall count
    state.stall_count = 0

    # Re-plan
    plan = agent.plan(state.goal_description, state.context)
    state.plan = {
        "id": plan.id,
        "title": plan.title,
        "steps": [
            {"id": step.id, "title": step.title, "status": step.status}
            for step in plan.steps
        ],
        "total_steps": len(plan.steps),
    }
    state.current_step = 0

    agent.monologue.reflect(f"Strategy changed to: {state.strategy}")

    return state


def evolve_node(state: SupervisorState) -> SupervisorState:
    """Evolve node — DeepAgent generates evolved approach."""
    agent = DeepAgent(name="evolver", role="evolution")

    # Inner monologue
    agent.monologue.observe("Multiple stalls detected, evolving approach")
    agent.monologue.reason("Generating novel strategy variation")

    # Evolution: combine previous strategies
    evolution = {
        "id": str(uuid.uuid4())[:8],
        "iteration": state.iterations,
        "previous_strategy": state.strategy,
        "new_strategy": f"evolved_{state.iterations}",
        "timestamp": time.time(),
    }
    state.evolution_history.append(evolution)
    state.strategy = evolution["new_strategy"]

    # Reset
    state.stall_count = 0
    state.current_step = 0

    # Spawn sub-agent for research
    subagent_id = agent.spawn_subagent(
        f"Research alternative approaches for: {state.goal_description}",
        state.context,
    )

    agent.monologue.reflect(f"Evolved to strategy: {state.strategy}")

    return state


# ---------------------------------------------------------------------------
# Integrated Supervisor (LangGraph + DeepAgents)
# ---------------------------------------------------------------------------

class IntegratedSupervisor:
    """Integrated supervisor combining LangGraph skeleton + DeepAgents core."""

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or Path.home() / ".hermes" / "supervisor"
        self._graph = build_default_graph(
            plan_handler=plan_node,
            dispatch_handler=dispatch_node,
            monitor_handler=monitor_node,
            adjust_handler=adjust_node,
            evolve_handler=evolve_node,
        )
        self._world_model = WorldModel(self._data_dir)

    def run(self, goal: str, context: Optional[Dict[str, Any]] = None) -> SupervisorState:
        """Run the integrated supervisor."""
        # Add to world model
        self._world_model.add_entity(goal, EntityType.GOAL)

        # Run graph
        state = self._graph.run(goal, context)

        # Update world model
        self._world_model.update_entity(
            list(self._world_model._entities.keys())[0],
            properties={"status": state.goal_status, "score": state.score},
        )

        return state

    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get execution log."""
        return self._graph.get_execution_log()

    def get_world_model(self) -> WorldModel:
        """Get world model."""
        return self._world_model
