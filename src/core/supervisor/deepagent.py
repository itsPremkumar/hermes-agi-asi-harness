"""DeepAgents Cognitive Core — Inner monologue, planning, sub-agent spawning, VFS.

Provides the cognitive intelligence for each supervisor node:
- Inner monologue (private reasoning before acting)
- Planning tool (multi-step plan generation)
- Sub-agent spawning (recursive delegation)
- Virtual filesystem (persistent memory)
- Context management (compaction, retrieval)
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Inner monologue
# ---------------------------------------------------------------------------

class MonologueStage(str, Enum):
    """Stages of inner monologue."""
    OBSERVE = "observe"
    REASON = "reason"
    PLAN = "plan"
    ACT = "act"
    REFLECT = "reflect"


@dataclass
class MonologueStep:
    """A single step in inner monologue."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    stage: MonologueStage = MonologueStage.OBSERVE
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    private: bool = True  # Not visible to outer system


@dataclass
class InnerMonologue:
    """Private reasoning trace for an agent."""
    steps: List[MonologueStep] = field(default_factory=list)
    current_stage: MonologueStage = MonologueStage.OBSERVE

    def observe(self, observation: str) -> None:
        """Record an observation."""
        self.steps.append(MonologueStep(stage=MonologueStage.OBSERVE, content=observation))
        self.current_stage = MonologueStage.OBSERVE

    def reason(self, reasoning: str) -> None:
        """Record reasoning."""
        self.steps.append(MonologueStep(stage=MonologueStage.REASON, content=reasoning))
        self.current_stage = MonologueStage.REASON

    def plan(self, plan: str) -> None:
        """Record a plan."""
        self.steps.append(MonologueStep(stage=MonologueStage.PLAN, content=plan))
        self.current_stage = MonologueStage.PLAN

    def act(self, action: str) -> None:
        """Record an action."""
        self.steps.append(MonologueStep(stage=MonologueStage.ACT, content=action))
        self.current_stage = MonologueStage.ACT

    def reflect(self, reflection: str) -> None:
        """Record a reflection."""
        self.steps.append(MonologueStep(stage=MonologueStage.REFLECT, content=reflection))
        self.current_stage = MonologueStage.REFLECT

    def get_trace(self) -> List[Dict[str, Any]]:
        """Get the full monologue trace."""
        return [
            {"stage": step.stage.value, "content": step.content, "timestamp": step.timestamp}
            for step in self.steps
        ]

    def get_summary(self) -> str:
        """Get a summary of the monologue."""
        return "\n".join(f"[{step.stage.value}] {step.content}" for step in self.steps)


# ---------------------------------------------------------------------------
# Virtual File System (Memory)
# ---------------------------------------------------------------------------

