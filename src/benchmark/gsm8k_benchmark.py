"""
GSM8K Benchmark — Grade School Math 8K
1,319 word problems requiring multi-step reasoning.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class GSM8KQuestion:
    id: str
    question: str
    answer: float
    steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GSM8KQuestion":
        return cls(**d)


@dataclass
class GSM8KResult:
    id: str
    question_id: str
    predicted: float
    correct: bool
    explanation: str = ""


class GSM8KLoader:
    def __init__(self, data_path: str | None = None) -> None:
        self.data_path = data_path
        self.questions: dict[str, GSM8KQuestion] = {}

    def load_questions(self, path: str | None = None) -> list[GSM8KQuestion]:
        target = path or self.data_path
        if not target or not os.path.exists(target):
            return []
        with open(target) as f:
            data = json.load(f)
        questions = []
        for item in data:
            q = GSM8KQuestion(
                id=str(item.get("id", uuid.uuid4().hex[:8])),
                question=item.get("question", ""),
                answer=float(item.get("answer", 0)),
                steps=item.get("steps", []),
            )
            self.questions[q.id] = q
            questions.append(q)
        return questions


class GSM8KEvaluator:
    def __init__(self, tolerance: float = 1e-6) -> None:
        self.tolerance = tolerance

    def extract_number(self, text: str) -> float | None:
        numbers = re.findall(r"[-+]?\d*\.?\d+", text)
        if numbers:
            return float(numbers[-1])
        return None

    def evaluate(self, question: GSM8KQuestion, response: str) -> GSM8KResult:
        predicted = self.extract_number(response)
        if predicted is None:
            return GSM8KResult(id=str(uuid.uuid4().hex[:8]), question_id=question.id,
                              predicted=0, correct=False, explanation=response)
        correct = abs(predicted - question.answer) < self.tolerance
        return GSM8KResult(id=str(uuid.uuid4().hex[:8]), question_id=question.id,
                          predicted=predicted, correct=correct, explanation=response)


class GSM8KBenchmark:
    def __init__(self, data_path: str | None = None) -> None:
        self.loader = GSM8KLoader(data_path)
        self.evaluator = GSM8KEvaluator()
        self.results: list[GSM8KResult] = []

    def load_questions(self, path: str | None = None) -> list[GSM8KQuestion]:
        return self.loader.load_questions(path)

    def run_question(self, question_id: str, response: str) -> GSM8KResult | None:
        q = self.loader.questions.get(question_id)
        if not q:
            return None
        result = self.evaluator.evaluate(q, response)
        self.results.append(result)
        return result

    def get_accuracy(self) -> dict[str, float]:
        if not self.results:
            return {"accuracy": 0.0, "total": 0}
        correct = sum(1 for r in self.results if r.correct)
        return {"accuracy": correct / len(self.results), "total": len(self.results)}
