"""Engineering Curriculum - Capability graph with measurable subskills."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Capability:
    id: str
    name: str
    score: float
    subskills: list[str] = field(default_factory=list)

class EngineeringCurriculum:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.capabilities: dict[str, Capability] = {}
    
    def add_capability(self, name: str, score: float, subskills: list[str] | None = None) -> Capability:
        cap = Capability(id=str(uuid.uuid4()), name=name, score=score, subskills=subskills or [])
        self.capabilities[name] = cap
        return cap
    
    def get_gaps(self, threshold: float = 0.7) -> list[Capability]:
        return [c for c in self.capabilities.values() if c.score < threshold]
    
    def get_state(self) -> dict[str, Any]:
        return {"capabilities": len(self.capabilities)}