@dataclass
class VFSFile:
    """A file in the virtual filesystem."""
    path: str
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class VirtualFileSystem:
    """Virtual filesystem for persistent agent memory."""

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or Path.home() / ".hermes" / "supervisor" / "vfs"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._files: Dict[str, VFSFile] = {}

    def write(self, path: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> VFSFile:
        """Write a file."""
        file = VFSFile(
            path=path,
            content=content,
            metadata=metadata or {},
            updated_at=time.time(),
        )
        self._files[path] = file
        return file

    def read(self, path: str) -> Optional[VFSFile]:
        """Read a file."""
        return self._files.get(path)

    def append(self, path: str, content: str) -> VFSFile:
        """Append to a file."""
        existing = self._files.get(path)
        if existing:
            existing.content += content
            existing.updated_at = time.time()
        else:
            existing = self.write(path, content)
        return existing

    def delete(self, path: str) -> bool:
        """Delete a file."""
        if path in self._files:
            del self._files[path]
            return True
        return False

    def list_files(self, prefix: str = "") -> List[str]:
        """List files, optionally filtered by prefix."""
        return [p for p in self._files if p.startswith(prefix)]

    def search(self, query: str) -> List[VFSFile]:
        """Search file contents."""
        results = []
        query_lower = query.lower()
        for file in self._files.values():
            if query_lower in file.content.lower():
                results.append(file)
        return results

    def save(self) -> None:
        """Persist VFS to disk."""
        data = {
            path: {"content": file.content, "metadata": file.metadata}
            for path, file in self._files.items()
        }
        path = self._data_dir / "vfs.json"
        path.write_text(json.dumps(data, indent=2))

    def load(self) -> None:
        """Load VFS from disk."""
        path = self._data_dir / "vfs.json"
        if not path.exists():
            return
        data = json.loads(path.read_text())
        for path, file_data in data.items():
            self._files[path] = VFSFile(
                path=path,
                content=file_data["content"],
                metadata=file_data.get("metadata", {}),
            )


# ---------------------------------------------------------------------------
# Planning tool
# ---------------------------------------------------------------------------

@dataclass
class PlanStep:
    """A single plan step."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    status: str = "pending"
    result: str = ""
    subplan: Optional['Plan'] = None


@dataclass
class Plan:
    """A multi-step plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    status: str = "draft"

    def add_step(self, title: str, description: str = "") -> PlanStep:
        """Add a step."""
        step = PlanStep(title=title, description=description)
        self.steps.append(step)
        return step

    def complete_step(self, step_id: str, result: str) -> None:
        """Mark a step as complete."""
        for step in self.steps:
            if step.id == step_id:
                step.status = "completed"
                step.result = result
                break

    def next_pending_step(self) -> Optional[PlanStep]:
        """Get the next pending step."""
        for step in self.steps:
            if step.status == "pending":
                return step
        return None

    def is_complete(self) -> bool:
        """Check if all steps are complete."""
        return all(step.status == "completed" for step in self.steps)


class PlanningTool:
    """Tool for generating and managing plans."""

    def create_plan(self, goal: str, context: Dict[str, Any]) -> Plan:
        """Create a plan for a goal."""
        plan = Plan(title=goal)

        # In live operation, this uses the LLM to decompose
        # For now, create a simple plan
        plan.add_step("Analyze", f"Analyze the requirements for: {goal}")
        plan.add_step("Execute", "Execute the main work")
        plan.add_step("Verify", "Verify the result")

        return plan

    def update_plan(self, plan: Plan, step_id: str, result: str) -> Plan:
        """Update a plan with step result."""
        plan.complete_step(step_id, result)
        return plan

    def revise_plan(self, plan: Plan, feedback: str) -> Plan:
        """Revise a plan based on feedback."""
        # In live operation, this uses the LLM to revise
        plan.status = "revised"
        return plan


# ---------------------------------------------------------------------------
# Sub-agent spawning
# ---------------------------------------------------------------------------

@dataclass
class SubAgentTask:
    """A task for a sub-agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: str = ""
    parent_id: str = ""


class SubAgentSpawner:
    """Spawns recursive sub-agents."""

    def __init__(self):
        self._spawned: Dict[str, SubAgentTask] = {}

    def spawn(self, description: str, context: Dict[str, Any], parent_id: str = "") -> SubAgentTask:
        """Spawn a sub-agent."""
        task = SubAgentTask(
            description=description,
            context=context,
            parent_id=parent_id,
        )
        self._spawned[task.id] = task
        return task

    def get_status(self, task_id: str) -> Optional[str]:
        """Get sub-agent status."""
        task = self._spawned.get(task_id)
        return task.status if task else None

    def complete(self, task_id: str, result: str) -> None:
        """Complete a sub-agent task."""
        task = self._spawned.get(task_id)
        if task:
            task.status = "completed"
            task.result = result

    def get_result(self, task_id: str) -> Optional[str]:
        """Get sub-agent result."""
        task = self._spawned.get(task_id)
        return task.result if task else None


# ---------------------------------------------------------------------------
# DeepAgent (cognitive core)
# ---------------------------------------------------------------------------

class DeepAgent:
    """Deep agent with inner monologue, planning, sub-agent spawning, VFS."""

    def __init__(
        self,
        name: str = "agent",
        role: str = "general",
        data_dir: Optional[Path] = None,
    ):
        self._id = str(uuid.uuid4())[:8]
        self._name = name
        self._role = role

        # Cognitive components
        self._monologue = InnerMonologue()
        self._vfs = VirtualFileSystem(data_dir)
        self._planner = PlanningTool()
        self._spawner = SubAgentSpawner()

        # State
        self._current_plan: Optional[Plan] = None
        self._context: Dict[str, Any] = {}
        self._results: List[Dict[str, Any]] = []

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def role(self) -> str:
        return self._role

    @property
    def monologue(self) -> InnerMonologue:
        return self._monologue

    @property
    def vfs(self) -> VirtualFileSystem:
        return self._vfs

    @property
    def planner(self) -> PlanningTool:
        return self._planner

    @property
    def spawner(self) -> SubAgentSpawner:
        return self._spawner

    # --- Cognitive loop ---

    def think(self, observation: str) -> str:
        """Run inner monologue (private reasoning)."""
        self._monologue.observe(observation)
        self._monologue.reason(f"Analyzing: {observation}")
        self._monologue.plan("Determine best approach")
        return "Reasoning complete"

    def plan(self, goal: str, context: Dict[str, Any]) -> Plan:
        """Create a plan for the goal."""
        self._monologue.observe(f"Planning for: {goal}")
        self._context = context
        self._current_plan = self._planner.create_plan(goal, context)
        self._monologue.plan(f"Created plan with {len(self._current_plan.steps)} steps")
        return self._current_plan

    def execute_plan_step(self, step: PlanStep) -> str:
        """Execute a single plan step."""
        self._monologue.act(f"Executing: {step.title}")

        # In live operation, this would use tools to execute
        result = f"Completed: {step.title}"

        self._monologue.reflect(f"Step result: {result}")

        # Update plan if it exists
        if self._current_plan:
            self._planner.update_plan(self._current_plan, step.id, result)

        return result

    def spawn_subagent(self, description: str, context: Dict[str, Any]) -> str:
        """Spawn a sub-agent for a sub-task."""
        self._monologue.reason(f"Spawning sub-agent for: {description}")
        task = self._spawner.spawn(description, context, parent_id=self._id)
        return task.id

    def reflect(self) -> str:
        """Reflect on progress."""
        summary = self._monologue.get_summary()
        self._monologue.reflect(f"Progress reflection:\n{summary}")
        return summary

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "id": self._id,
            "name": self._name,
            "role": self._role,
            "monologue_steps": len(self._monologue.steps),
            "plan_steps": len(self._current_plan.steps) if self._current_plan else 0,
            "spawned_subagents": len(self._spawner._spawned),
        }
