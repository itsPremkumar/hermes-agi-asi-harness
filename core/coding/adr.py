"""Architecture Decision Records (ADR)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ADRStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"

@dataclass
class ADR:
    id: str
    number: int
    title: str
    problem: str
    constraints: list[str]
    alternatives: list[dict[str, str]]
    chosen: str
    rejected: list[str]
    evidence: str
    consequences: list[str]
    reversibility: str = "high"
    status: ADRStatus = ADRStatus.PROPOSED
    owner: str = ""
    created_at: float = field(default_factory=time.time)

class ADRRegistry:
    def __init__(self):
        self.adrs: dict[str, ADR] = {}
        self._counter = 0
    
    def create(self, title: str, problem: str, constraints: list[str],
               alternatives: list[dict[str, str]], chosen: str,
               rejected: list[str], evidence: str,
               consequences: list[str], **kwargs) -> ADR:
        self._counter += 1
        adr = ADR(id=str(uuid.uuid4()), number=self._counter, title=title,
                  problem=problem, constraints=constraints,
                  alternatives=alternatives, chosen=chosen, rejected=rejected,
                  evidence=evidence, consequences=consequences, **kwargs)
        self.adrs[adr.id] = adr
        return adr
    
    def accept(self, adr_id: str):
        if adr_id in self.adrs:
            self.adrs[adr_id].status = ADRStatus.ACCEPTED
    
    def get_accepted(self) -> list[ADR]:
        return [a for a in self.adrs.values() if a.status == ADRStatus.ACCEPTED]
    
    def get_all(self) -> list[ADR]:
        return list(self.adrs.values())
    
    def get_state(self) -> dict[str, Any]:
        return {"total": len(self.adrs), "accepted": len(self.get_accepted())}
