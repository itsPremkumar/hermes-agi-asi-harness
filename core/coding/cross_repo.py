"""Cross-Repository Reasoning - Repo A depends on Repo B."""
from __future__ import annotations

import uuid
from typing import Any


class CrossRepoReasoning:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.dependencies: dict[str, list[str]] = {}
    
    def add_dependency(self, repo: str, depends_on: str):
        if repo not in self.dependencies:
            self.dependencies[repo] = []
        self.dependencies[repo].append(depends_on)
    
    def get_impact(self, changed_repo: str) -> list[str]:
        impacted = []
        for repo, deps in self.dependencies.items():
            if changed_repo in deps:
                impacted.append(repo)
        return impacted
    
    def get_state(self) -> dict[str, Any]:
        return {"repos": len(self.dependencies)}
