"""
Workflow Engine — Production-Grade Async Workflow Orchestration.

Features:
- DAG-based workflow definitions
- Parallel execution with dependency resolution
- Automatic retry with exponential backoff
- Circuit breaker pattern
- Timeout handling
- Progress tracking
- Event-driven architecture
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


# ──────────────────────────── Enums ────────────────────────────


class WorkflowState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ──────────────────────────── Data Classes ────────────────────────────


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    state: TaskState
    result: Any = None
    error: str = ""
    attempts: int = 0
    start_time: float = 0
    end_time: float = 0
    duration: float = 0


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    workflow_id: str
    state: WorkflowState
    results: dict[str, TaskResult] = field(default_factory=dict)
    start_time: float = 0
    end_time: float = 0
    duration: float = 0
    error: str = ""


@dataclass
class Task:
    """A workflow task."""
    task_id: str
    name: str
    coro: Callable[..., Coroutine]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 60.0
    priority: int = 0
    condition: Callable[..., bool] = None
    on_failure: str = "fail"  # fail, skip, retry
    fallback: Callable[..., Coroutine] = None


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance."""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure: float = 0
    
    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN


# ──────────────────────────── Workflow Engine ────────────────────────────


class WorkflowEngine:
    """
    Async workflow engine with DAG execution, retry, circuit breaker.
    """
    
    def __init__(self, max_parallel: int = 4):
        self.max_parallel = max_parallel
        self._workflows: dict[str, WorkflowResult] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = defaultdict(CircuitBreaker)
        self._semaphore = asyncio.Semaphore(max_parallel)
    
    async def execute(self, tasks: list[Task], workflow_id: str = None) -> WorkflowResult:
        """Execute a workflow."""
        workflow_id = workflow_id or str(uuid.uuid4())[:8]
        
        result = WorkflowResult(
            workflow_id=workflow_id,
            state=WorkflowState.RUNNING,
            start_time=time.time(),
        )
        self._workflows[workflow_id] = result
        
        try:
            # Build dependency graph
            task_map = {t.task_id: t for t in tasks}
            completed = set()
            running = set()
                
            async def run_task(task: Task) -> TaskResult:
                """Run a single task with retry and circuit breaker."""
                # Wait for dependencies
                for dep_id in task.dependencies:
                    while dep_id not in completed:
                        await asyncio.sleep(0.1)
                
                # Check condition
                if task.condition and not task.condition():
                    return TaskResult(
                        task_id=task.task_id,
                        state=TaskState.SKIPPED,
                        result=None,
                    )
                
                # Check circuit breaker
                cb = self._circuit_breakers[task.task_id]
                if not cb.can_execute():
                    return TaskResult(
                        task_id=task.task_id,
                        state=TaskState.SKIPPED,
                        result=None,
                        error="Circuit breaker open",
                    )
                
                # Execute with semaphore
                async with self._semaphore:
                    task_result = TaskResult(
                        task_id=task.task_id,
                        state=TaskState.RUNNING,
                        start_time=time.time(),
                    )
                    
                    for attempt in range(task.max_retries + 1):
                        try:
                            task_result.attempts = attempt + 1
                            task_result.state = TaskState.RUNNING
                            
                            # Execute with timeout
                            task_result.result = await asyncio.wait_for(
                                task.coro(*task.args, **task.kwargs),
                                timeout=task.timeout,
                            )
                            task_result.state = TaskState.COMPLETED
                            task_result.end_time = time.time()
                            task_result.duration = task_result.end_time - task_result.start_time
                            
                            cb.record_success()
                            completed.add(task.task_id)
                            return task_result
                            
                        except asyncio.TimeoutError:
                            task_result.error = f"Timeout after {task.timeout}s"
                            logger.warning(f"Task {task.task_id} timeout (attempt {attempt + 1})")
                            if attempt < task.max_retries:
                                task_result.state = TaskState.RETRYING
                                await asyncio.sleep(task.retry_delay * (2 ** attempt))
                            else:
                                cb.record_failure()
                                if task.fallback:
                                    try:
                                        task_result.result = await task.fallback()
                                        task_result.state = TaskState.COMPLETED
                                    except Exception as e:
                                        task_result.error = str(e)
                                        task_result.state = TaskState.FAILED
                                else:
                                    task_result.state = TaskState.FAILED
                                    
                        except Exception as e:
                            task_result.error = str(e)
                            logger.warning(f"Task {task.task_id} failed (attempt {attempt + 1}): {e}")
                            if attempt < task.max_retries:
                                task_result.state = TaskState.RETRYING
                                await asyncio.sleep(task.retry_delay * (2 ** attempt))
                            else:
                                cb.record_failure()
                                if task.fallback:
                                    try:
                                        task_result.result = await task.fallback()
                                        task_result.state = TaskState.COMPLETED
                                    except Exception as e:
                                        task_result.error = str(e)
                                        task_result.state = TaskState.FAILED
                                else:
                                    task_result.state = TaskState.FAILED
                    
                    task_result.end_time = time.time()
                    task_result.duration = task_result.end_time - task_result.start_time
                    return task_result
                
            # Run all tasks
            task_coros = [run_task(t) for t in tasks]
            task_results = await asyncio.gather(*task_coros, return_exceptions=True)
            
            # Collect results
            for task_result in task_results:
                if isinstance(task_result, Exception):
                    logger.error(f"Workflow task exception: {task_result}")
                else:
                    result.results[task_result.task_id] = task_result
            
            # Determine workflow state
            if any(r.state == TaskState.FAILED for r in result.results.values()):
                result.state = WorkflowState.FAILED
            elif all(r.state in (TaskState.COMPLETED, TaskState.SKIPPED) for r in result.results.values()):
                result.state = WorkflowState.COMPLETED
            else:
                result.state = WorkflowState.FAILED
                
        except Exception as e:
            result.state = WorkflowState.FAILED
            result.error = str(e)
            logger.error(f"Workflow {workflow_id} failed: {e}")
        
        result.end_time = time.time()
        result.duration = result.end_time - result.start_time
        return result
    
    def get_workflow(self, workflow_id: str) -> WorkflowResult | None:
        """Get workflow result."""
        return self._workflows.get(workflow_id)
    
    def get_circuit_breaker(self, task_id: str) -> CircuitBreaker:
        """Get circuit breaker for a task."""
        return self._circuit_breakers[task_id]


