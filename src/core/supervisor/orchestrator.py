"""Multi-Agent Orchestration — LangGraph + DeepAgents patterns.

Coordinates multiple specialized agents in various topologies:
- Pipeline: A → B → C → D
- Debate: A ↔ B → Judge
- Divide-and-Conquer: Split → Parallel → Merge
- Assembly Line: Each agent does one step
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List


class Topology(str, Enum):
    PIPELINE = "pipeline"
    DEBATE = "debate"
    DIVIDE_AND_CONQUER = "divide_and_conquer"
    ASSEMBLY_LINE = "assembly_line"


class AgentRole(str, Enum):
    RESEARCHER = "researcher"
    CODER = "coder"
    TESTER = "tester"
    WRITER = "writer"
    REVIEWER = "reviewer"
    JUDGE = "judge"


@dataclass
class AgentMessage:
    """A message between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str = ""
    receiver: str = ""
    content: str = ""
    message_type: str = "info"  # info, critique, vote, result
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Agent:
    """An agent in the swarm."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: AgentRole = AgentRole.RESEARCHER
    name: str = ""
    callback: Callable | None = None
    state: Dict[str, Any] = field(default_factory=dict)


class MultiAgentOrchestrator:
    """Orchestrates multiple agents in various topologies."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._messages: List[AgentMessage] = []
        self._topology: Topology = Topology.PIPELINE

    def register_agent(self, agent: Agent) -> None:
        """Register an agent."""
        self._agents[agent.id] = agent

    def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def get_agents_by_role(self, role: AgentRole) -> List[Agent]:
        """Get all agents with a specific role."""
        return [a for a in self._agents.values() if a.role == role]

    # --- Pipeline ---

    def run_pipeline(
        self,
        initial_input: str,
        role_order: List[AgentRole],
    ) -> str:
        """Run agents in sequence, passing output to next."""
        result = initial_input

        for role in role_order:
            agents = self.get_agents_by_role(role)
            if not agents:
                continue

            agent = agents[0]
            if agent.callback:
                result = agent.callback(result, agent.state)
            else:
                result = f"[{role.value} processed]: {result}"

        return result

    # --- Debate ---

    def run_debate(
        self,
        topic: str,
        num_rounds: int = 3,
    ) -> Dict[str, Any]:
        """Run a debate between agents and a judge."""
        agents = list(self._agents.values())
        judge = self.get_agents_by_role(AgentRole.JUDGE)

        positions = {}
        for round_num in range(num_rounds):
            for agent in agents:
                if agent.role == AgentRole.JUDGE:
                    continue

                if agent.callback:
                    position = agent.callback(topic, agent.state)
                else:
                    position = f"[{agent.role.value} position on]: {topic}"

                positions[agent.id] = {
                    "role": agent.role.value,
                    "position": position,
                    "round": round_num,
                }

        # Judge decides
        winner = None
        if judge:
            judge_agent = judge[0]
            if judge_agent.callback:
                winner = judge_agent.callback(topic, positions)

        return {
            "topic": topic,
            "positions": positions,
            "winner": winner,
            "rounds": num_rounds,
        }

    # --- Divide and Conquer ---

    def run_divide_and_conquer(
        self,
        task: str,
        num_splits: int = 4,
    ) -> List[Any]:
        """Split task, process in parallel, merge results."""
        # Split
        splits = self._split_task(task, num_splits)

        # Process (parallel)
        results = []
        agents = [a for a in self._agents.values() if a.role != AgentRole.JUDGE]

        for i, split in enumerate(splits):
            agent = agents[i % len(agents)] if agents else None
            if agent and agent.callback:
                result = agent.callback(split, agent.state)
            else:
                result = f"[Processed]: {split}"
            results.append(result)

        return results

    def _split_task(self, task: str, num_splits: int) -> List[str]:
        """Split a task into sub-tasks."""
        words = task.split()
        chunk_size = max(1, len(words) // num_splits)
        splits = []
        for i in range(0, len(words), chunk_size):
            splits.append(" ".join(words[i:i + chunk_size]))
        return splits[:num_splits]

    # --- Assembly Line ---

    def run_assembly_line(
        self,
        input_data: str,
        steps: List[AgentRole],
    ) -> Dict[str, Any]:
        """Each agent does one step, passes to next."""
        result = input_data
        history = []

        for step in steps:
            agents = self.get_agents_by_role(step)
            if not agents:
                continue

            agent = agents[0]
            if agent.callback:
                result = agent.callback(result, agent.state)

            history.append({
                "step": step.value,
                "agent": agent.id,
                "result": result,
            })

        return {
            "final_result": result,
            "history": history,
            "steps_completed": len(history),
        }

    # --- Utility ---

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        roles = {}
        for agent in self._agents.values():
            r = agent.role.value
            roles[r] = roles.get(r, 0) + 1

        return {
            "total_agents": len(self._agents),
            "roles": roles,
            "topology": self._topology.value,
            "messages": len(self._messages),
        }
