"""
Agent Team Coordinator — Apodex 1.1 Pattern
============================================
Dynamic parallel sub-agent coordination with shared task state.
Coordinator decomposes task -> dispatches specialized sub-agents -> shared state -> continuous results.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Specialized sub-agent roles."""
    RESEARCHER = "researcher"           # Information gathering, evidence collection
    ARCHITECT = "architect"             # System design, architecture decisions
    CODER = "coder"                     # Implementation, refactoring, tests
    VERIFIER = "verifier"               # Adversarial verification, testing
    DOCUMENTER = "documenter"           # Documentation, comments, README
    REVIEWER = "reviewer"               # Code review, security audit
    PLANNER = "planner"                 # Task decomposition, scheduling
    SYNTHESIZER = "synthesizer"         # Result integration, final deliverable


class AgentStatus(str, Enum):
    """Sub-agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class SubTask:
    """A unit of work assigned to a sub-agent."""
    id: str
    role: AgentRole
    title: str
    description: str
    required_capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # SubTask IDs
    status: AgentStatus = AgentStatus.PENDING
    assigned_agent_id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SharedTaskState:
    """
    Shared task state — Apodex AgentOS pattern.
    All sub-agents read/write to this shared state.
    """
    task_id: str
    original_goal: str
    decomposed_subtasks: dict[str, SubTask] = field(default_factory=dict)
    evidence_store: dict[str, Any] = field(default_factory=dict)  # key -> evidence
    decisions: list[dict] = field(default_factory=list)  # {timestamp, decision, rationale, agent}
    artifacts: dict[str, bytes] = field(default_factory=dict)  # path -> content
    verification_results: dict[str, Any] = field(default_factory=dict)
    current_phase: str = "decomposition"
    metadata: dict = field(default_factory=dict)

    def add_evidence(self, key: str, evidence: Any, agent_id: str) -> None:
        self.evidence_store[key] = {
            "value": evidence,
            "source_agent": agent_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_evidence(self, key: str) -> Optional[Any]:
        return self.evidence_store.get(key, {}).get("value")

    def record_decision(self, decision: str, rationale: str, agent_id: str) -> None:
        self.decisions.append({
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "rationale": rationale,
            "agent": agent_id,
        })


@dataclass
class AgentTeamResult:
    """Final result from agent team execution."""
    task_id: str
    status: str  # "completed" | "failed" | "partial"
    shared_state: SharedTaskState
    sub_task_results: dict[str, Any] = field(default_factory=dict)
    final_deliverable: Optional[Any] = None
    verification_report: Optional[Any] = None
    duration_seconds: float = 0.0


class SubAgent:
    """
    A specialized sub-agent with a specific role.
    In production, this wraps a Harness or LLM call with role-specific prompting.
    """

    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        executor: Callable[[SubTask, SharedTaskState], Any],
        capabilities: Optional[list[str]] = None,
    ):
        self.agent_id = agent_id
        self.role = role
        self.executor = executor
        self.capabilities = capabilities or []
        self.status = AgentStatus.PENDING
        self.current_task: Optional[SubTask] = None

    async def execute(self, task: SubTask, shared_state: SharedTaskState) -> Any:
        """Execute a sub-task with access to shared state."""
        self.status = AgentStatus.RUNNING
        self.current_task = task
        task.status = AgentStatus.RUNNING
        task.assigned_agent_id = self.agent_id
        task.started_at = datetime.utcnow()

        try:
            logger.info(f"[{self.role.value}:{self.agent_id}] Starting: {task.title}")
            result = await self.executor(task, shared_state)
            task.result = result
            task.status = AgentStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            self.status = AgentStatus.COMPLETED
            logger.info(f"[{self.role.value}:{self.agent_id}] Completed: {task.title}")
            return result
        except Exception as e:
            task.error = str(e)
            task.status = AgentStatus.FAILED
            task.completed_at = datetime.utcnow()
            self.status = AgentStatus.FAILED
            logger.error(f"[{self.role.value}:{self.agent_id}] Failed: {task.title} - {e}")
            raise


class AgentTeamCoordinator:
    """
    Adaptive Agent Team Coordinator — Apodex 1.1 pattern.

    Flow:
    1. DECOMPOSE: Coordinator breaks goal into sub-tasks along verification boundaries
    2. DISPATCH: Spawn specialized sub-agents for each sub-task
    3. EXECUTE: Sub-agents run in parallel with shared state access
    4. SYNTHESIZE: Coordinator integrates results into final deliverable
    5. VERIFY: Adversarial verification of complete work
    """

    def __init__(
        self,
        workspace_root: Path,
        max_parallel: int = 4,
        default_executor: Optional[Callable] = None,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.max_parallel = max_parallel
        self.default_executor = default_executor or self._default_executor

        # Agent registry
        self._agents: dict[str, SubAgent] = {}
        self._role_agents: dict[AgentRole, list[SubAgent]] = {r: [] for r in AgentRole}

        # Execution state
        self._shared_state: Optional[SharedTaskState] = None
        self._running_tasks: dict[str, asyncio.Task] = {}

    def _default_executor(self, task: SubTask, state: SharedTaskState) -> Any:
        """Default executor - override with actual harness/LLM call."""
        logger.warning(f"No executor provided for {task.role.value}: {task.title}")
        return {"status": "mock_completed", "task": task.title}

    def register_agent(
        self,
        role: AgentRole,
        executor: Callable,
        agent_id: Optional[str] = None,
        capabilities: Optional[list[str]] = None,
    ) -> SubAgent:
        """Register a sub-agent for a specific role."""
        agent_id = agent_id or f"{role.value}-{uuid.uuid4().hex[:8]}"
        agent = SubAgent(agent_id, role, executor, capabilities)
        self._agents[agent_id] = agent
        self._role_agents[role].append(agent)
        logger.info(f"Registered {role.value} agent: {agent_id}")
        return agent

    def get_available_agents(self, role: AgentRole) -> list[SubAgent]:
        """Get available (not running) agents for a role."""
        return [a for a in self._role_agents[role] if a.status != AgentStatus.RUNNING]

    async def execute(self, goal: str, context: Optional[dict] = None) -> AgentTeamResult:
        """
        Main entry point: execute a goal with an agent team.

        Args:
            goal: High-level goal description
            context: Optional context (constraints, preferences, existing artifacts)

        Returns:
            AgentTeamResult with final deliverable and verification
        """
        start_time = datetime.utcnow()
        task_id = f"team-{uuid.uuid4().hex[:12]}"

        logger.info(f"[{task_id}] Starting agent team for: {goal}")

        # Initialize shared state
        self._shared_state = SharedTaskState(
            task_id=task_id,
            original_goal=goal,
            metadata=context or {},
        )

        try:
            # Phase 1: Decompose
            self._shared_state.current_phase = "decomposition"
            subtasks = await self._decompose_goal(goal, context)

            # Phase 2: Dispatch & Execute
            self._shared_state.current_phase = "execution"
            await self._dispatch_and_execute(subtasks)

            # Phase 3: Synthesize
            self._shared_state.current_phase = "synthesis"
            final_deliverable = await self._synthesize_results()

            # Phase 4: Verify
            self._shared_state.current_phase = "verification"
            verification_report = await self._verify_final_deliverable(final_deliverable)

            duration = (datetime.utcnow() - start_time).total_seconds()

            return AgentTeamResult(
                task_id=task_id,
                status="completed" if verification_report.get("passed", True) else "failed",
                shared_state=self._shared_state,
                sub_task_results={st.id: st.result for st in subtasks.values()},
                final_deliverable=final_deliverable,
                verification_report=verification_report,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.error(f"[{task_id}] Agent team execution failed: {e}")
            duration = (datetime.utcnow() - start_time).total_seconds()
            return AgentTeamResult(
                task_id=task_id,
                status="failed",
                shared_state=self._shared_state,
                duration_seconds=duration,
                final_deliverable={"error": str(e)},
            )

    async def _decompose_goal(self, goal: str, context: Optional[dict]) -> dict[str, SubTask]:
        """Decompose goal into sub-tasks along verification boundaries (Fable-5 pattern)."""
        logger.info(f"Decomposing goal: {goal}")

        # This is where you'd use an LLM/planner to decompose
        # For now, using a template decomposition based on goal keywords
        subtasks = self._template_decomposition(goal, context)

        # Store in shared state
        for st in subtasks.values():
            self._shared_state.decomposed_subtasks[st.id] = st

        return subtasks

    def _template_decomposition(self, goal: str, context: Optional[dict]) -> dict[str, SubTask]:
        """Template-based decomposition (replace with LLM-based in production)."""
        goal_lower = goal.lower()
        subtasks = {}

        # Always need planning
        subtasks["plan"] = SubTask(
            id="plan",
            role=AgentRole.PLANNER,
            title="Create execution plan",
            description=f"Decompose '{goal}' into verification-bounded steps with clear done criteria",
            required_capabilities=["planning", "task_decomposition"],
        )

        # Research phase if goal involves unknowns
        if any(kw in goal_lower for kw in ["research", "analyze", "investigate", "explore", "find"]):
            subtasks["research"] = SubTask(
                id="research",
                role=AgentRole.RESEARCHER,
                title="Gather evidence & context",
                description="Collect primary sources, existing implementations, documentation",
                dependencies=["plan"],
                required_capabilities=["web_search", "code_search", "documentation"],
            )

        # Architecture/design if building something
        if any(kw in goal_lower for kw in ["build", "create", "implement", "design", "architect"]):
            subtasks["architect"] = SubTask(
                id="architect",
                role=AgentRole.ARCHITECT,
                title="Design system architecture",
                description="Define components, interfaces, data flows, and technical approach",
                dependencies=["plan", "research"] if "research" in subtasks else ["plan"],
                required_capabilities=["system_design", "api_design"],
            )

        # Implementation
        if any(kw in goal_lower for kw in ["implement", "code", "write", "build", "create"]):
            subtasks["implement"] = SubTask(
                id="implement",
                role=AgentRole.CODER,
                title="Implement solution",
                description="Write code, tests, and configuration per architecture",
                dependencies=["architect"] if "architect" in subtasks else ["plan"],
                required_capabilities=["coding", "testing", "debugging"],
            )

        # Documentation
        subtasks["document"] = SubTask(
            id="document",
            role=AgentRole.DOCUMENTER,
            title="Document implementation",
            description="Write README, docstrings, architecture decision records",
            dependencies=["implement"] if "implement" in subtasks else ["plan"],
            required_capabilities=["technical_writing"],
        )

        # Verification (adversarial)
        subtasks["verify"] = SubTask(
            id="verify",
            role=AgentRole.VERIFIER,
            title="Adversarial verification",
            description="Re-run tests, diff changes, hunt weakened tests, check scope",
            dependencies=["implement", "document"],
            required_capabilities=["testing", "static_analysis", "adversarial_verification"],
        )

        # Synthesis
        subtasks["synthesize"] = SubTask(
            id="synthesize",
            role=AgentRole.SYNTHESIZER,
            title="Synthesize final deliverable",
            description="Integrate all artifacts into coherent deliverable with evidence",
            dependencies=["verify"],
            required_capabilities=["integration", "reporting"],
        )

        return subtasks

    async def _dispatch_and_execute(self, subtasks: dict[str, SubTask]) -> None:
        """Execute sub-tasks in parallel respecting dependencies."""
        completed = set()
        running: dict[str, asyncio.Task] = {}

        while len(completed) < len(subtasks):
            # Find ready tasks (dependencies met, not running, not completed)
            ready = [
                st for st in subtasks.values()
                if st.id not in completed
                and st.id not in running
                and all(dep in completed for dep in st.dependencies)
            ]

            # Launch up to max_parallel
            for st in ready[:self.max_parallel - len(running)]:
                agent = self._assign_agent(st)
                if agent:
                    task = asyncio.create_task(self._execute_with_monitoring(agent, st))
                    running[st.id] = task
                else:
                    logger.warning(f"No available agent for {st.role.value}: {st.title}")
                    st.status = AgentStatus.BLOCKED

            # Wait for at least one to complete
            if running:
                done, pending = await asyncio.wait(
                    running.values(),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in done:
                    # Find which subtask this was
                    for st_id, rt in list(running.items()):
                        if rt is t:
                            try:
                                await t  # Raise any exception
                                completed.add(st_id)
                            except Exception as e:
                                logger.error(f"Subtask {st_id} failed: {e}")
                                completed.add(st_id)  # Still mark as done to avoid deadlock
                            del running[st_id]
                            break
            else:
                # No tasks ready and none running - deadlock or all blocked
                blocked = [st for st in subtasks.values() if st.status == AgentStatus.BLOCKED]
                if blocked:
                    logger.error(f"Deadlock: {len(blocked)} tasks blocked, no agents available")
                    break
                await asyncio.sleep(0.1)

    def _assign_agent(self, subtask: SubTask) -> Optional[SubAgent]:
        """Assign best available agent for a sub-task."""
        available = self.get_available_agents(subtask.role)
        if not available:
            return None

        # Prefer agent with matching capabilities
        for agent in available:
            if all(cap in agent.capabilities for cap in subtask.required_capabilities):
                return agent

        return available[0] if available else None

    async def _execute_with_monitoring(self, agent: SubAgent, subtask: SubTask) -> Any:
        """Execute sub-task with monitoring and shared state updates."""
        try:
            result = await agent.execute(subtask, self._shared_state)

            # Store result in shared state evidence
            self._shared_state.add_evidence(
                f"subtask:{subtask.id}",
                {"title": subtask.title, "result": result},
                agent.agent_id
            )

            return result
        except Exception as e:
            # Store error in shared state
            self._shared_state.add_evidence(
                f"subtask:{subtask.id}:error",
                {"title": subtask.title, "error": str(e)},
                agent.agent_id
            )
            raise

    async def _synthesize_results(self) -> Any:
        """Synthesize final deliverable from all sub-task results."""
        logger.info("Synthesizing final deliverable...")

        state = self._shared_state

        # Collect all artifacts
        deliverable = {
            "goal": state.original_goal,
            "task_id": state.task_id,
            "phases": {},
            "evidence": state.evidence_store,
            "decisions": state.decisions,
            "artifacts": {k: v.decode() if isinstance(v, bytes) else v for k, v in state.artifacts.items()},
            "subtask_results": {
                st_id: st.result for st_id, st in state.decomposed_subtasks.items()
            },
            "verification": state.verification_results,
        }

        # Try to get synthesized result from synthesizer agent
        synth_agent = self.get_available_agents(AgentRole.SYNTHESIZER)
        if synth_agent:
            synth_task = SubTask(
                id="synthesize_final",
                role=AgentRole.SYNTHESIZER,
                title="Synthesize final deliverable",
                description="Create coherent final output from all evidence and results",
            )
            try:
                synth_result = await synth_agent[0].execute(synth_task, state)
                deliverable["synthesized_output"] = synth_result
            except Exception as e:
                logger.warning(f"Synthesis agent failed: {e}")

        return deliverable

    async def _verify_final_deliverable(self, deliverable: Any) -> dict:
        """Run adversarial verification on final deliverable."""
        logger.info("Running adversarial verification...")

        # Import here to avoid circular dependency
        from hermes.agi.verification import AdversarialVerifier, WorkPackage

        wp = WorkPackage(
            task_id=self._shared_state.task_id,
            task_description=self._shared_state.original_goal,
        )

        # Add claimed checks from verification subtask
        verify_subtask = self._shared_state.decomposed_subtasks.get("verify")
        if verify_subtask and verify_subtask.result:
            wp.add_claimed_check(
                "adversarial_verification",
                "python -m hermes.agi.verification",
                "pass"
            )

        # Add file changes
        for path in deliverable.get("artifacts", {}):
            wp.add_claimed_file_change(path, "create")

        # Add declared scope
        for st in self._shared_state.decomposed_subtasks.values():
            wp.add_declared_scope(st.title)

        verifier = AdversarialVerifier(self.workspace_root)
        report = await verifier.verify(wp)

        # Store in shared state
        self._shared_state.verification_results = report.to_dict()

        return report.to_dict()


# Integration with existing Harness
async def run_agent_team(
    harness: "Harness",
    goal: str,
    context: Optional[dict] = None,
    max_parallel: int = 4,
) -> AgentTeamResult:
    """
    Convenience function to run agent team from a Harness instance.
    Usage:
        harness = await Harness.create()
        result = await run_agent_team(harness, "Build a REST API with authentication")
    """
    coordinator = AgentTeamCoordinator(
        workspace_root=Path(harness.config.state_dir) if hasattr(harness, 'config') else Path("."),
        max_parallel=max_parallel,
    )

    # Register agents using harness capabilities
    coordinator.register_agent(
        AgentRole.RESEARCHER,
        lambda task, state: harness.research(task.description),
        capabilities=["web_search", "code_search", "documentation"],
    )
    coordinator.register_agent(
        AgentRole.ARCHITECT,
        lambda task, state: harness.think(task.description),
        capabilities=["system_design", "api_design"],
    )
    coordinator.register_agent(
        AgentRole.CODER,
        lambda task, state: harness.run(task.description),
        capabilities=["coding", "testing", "debugging"],
    )
    coordinator.register_agent(
        AgentRole.VERIFIER,
        lambda task, state: harness.asi(task.description),  # Uses full ASI pipeline
        capabilities=["testing", "static_analysis", "adversarial_verification"],
    )
    coordinator.register_agent(
        AgentRole.DOCUMENTER,
        lambda task, state: harness.run(f"Document: {task.description}"),
        capabilities=["technical_writing"],
    )
    coordinator.register_agent(
        AgentRole.PLANNER,
        lambda task, state: harness.discover(task.description),
        capabilities=["planning", "task_decomposition"],
    )
    coordinator.register_agent(
        AgentRole.SYNTHESIZER,
        lambda task, state: harness.run(f"Synthesize final deliverable for: {state.original_goal}"),
        capabilities=["integration", "reporting"],
    )

    return await coordinator.execute(goal, context)


if __name__ == "__main__":
    # Demo
    async def demo():
        coordinator = AgentTeamCoordinator(Path("."))
        result = await coordinator.execute("Create a Python function that validates email addresses")
        print(f"Status: {result.status}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        print(f"Subtasks: {len(result.sub_task_results)}")
        print(f"Verification: {result.verification_report.get('verdict', 'N/A') if result.verification_report else 'N/A'}")

    asyncio.run(demo())