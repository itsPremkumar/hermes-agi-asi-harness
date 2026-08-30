"""Coding Evaluation Pyramid - 10 levels of evaluation."""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any


class EvalLevel(str, Enum):
    SYNTAX = "syntax"
    UNIT = "unit"
    INTEGRATION = "integration"
    REPOSITORY = "repository"
    REFACTOR = "refactor"
    MIGRATION = "migration"
    LONG_HORIZON = "long_horizon"
    PRODUCTION_SIM = "production_sim"
    NOVEL_REPOS = "novel_repos"
    CROSS_DOMAIN = "cross_domain"

class EvaluationPyramid:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.results: dict[str, float] = {}
    
    def evaluate_level(self, level: EvalLevel, score: float):
        self.results[level.value] = score
    
    def get_weakest_level(self) -> str:
        if not self.results:
            return ""
        return min(self.results, key=self.results.get)
    
    def get_state(self) -> dict[str, Any]:
        return {"levels_evaluated": len(self.results)}
