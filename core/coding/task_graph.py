"""Engineering Task Graph — Product goal → dependency-aware DAG."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class Task:
    id: str
    name: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: int = 0  # minutes
    assigned_agent: str = ""
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class TaskGraph:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.tasks: Dict[str, Task] = {}
    
    def add_task(self, name: str, description: str,
                 dependencies: List[str] = None, **kwargs) -> Task:
        task = Task(id=str(uuid.uuid4()), name=name, description=description,
                   dependencies=dependencies or [], **kwargs)
        self.tasks[task.id] = task
        return task
    
    def get_ready_tasks(self) -> List[Task]:
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            deps_met = all(
                self.tasks.get(dep_id, Task(id="", name="", description="")).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if deps_met:
                ready.append(task)
        return ready
    
    def get_next_batch(self) -> List[Task]:
        return sorted(self.get_ready_tasks(), key=lambda t: -t.priority)
    
    def complete_task(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
    
    def get_critical_path(self) -> List[str]:
        """Find the longest dependency chain (simplified)."""
        visited = set()
        longest = []
        
        def dfs(task_id: str, path: List[str]):
            nonlocal longest
            if task_id in visited:
                return
            visited.add(task_id)
            path.append(task_id)
            if len(path) > len(longest):
                longest = list(path)
            task = self.tasks.get(task_id)
            if task:
                for dep in task.dependencies:
                    dfs(dep, path)
            path.pop()
        
        for task_id in self.tasks:
            visited.clear()
            dfs(task_id, [])
        
        return longest
    
    def get_state(self) -> Dict[str, Any]:
        status_counts = {}
        for task in self.tasks.values():
            status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1
        return {"total": len(self.tasks), "status": status_counts}
