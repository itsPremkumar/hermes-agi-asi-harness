"""Skill Forge - Extract reusable skills from trajectories."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class Skill:
    id: str
    name: str
    description: str
    steps: list[dict[str, Any]]
    source_trajectory: str
    benchmark_score: float = 0.0
    verified: bool = False

class SkillForge:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.skills: dict[str, Skill] = {}
    
    def extract_skill(self, name: str, description: str, trajectory: dict[str, Any]) -> Skill:
        skill = Skill(id=str(uuid.uuid4()), name=name, description=description,
                     steps=[], source_trajectory=trajectory.get("id", ""))
        self.skills[skill.id] = skill
        return skill
    
    def get_state(self) -> dict[str, Any]:
        return {"skills": len(self.skills)}
