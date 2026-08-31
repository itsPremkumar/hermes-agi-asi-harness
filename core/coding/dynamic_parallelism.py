"""Dynamic Parallelism — Parallelize independent tasks with conflict detection."""
from __future__ import annotations

import uuid


class ParallelScheduler:
    def __init__(self):
        self.id = str(uuid.uuid4())
    
    def schedule(self, tasks: list[dict]) -> list[list[str]]:
        """Schedule tasks into parallel batches."""
        batches = []
        completed = set()
        remaining = {t["id"]: t for t in tasks}
        
        while remaining:
            batch = []
            for task_id, task in list(remaining.items()):
                deps = set(task.get("dependencies", []))
                if deps.issubset(completed):
                    batch.append(task_id)
            
            if not batch:
                break
            
            batches.append(batch)
            for task_id in batch:
                completed.add(task_id)
                del remaining[task_id]
        
        return batches
    
    def detect_conflicts(self, tasks: list[dict]) -> list[dict]:
        """Detect resource conflicts between tasks."""
        conflicts = []
        for i, task_a in enumerate(tasks):
            for task_b in tasks[i+1:]:
                files_a = set(task_a.get("files", []))
                files_b = set(task_b.get("files", []))
                overlap = files_a & files_b
                if overlap:
                    conflicts.append({
                        "task_a": task_a["id"],
                        "task_b": task_b["id"],
                        "conflict": list(overlap),
                    })
        return conflicts
