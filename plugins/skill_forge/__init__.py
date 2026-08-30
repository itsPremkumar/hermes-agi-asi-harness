"""
Skill Forge Plugin — Procedural Skill Generation & Refinement

Implements: skill creation, testing, deployment, versioning, retirement.
Skills are reusable procedures built from successful task patterns.
"""

import time
import json
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
from pathlib import Path


class SkillStatus(str, Enum):
    DRAFT = "draft"
    TESTING = "testing"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass
class Skill:
    name: str
    description: str
    procedure: str
    triggers: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    usage_count: int = 0
    version: str = "1.0.0"
    status: SkillStatus = SkillStatus.DRAFT
    skill_id: str = field(default_factory=lambda: f"SKILL-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}")
    created_at: float = field(default_factory=time.time)
    last_used: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "procedure": self.procedure,
            "triggers": self.triggers,
            "preconditions": self.preconditions,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "version": self.version,
            "status": self.status.value,
            "skill_id": self.skill_id,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "metadata": self.metadata,
        }


class SkillForge:
    """Forge new skills from patterns."""

    def __init__(self, storage_path: Optional[Path] = None):
        self._skills: Dict[str, Skill] = {}
        self._storage_path = storage_path
        if storage_path and storage_path.exists():
            self._load()

    def _load(self):
        try:
            with open(self._storage_path, "r") as f:
                data = json.load(f)
                for s in data.get("skills", []):
                    skill = Skill(**s)
                    self._skills[skill.skill_id] = skill
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    def _save(self):
        if not self._storage_path:
            return
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "w") as f:
                json.dump(
                    {"skills": [s.to_dict() for s in self._skills.values()]},
                    f, indent=2
                )
        except Exception:
            pass

    def forge_skill(self, name: str, description: str, procedure: str,
                    triggers: List[str] = None,
                    preconditions: List[str] = None) -> Skill:
        """Forge a new skill from a successful pattern."""
        skill = Skill(
            name=name,
            description=description,
            procedure=procedure,
            triggers=triggers or [],
            preconditions=preconditions or [],
            status=SkillStatus.TESTING,
        )
        self._skills[skill.skill_id] = skill
        self._save()
        return skill

    def find_matching_skill(self, task: str) -> Optional[Skill]:
        """Find a skill that matches a task based on triggers."""
        task_lower = task.lower()
        best_match = None
        best_score = 0.0

        for skill in self._skills.values():
            if skill.status != SkillStatus.DEPLOYED:
                continue
            for trigger in skill.triggers:
                if trigger.lower() in task_lower:
                    score = len(trigger) / len(task_lower) if task_lower else 0
                    if score > best_score:
                        best_score = score
                        best_match = skill
        return best_match

    def record_usage(self, skill_id: str, success: bool):
        """Record skill usage and update success rate."""
        if skill_id not in self._skills:
            return
        skill = self._skills[skill_id]
        skill.usage_count += 1
        skill.last_used = time.time()
        # Bayesian update of success rate
        alpha = skill.success_rate * 100 + (10 if success else 1)
        beta = (1 - skill.success_rate) * 100 + (10 if not success else 1)
        skill.success_rate = alpha / (alpha + beta)
        self._save()

    def deploy_skill(self, skill_id: str):
        if skill_id in self._skills:
            self._skills[skill_id].status = SkillStatus.DEPLOYED
            self._save()

    def retire_skill(self, skill_id: str):
        if skill_id in self._skills:
            self._skills[skill_id].status = SkillStatus.RETIRED
            self._save()

    def list_skills(self, status: Optional[SkillStatus] = None) -> List[Skill]:
        if status:
            return [s for s in self._skills.values() if s.status == status]
        return list(self._skills.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_skills": len(self._skills),
            "deployed": sum(1 for s in self._skills.values() if s.status == SkillStatus.DEPLOYED),
            "testing": sum(1 for s in self._skills.values() if s.status == SkillStatus.TESTING),
            "retired": sum(1 for s in self._skills.values() if s.status == SkillStatus.RETIRED),
            "total_usage": sum(s.usage_count for s in self._skills.values()),
            "avg_success_rate": sum(s.success_rate for s in self._skills.values()) / max(1, len(self._skills)),
        }


class SkillForgePlugin:
    def __init__(self, storage_path: Optional[Path] = None):
        self.engine = SkillForge(storage_path=storage_path)

    async def load(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health(self):
        return {
            "status": "healthy",
            "stats": self.engine.get_stats(),
        }


async def create(kernel=None):
    plugin = SkillForgePlugin()
    if kernel:
        plugin._kernel = kernel
    return plugin
