"""
MMLU Benchmark — Massive Multitask Language Understanding
57 subjects, 15,908 questions total.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class MMLUQuestion:
    id: str
    question: str
    subject: str
    choices: list[str]
    answer: int  # 0-3 index

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MMLUQuestion":
        return cls(**d)


@dataclass
class MMLUResult:
    id: str
    question_id: str
    predicted: int
    correct: bool
    confidence: float = 0.0
    subject: str = ""


class MMLULoader:
    def __init__(self, data_path: str | None = None) -> None:
        self.data_path = data_path
        self.questions: dict[str, MMLUQuestion] = {}

    def load_questions(self, path: str | None = None) -> list[MMLUQuestion]:
        target = path or self.data_path
        if not target or not os.path.exists(target):
            return []
        with open(target) as f:
            data = json.load(f)
        questions = []
        for item in data:
            q = MMLUQuestion(
                id=str(item.get("id", uuid.uuid4().hex[:8])),
                question=item.get("question", ""),
                subject=item.get("subject", "unknown"),
                choices=item.get("choices", []),
                answer=int(item.get("answer", 0)),
            )
            self.questions[q.id] = q
            questions.append(q)
        return questions

    def get_by_subject(self, subject: str) -> list[MMLUQuestion]:
        return [q for q in self.questions.values() if q.subject == subject]

    def get_subjects(self) -> list[str]:
        return list(set(q.subject for q in self.questions.values()))


class MMLUEvaluator:
    def evaluate(self, question: MMLUQuestion, predicted: int) -> MMLUResult:
        return MMLUResult(
            id=str(uuid.uuid4().hex[:8]),
            question_id=question.id,
            predicted=predicted,
            correct=predicted == question.answer,
            subject=question.subject,
        )

    def evaluate_batch(self, questions: list[MMLUQuestion], predictions: list[int]) -> list[MMLUResult]:
        return [self.evaluate(q, p) for q, p in zip(questions, predictions)]


class MMLUBenchmark:
    def __init__(self, data_path: str | None = None) -> None:
        self.loader = MMLULoader(data_path)
        self.evaluator = MMLUEvaluator()
        self.results: list[MMLUResult] = []

    def load_questions(self, path: str | None = None) -> list[MMLUQuestion]:
        return self.loader.load_questions(path)

    def run_question(self, question_id: str, predicted: int) -> MMLUResult | None:
        q = self.loader.questions.get(question_id)
        if not q:
            return None
        result = self.evaluator.evaluate(q, predicted)
        self.results.append(result)
        return result

    def get_accuracy(self, subject: str | None = None) -> dict[str, float]:
        results = self.results
        if subject:
            results = [r for r in results if r.subject == subject]
        if not results:
            return {"accuracy": 0.0, "total": 0}
        correct = sum(1 for r in results if r.correct)
        return {"accuracy": correct / len(results), "total": len(results)}

    def get_all_subjects_accuracy(self) -> dict[str, dict[str, float]]:
        subjects = set(r.subject for r in self.results)
        return {s: self.get_accuracy(s) for s in subjects}