# ──────────────────────────── Workflow Builder ────────────────────────────


class WorkflowBuilder:
    """Builder for creating workflows."""
    
    def __init__(self, name: str = ""):
        self.name = name
        self.tasks: list[Task] = []
    
    def add_task(
        self,
        task_id: str,
        name: str,
        coro: Callable[..., Coroutine],
        dependencies: list[str] = None,
        args: tuple = (),
        kwargs: dict = None,
        max_retries: int = 3,
        timeout: float = 60.0,
        priority: int = 0,
        condition: Callable[..., bool] = None,
        fallback: Callable[..., Coroutine] = None,
    ) -> "WorkflowBuilder":
        """Add a task to the workflow."""
        self.tasks.append(Task(
            task_id=task_id,
            name=name,
            coro=coro,
            args=args,
            kwargs=kwargs or {},
            dependencies=dependencies or [],
            max_retries=max_retries,
            timeout=timeout,
            priority=priority,
            condition=condition,
            fallback=fallback,
        ))
        return self
    
    def add_parallel_tasks(
        self,
        task_configs: list[dict],
        dependencies: list[str] = None,
    ) -> "WorkflowBuilder":
        """Add multiple tasks that can run in parallel."""
        for config in task_configs:
            self.add_task(
                dependencies=dependencies,
                **config,
            )
        return self
    
    def add_sequential_tasks(
        self,
        task_configs: list[dict],
    ) -> "WorkflowBuilder":
        """Add tasks that must run sequentially."""
        prev_id = None
        for config in task_configs:
            if prev_id:
                config["dependencies"] = [prev_id]
            self.add_task(**config)
            prev_id = config["task_id"]
        return self
    
    def build(self) -> list[Task]:
        """Build the workflow."""
        return self.tasks


# ──────────────────────────── Predefined Workflows ────────────────────────────


class WorkflowLibrary:
    """Library of predefined workflows."""
    
    @staticmethod
    def create_daily_improvement_workflow(
        test_suite: Callable,
        fix_code: Callable,
        run_benchmarks: Callable,
        update_docs: Callable,
        commit_changes: Callable,
    ) -> list[Task]:
        """Create daily improvement workflow."""
        return (
            WorkflowBuilder("daily_improvement")
            .add_task("test", "Run test suite", test_suite, max_retries=0)
            .add_task("fix", "Fix issues", fix_code, dependencies=["test"], max_retries=2)
            .add_task("benchmark", "Run benchmarks", run_benchmarks, dependencies=["fix"], max_retries=1)
            .add_task("docs", "Update documentation", update_docs, dependencies=["fix"], max_retries=1)
            .add_task("commit", "Commit changes", commit_changes, dependencies=["benchmark", "docs"], max_retries=3)
            .build()
        )
    
    @staticmethod
    def create_self_healing_workflow(
        health_check: Callable,
        diagnose: Callable,
        repair: Callable,
        verify: Callable,
    ) -> list[Task]:
        """Create self-healing workflow."""
        return (
            WorkflowBuilder("self_healing")
            .add_task("check", "Health check", health_check, max_retries=0)
            .add_task("diagnose", "Diagnose issues", diagnose, dependencies=["check"], max_retries=1)
            .add_task("repair", "Repair issues", repair, dependencies=["diagnose"], max_retries=3)
            .add_task("verify", "Verify repair", verify, dependencies=["repair"], max_retries=2)
            .build()
        )
    
    @staticmethod
    def create_research_workflow(
        search: Callable,
        analyze: Callable,
        synthesize: Callable,
        write_report: Callable,
    ) -> list[Task]:
        """Create research workflow."""
        return (
            WorkflowBuilder("research")
            .add_task("search", "Search sources", search, max_retries=2)
            .add_task("analyze", "Analyze sources", analyze, dependencies=["search"], max_retries=1)
            .add_task("synthesize", "Synthesize findings", synthesize, dependencies=["analyze"], max_retries=1)
            .add_task("report", "Write report", write_report, dependencies=["synthesize"], max_retries=1)
            .build()
        )
    
    @staticmethod
    def create_deployment_workflow(
        test: Callable,
        build: Callable,
        stage: Callable,
        deploy: Callable,
        verify: Callable,
    ) -> list[Task]:
        """Create deployment workflow."""
        return (
            WorkflowBuilder("deployment")
            .add_task("test", "Run tests", test, max_retries=0)
            .add_task("build", "Build package", build, dependencies=["test"], max_retries=1)
            .add_task("stage", "Stage deployment", stage, dependencies=["build"], max_retries=1)
            .add_task("deploy", "Deploy", deploy, dependencies=["stage"], max_retries=3)
            .add_task("verify", "Verify deployment", verify, dependencies=["deploy"], max_retries=2)
            .build()
        )
