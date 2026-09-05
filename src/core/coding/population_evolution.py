"""Population-Based Coding Evolution — Archive, mutate, evaluate."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class Candidate:
    id: str
    strategy: dict[str, Any]
    score: float = 0.0
    parent: str = ""

class PopulationEvolution:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.archive: list[Candidate] = []
        self.generation = 0
    
    def add_candidate(self, strategy: dict[str, Any],
                      score: float = 0.0, parent: str = "") -> Candidate:
        c = Candidate(id=str(uuid.uuid4()), strategy=strategy, score=score, parent=parent)
        self.archive.append(c)
        return c
    
    def evolve(self) -> Candidate:
        if len(self.archive) < 2:
            return Candidate(id=str(uuid.uuid4()), strategy={})
        parents = sorted(self.archive, key=lambda c: c.score, reverse=True)[:2]
        child = Candidate(id=str(uuid.uuid4()),
                         strategy={"parent_a": parents[0].id, "parent_b": parents[1].id})
        self.archive.append(child)
        self.generation += 1
        return child
    
    def get_state(self) -> dict[str, Any]:
        return {"archive": len(self.archive), "generation": self.generation}
