"""
SIQA Benchmark — Social Interaction Question Answering

15K+ social commonsense questions for evaluating AI understanding of
social situations, emotional states, and interpersonal dynamics.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class SIQAQuestion:
    id: str
    context: str
    question: str
    choices: list[str]
    correct_answer: int  # 0-indexed
    metadata: dict = field(default_factory=dict)


@dataclass
class SIQAResult:
    question_id: str
    predicted_answer: int
    correct_answer: int
    correct: bool
    confidence: float = 0.0
    duration: float = 0.0


@dataclass
class SIQADataset:
    questions: list[SIQAQuestion]
    metadata: dict = field(default_factory=dict)


class SIQABenchmark:
    """SIQA benchmark for social commonsense evaluation."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else Path("./data/siqa")
        self._dataset: Optional[SIQADataset] = None
        self._results: list[SIQAResult] = []

    def load(self, split: str = "validation") -> SIQADataset:
        """Load SIQA dataset from disk."""
        self._dataset = SIQADataset(questions=[], metadata={"split": split})

        # Try multiple file patterns
        patterns = [
            self.data_dir / f"siqa_{split}.jsonl",
            self.data_dir / f"siqa_{split}.json",
            self.data_dir / "siqa.jsonl",
            self.data_dir / "siqa.json",
        ]

        for path in patterns:
            if path.exists():
                self._dataset = self._load_file(path)
                logger.info(f"Loaded {len(self._dataset.questions)} questions from {path}")
                return self._dataset

        # If no file found, generate synthetic data for testing
        logger.warning(f"No SIQA data found in {self.data_dir}, generating synthetic data")
        self._dataset = self._generate_synthetic()
        return self._dataset

    def _load_file(self, path: Path) -> SIQADataset:
        """Load questions from a file."""
        questions = []

        if path.suffix == ".jsonl":
            with open(path) as f:
                for line in f:
                    data = json.loads(line.strip())
                    questions.append(self._parse_question(data))
        else:
            with open(path) as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        questions.append(self._parse_question(item))
                elif isinstance(data, dict) and "questions" in data:
                    for item in data["questions"]:
                        questions.append(self._parse_question(item))

        return SIQADataset(questions=questions, metadata={"source": str(path)})

    def _parse_question(self, data: dict) -> SIQAQuestion:
        """Parse a question from raw data."""
        # Handle multiple SIQA formats
        if "choices" in data:
            choices = data["choices"]
            if isinstance(choices, dict):
                choices = [choices.get(str(i), "") for i in range(len(choices))]
        elif "answerA" in data:
            choices = [
                data.get("answerA", ""),
                data.get("answerB", ""),
                data.get("answerC", ""),
            ]
        else:
            choices = ["", "", ""]

        # Determine correct answer
        correct = data.get("correct", data.get("answer", "A"))
        if isinstance(correct, str):
            correct_map = {"A": 0, "B": 1, "C": 2, "D": 3}
            correct_idx = correct_map.get(correct, 0)
        else:
            correct_idx = int(correct) - 1 if correct > 0 else 0

        return SIQAQuestion(
            id=str(data.get("id", data.get("qid", len(choices)))),
            context=data.get("context", data.get("premise", "")),
            question=data.get("question", ""),
            choices=choices,
            correct_answer=correct_idx,
            metadata=data.get("metadata", {}),
        )

    def _generate_synthetic(self, count: int = 100) -> SIQADataset:
        """Generate synthetic SIQA data for testing."""
        questions = []
        templates = [
            {
                "context": "After failing the exam, {name} felt {emotion}.",
                "question": "How would {name} feel afterwards?",
                "choices": ["disappointed", "excited", "indifferent"],
                "correct": 0,
            },
            {
                "context": "{name} received a surprise birthday party from friends.",
                "question": "What will {name} want to do next?",
                "choices": ["thank everyone", "leave early", "ignore them"],
                "correct": 0,
            },
            {
                "context": "{name} accidentally broke a friend's favorite vase.",
                "question": "What should {name} do?",
                "choices": ["apologize sincerely", "hide the evidence", "blame someone else"],
                "correct": 0,
            },
            {
                "context": "During the meeting, {name} was interrupted repeatedly.",
                "question": "How might {name} feel?",
                "choices": ["frustrated", "happy", "grateful"],
                "correct": 0,
            },
            {
                "context": "{name} helped a stranger carry heavy groceries.",
                "question": "How would the stranger feel?",
                "choices": ["grateful", "suspicious", "angry"],
                "correct": 0,
            },
            {
                "context": "{name} studied hard and passed the exam.",
                "question": "How would {name} feel?",
                "choices": ["proud", "disappointed", "indifferent"],
                "correct": 0,
            },
            {
                "context": "{name} was stuck in traffic for hours.",
                "question": "How might {name} feel?",
                "choices": ["relaxed", "frustrated", "excited"],
                "correct": 1,
            },
            {
                "context": "{name} got a promotion at work.",
                "question": "What will {name} want to do next?",
                "choices": ["quit immediately", "celebrate with colleagues", "ignore the news"],
                "correct": 1,
            },
        ]

        names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Quinn", "Avery"]

        for i in range(count):
            template = templates[i % len(templates)]
            name = names[i % len(names)]
            question = SIQAQuestion(
                id=f"siqa_synth_{i:04d}",
                context=template["context"].format(name=name, emotion="sad"),
                question=template["question"].format(name=name),
                choices=template["choices"],
                correct_answer=template["correct"],
                metadata={"synthetic": True},
            )
            questions.append(question)

        return SIQADataset(questions=questions, metadata={"synthetic": True, "count": count})

    def run(
        self,
        predictor: Callable[[SIQAQuestion], Awaitable[int]],
        max_questions: Optional[int] = None,
    ) -> list[SIQAResult]:
        """Run benchmark on all or a subset of questions."""
        if self._dataset is None:
            self.load()

        questions = self._dataset.questions
        if max_questions:
            questions = questions[:max_questions]

        self._results = []
        for question in questions:
            started = time.time()
            try:
                predicted = asyncio.run(predictor(question))
                duration = time.time() - started
                result = SIQAResult(
                    question_id=question.id,
                    predicted_answer=predicted,
                    correct_answer=question.correct_answer,
                    correct=predicted == question.correct_answer,
                    duration=duration,
                )
            except Exception as e:
                result = SIQAResult(
                    question_id=question.id,
                    predicted_answer=-1,
                    correct_answer=question.correct_answer,
                    correct=False,
                    duration=time.time() - started,
                )
                logger.warning(f"Question {question.id} failed: {e}")

            self._results.append(result)

        return self._results

    def run_sample(
        self,
        predictor: Callable[[SIQAQuestion], Awaitable[int]],
        sample_size: int = 10,
        seed: int = 42,
    ) -> list[SIQAResult]:
        """Run benchmark on a random sample."""
        if self._dataset is None:
            self.load()

        random.seed(seed)
        questions = random.sample(self._dataset.questions, min(sample_size, len(self._dataset.questions)))

        results = []
        for question in questions:
            started = time.time()
            try:
                predicted = asyncio.run(predictor(question))
                duration = time.time() - started
                result = SIQAResult(
                    question_id=question.id,
                    predicted_answer=predicted,
                    correct_answer=question.correct_answer,
                    correct=predicted == question.correct_answer,
                    duration=duration,
                )
            except Exception:
                result = SIQAResult(
                    question_id=question.id,
                    predicted_answer=-1,
                    correct_answer=question.correct_answer,
                    correct=False,
                    duration=time.time() - started,
                )
            results.append(result)

        return results

    def get_accuracy(self) -> float:
        """Get overall accuracy."""
        if not self._results:
            return 0.0
        correct = sum(1 for r in self._results if r.correct)
        return correct / len(self._results)

    def get_category_accuracy(self) -> dict[str, float]:
        """Get accuracy by category (if available)."""
        if not self._results or self._dataset is None:
            return {}

        category_results: dict[str, list[bool]] = {}
        question_map = {q.id: q for q in self._dataset.questions}

        for result in self._results:
            question = question_map.get(result.question_id)
            if question:
                category = question.metadata.get("category", "general")
                if category not in category_results:
                    category_results[category] = []
                category_results[category].append(result.correct)

        return {
            cat: sum(results) / len(results)
            for cat, results in category_results.items()
        }

    def get_report(self) -> dict[str, Any]:
        """Get a comprehensive benchmark report."""
        if not self._results:
            return {"error": "No results available"}

        accuracy = self.get_accuracy()
        total = len(self._results)
        correct = sum(1 for r in self._results if r.correct)
        incorrect = total - correct

        # Compute timing stats
        durations = [r.duration for r in self._results]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Compute confidence stats (for questions with confidence scores)
        confidences = [r.confidence for r in self._results if r.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "benchmark": "SIQA",
            "total_questions": total,
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": accuracy,
            "accuracy_pct": f"{accuracy * 100:.2f}%",
            "avg_duration_ms": avg_duration * 1000,
            "avg_confidence": avg_confidence,
            "category_accuracy": self.get_category_accuracy(),
        }

    def get_results(self) -> list[SIQAResult]:
        """Get all results."""
        return list(self._results)

    def get_dataset(self) -> Optional[SIQADataset]:
        """Get the loaded dataset."""
        return self._dataset

    def reset(self):
        """Reset results."""
        self._results = []
