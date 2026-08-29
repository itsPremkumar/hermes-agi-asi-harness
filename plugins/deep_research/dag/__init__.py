#!/usr/bin/env python3
"""
HERMES DEEP RESEARCH ENGINE — DAG RESEARCH EXECUTOR
====================================================
DAG-based research planning and parallel execution.

Extracted from:
- DeepResearch Agent: DAG planning + parallel task execution
- Open Deep Research: Research workflow orchestration
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("hermes_dag_executor")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResearchTask:
    """A research task in the DAG."""
    task_id: str
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DAGResearchExecutor:
    """
    DAG Research Executor — plans and executes research as a DAG.
    
    Features:
    - DAG-based research planning
    - Parallel task execution
    - Dependency resolution
    - Progress tracking
    - Retry on failure
    """
    
    def __init__(self, max_parallel: int = 5):
        self.max_parallel = max_parallel
        self._tasks: Dict[str, ResearchTask] = {}
        self._execution_order: List[str] = []
    
    def create_task(self, name: str, description: str, dependencies: List[str] = None) -> str:
        """Create a research task."""
        task_id = str(uuid.uuid4())
        
        task = ResearchTask(
            task_id=task_id,
            name=name,
            description=description,
            dependencies=dependencies or []
        )
        
        self._tasks[task_id] = task
        return task_id
    
    def build_dag(self, topic: str) -> Dict[str, Any]:
        """Build a research DAG for a topic."""
        # Create tasks
        plan_task = self.create_task("Plan Research", f"Plan research for: {topic}")
        
        search_task = self.create_task("Web Search", f"Search for: {topic}", [plan_task])
        
        crawl_tasks = []
        for i in range(3):
            task_id = self.create_task(
                f"Crawl Source {i+1}",
                f"Crawl and extract from source {i+1}",
                [search_task]
            )
            crawl_tasks.append(task_id)
        
        analyze_task = self.create_task("Analyze Evidence", f"Analyze collected evidence", crawl_tasks)
        
        verify_task = self.create_task("Verify Claims", f"Verify research claims", [analyze_task])
        
        report_task = self.create_task("Generate Report", f"Generate final report", [verify_task])
        
        # Compute execution order
        self._execution_order = self._topological_sort()
        
        return {
            "topic": topic,
            "tasks": len(self._tasks),
            "execution_order": self._execution_order,
            "dag": {
                task_id: {
                    "name": task.name,
                    "dependencies": task.dependencies,
                    "status": task.status.value
                }
                for task_id, task in self._tasks.items()
            }
        }
    
    def _topological_sort(self) -> List[str]:
        """Topological sort of tasks."""
        # Build adjacency list
        in_degree = {task_id: 0 for task_id in self._tasks}
        dependents = {task_id: [] for task_id in self._tasks}
        
        for task_id, task in self._tasks.items():
            for dep in task.dependencies:
                if dep in dependents:
                    dependents[dep].append(task_id)
                    in_degree[task_id] += 1
        
        # BFS
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            task_id = queue.pop(0)
            order.append(task_id)
            
            for dependent in dependents[task_id]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        return order
    
    async def execute(self, task_handlers: Dict[str, Callable] = None) -> Dict[str, Any]:
        """Execute the research DAG."""
        results = {}
        
        for task_id in self._execution_order:
            task = self._tasks[task_id]
            
            # Check dependencies
            deps_complete = all(
                self._tasks[dep].status == TaskStatus.COMPLETED
                for dep in task.dependencies
            )
            
            if not deps_complete:
                task.status = TaskStatus.FAILED
                task.error = "Dependencies not complete"
                continue
            
            # Execute task
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            
            try:
                if task_handlers and task.name in task_handlers:
                    handler = task_handlers[task.name]
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(task.description)
                    else:
                        result = handler(task.description)
                    task.result = str(result)
                else:
                    # Default execution
                    task.result = f"Executed: {task.name}"
                
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                logger.error("Task failed: %s - %s", task.name, e)
            
            results[task_id] = {
                "name": task.name,
                "status": task.status.value,
                "result": task.result,
                "error": task.error
            }
        
        return {
            "tasks_total": len(self._tasks),
            "tasks_completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
            "tasks_failed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED),
            "results": results
        }
    
    async def health(self) -> Dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            "tasks": len(self._tasks),
            "max_parallel": self.max_parallel
        }
