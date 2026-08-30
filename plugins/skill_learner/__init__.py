#!/usr/bin/env python3
"""
Skill Learner Plugin — Automated skill extraction and management
==============================================================
Features:
- Learn skills from successful task executions
- Store skills as reusable templates
- Match skills to new tasks
- Skill versioning and improvement
- Skill effectiveness tracking
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_skill_learner")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum
    
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: list[str] = field(default_factory=list)
        shell_commands: list[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: list[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: list[str] = field(default_factory=list)
        path: Path | None = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


@dataclass
class Skill:
    """A learned skill."""
    id: str
    name: str
    description: str
    trigger_patterns: list[str]
    steps: list[str]
    success_count: int = 0
    failure_count: int = 0
    avg_duration: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used: str | None = None
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillLearner:
    """Learns and manages skills."""
    
    def __init__(self, storage_path: str = ".hermes/skills"):
        self.storage_path = Path(storage_path)
        self.skills: dict[str, Skill] = {}
        self._loaded = False
    
    def load(self):
        """Load skills from storage."""
        if self._loaded:
            return
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        for skill_file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(skill_file.read_text(encoding="utf-8"))
                skill = Skill(**data)
                self.skills[skill.id] = skill
            except Exception as e:
                logger.warning(f"Failed to load skill {skill_file}: {e}")
        
        self._loaded = True
    
    def save(self):
        """Save skills to storage."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        for skill in self.skills.values():
            skill_file = self.storage_path / f"{skill.id}.json"
            skill_file.write_text(json.dumps(skill.__dict__, indent=2), encoding="utf-8")
    
    def learn_skill(self, name: str, description: str, trigger_patterns: list[str], steps: list[str]) -> str:
        """Learn a new skill."""
        skill_id = f"skill_{hashlib.md5(name.encode()).hexdigest()[:12]}"
        
        skill = Skill(
            id=skill_id,
            name=name,
            description=description,
            trigger_patterns=trigger_patterns,
            steps=steps,
        )
        
        self.skills[skill_id] = skill
        self.save()
        
        logger.info(f"Learned skill: {name} ({skill_id})")
        return skill_id
    
    def match_skill(self, task_description: str) -> Skill | None:
        """Match a task to the best skill."""
        best_skill = None
        best_score = 0.0
        
        task_lower = task_description.lower()
        
        for skill in self.skills.values():
            score = 0.0
            for pattern in skill.trigger_patterns:
                if pattern.lower() in task_lower:
                    score += 1.0
                # Partial match
                elif any(word in task_lower for word in pattern.lower().split()):
                    score += 0.3
            
            # Factor in success rate
            total_uses = skill.success_count + skill.failure_count
            if total_uses > 0:
                success_rate = skill.success_count / total_uses
                score *= (0.5 + 0.5 * success_rate)
            
            if score > best_score:
                best_score = score
                best_skill = skill
        
        return best_skill if best_score > 0 else None
    
    def record_outcome(self, skill_id: str, success: bool, duration: float = 0.0):
        """Record skill usage outcome."""
        skill = self.skills.get(skill_id)
        if not skill:
            return
        
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1
        
        # Update average duration
        total_uses = skill.success_count + skill.failure_count
        skill.avg_duration = (skill.avg_duration * (total_uses - 1) + duration) / total_uses
        skill.last_used = datetime.utcnow().isoformat()
        
        self.save()
    
    def get_skill(self, skill_id: str) -> Skill | None:
        return self.skills.get(skill_id)
    
    def list_skills(self) -> list[dict[str, Any]]:
        """List all skills."""
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "success_count": s.success_count,
                "failure_count": s.failure_count,
                "success_rate": (s.success_count / (s.success_count + s.failure_count)) if (s.success_count + s.failure_count) > 0 else 0.0,
                "avg_duration": s.avg_duration,
                "version": s.version,
            }
            for s in self.skills.values()
        ]
    
    def improve_skill(self, skill_id: str, new_steps: list[str]) -> bool:
        """Improve a skill with new steps."""
        skill = self.skills.get(skill_id)
        if not skill:
            return False
        
        skill.steps = new_steps
        skill.version += 1
        skill.metadata["improved_at"] = datetime.utcnow().isoformat()
        self.save()
        return True
    
    def remove_skill(self, skill_id: str) -> bool:
        """Remove a skill."""
        if skill_id in self.skills:
            del self.skills[skill_id]
            skill_file = self.storage_path / f"{skill_id}.json"
            if skill_file.exists():
                skill_file.unlink()
            return True
        return False
    
    def get_stats(self) -> dict[str, Any]:
        """Get skill library stats."""
        total_success = sum(s.success_count for s in self.skills.values())
        total_failure = sum(s.failure_count for s in self.skills.values())
        
        return {
            "total_skills": len(self.skills),
            "total_success": total_success,
            "total_failure": total_failure,
            "overall_success_rate": (total_success / (total_success + total_failure)) if (total_success + total_failure) > 0 else 0.0,
        }


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Skill Learner Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="skill_learner",
            version="1.0.0",
            description="Automatic skill extraction from successful executions, skill matching, and improvement tracking",
            license="MIT",
            source="internal",
            capabilities=["skill_learning", "skill_matching", "skill_improvement", "skill_tracking"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=20,
            ),
        )
        self.learner: SkillLearner | None = None
    
    async def load(self) -> bool:
        self.learner = SkillLearner()
        self.learner.load()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.learner:
            self.learner = SkillLearner()
            self.learner.load()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.learner is not None,
            "skills": len(self.learner.skills) if self.learner else 0,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def learn_skill(self, name: str, description: str, trigger_patterns: list[str], steps: list[str]) -> str:
        return self.learner.learn_skill(name, description, trigger_patterns, steps)
    
    def match_skill(self, task_description: str) -> dict[str, Any] | None:
        skill = self.learner.match_skill(task_description)
        if skill:
            return {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "steps": skill.steps,
                "success_rate": (skill.success_count / (skill.success_count + skill.failure_count)) if (skill.success_count + skill.failure_count) > 0 else 0.0,
            }
        return None
    
    def record_outcome(self, skill_id: str, success: bool, duration: float = 0.0):
        self.learner.record_outcome(skill_id, success, duration)
    
    def list_skills(self) -> list[dict[str, Any]]:
        return self.learner.list_skills()
    
    def improve_skill(self, skill_id: str, new_steps: list[str]) -> bool:
        return self.learner.improve_skill(skill_id, new_steps)
    
    def remove_skill(self, skill_id: str) -> bool:
        return self.learner.remove_skill(skill_id)
    
    def get_stats(self) -> dict[str, Any]:
        return self.learner.get_stats()
    
    def get_capabilities(self) -> list[str]:
        return self.manifest.capabilities
