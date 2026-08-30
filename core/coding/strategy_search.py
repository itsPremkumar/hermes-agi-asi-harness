"""Strategy Search."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

class StrategyType(str, Enum):
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEBUGGING = "debugging"
    DEPLOYMENT = "deployment"
    ROLLBACK = "rollback"

@dataclass
class Strategy:
    id: str
    strategy_type: StrategyType
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_cost: float = 0.5
    risk: float = 0.5

@dataclass
class StrategyEvaluation:
    strategy_id: str
    correctness: float = 0.5
    speed: float = 0.5
    cost: float = 0.5
    maintainability: float = 0.5
    risk: float = 0.5
    @property
    def overall(self) -> float:
        return (self.correctness + self.speed + self.cost + self.maintainability + self.risk) / 5

class StrategySearcher:
    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self.evaluations: Dict[str, StrategyEvaluation] = {}
    
    def register(self, strategy_type: StrategyType, name: str,
                 description: str, **kwargs) -> Strategy:
        s = Strategy(id=str(uuid.uuid4()), strategy_type=strategy_type,
                    name=name, description=description, **kwargs)
        self.strategies[s.id] = s
        return s
    
    def evaluate(self, strategy_id: str, **kwargs) -> StrategyEvaluation:
        e = StrategyEvaluation(strategy_id=strategy_id, **kwargs)
        self.evaluations[strategy_id] = e
        return e
    
    def search(self, strategy_type: StrategyType) -> List[Strategy]:
        candidates = [s for s in self.strategies.values() if s.strategy_type == strategy_type]
        candidates.sort(key=lambda s: self.evaluations.get(s.id, StrategyEvaluation(strategy_id=s.id)).overall, reverse=True)
        return candidates
    
    def get_best(self, strategy_type: StrategyType) -> Optional[Strategy]:
        results = self.search(strategy_type)
        return results[0] if results else None
    
    def get_state(self) -> Dict[str, Any]:
        return {"strategies": len(self.strategies), "evaluations": len(self.evaluations)}
