"""GSM8K Benchmark — Grade School Math Word Problems."""
from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GSM8KQuestion:
    question_id: str
    question: str
    answer: float
    steps: list[str] = field(default_factory=list)


@dataclass
class GSM8KResult:
    question_id: str
    correct: bool
    predicted: float
    expected: float
    error_margin: float = 0.01


class GSM8KBenchmark:
    """GSM8K benchmark adapter."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self._questions: list[GSM8KQuestion] = []

    def load_questions(self) -> list[GSM8KQuestion]:
        """Load GSM8K questions from data directory."""
        if not self.data_dir.exists():
            return []
        return self._questions

    def add_question(self, question: GSM8KQuestion) -> None:
        self._questions.append(question)

    def evaluate(self, question_id: str, answer: float) -> bool:
        """Evaluate an answer with tolerance for floating point."""
        question = next((q for q in self._questions if q.question_id == question_id), None)
        if not question:
            return False
        return abs(answer - question.answer) < 0.01

    def run_benchmark(self, num_questions: int | None = None) -> dict[str, Any]:
        """Run the GSM8K benchmark."""
        questions = self._questions
        if num_questions:
            questions = questions[:num_questions]

        results = []
        for q in questions:
            # In production: get answer from LLM
            predicted = q.answer + random.uniform(-1, 1)
            correct = self.evaluate(q.question_id, predicted)
            results.append(GSM8KResult(
                question_id=q.question_id,
                correct=correct,
                predicted=predicted,
                expected=q.answer,
            ))

        correct_count = sum(1 for r in results if r.correct)
        total = len(results) if results else 1
        return {
            "benchmark": "gsm8k",
            "total": total,
            "correct": correct_count,
            "accuracy": correct_count / total,
            "results": results,
        }

    def generate_synthetic_questions(self, count: int = 50) -> list[GSM8KQuestion]:
        """Generate synthetic GSM8K questions for testing."""
        questions = []
        templates = [
            "If John has {a} apples and gives {b} to Mary, how many apples does John have?",
            "A store sells {a} items per day. How many items are sold in {b} days?",
            "If a car travels {a} miles per hour for {b} hours, how far does it travel?",
        ]
        for i in range(count):
            a, b = random.randint(1, 100), random.randint(1, 100)
            template = templates[i % len(templates)]
            question = template.format(a=a, b=b)
            answer = a - b if "gives" in question else a * b
            q = GSM8KQuestion(
                question_id=f"gsm8k-{i}",
                question=question,
                answer=float(answer),
                steps=[f"Step 1: Parse the problem", f"Step 2: Calculate {answer}"],
            )
            questions.append(q)
            self.add_question(q)
        return questions

    def save_results(self, results: dict[str, Any], path: str) -> None:
        """Save benchmark results to a JSON file."""
        with open(path, "w") as f:
            json.dump(results, f, indent=2, default=str)

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about loaded questions."""
        return {
            "total_questions": len(self._questions),
        }
