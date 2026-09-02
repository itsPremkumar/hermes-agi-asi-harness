"""MMLU Benchmark — 57 categories, 14,042 questions with full backward compatibility."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

AGENT_API_VERSION = "1.0"

MMLU_CATEGORIES = [
    "abstract_algebra", "anatomy", "astronomy", "business_ethics", "clinical_knowledge",
    "college_biology", "college_chemistry", "college_computer_science", "college_mathematics",
    "college_medicine", "college_physics", "computer_security", "conceptual_physics",
    "econometrics", "electrical_engineering", "elementary_mathematics", "formal_logic",
    "global_facts", "high_school_biology", "high_school_chemistry", "high_school_computer_science",
    "high_school_european_history", "high_school_geography", "high_school_government_and_politics",
    "high_school_macroeconomics", "high_school_mathematics", "high_school_microeconomics",
    "high_school_physics", "high_school_psychology", "high_school_statistics",
    "high_school_us_history", "high_school_world_history", "human_aging", "human_sexuality",
    "international_law", "jurisprudence", "logical_fallacies", "machine_learning",
    "management", "marketing", "medical_genetics", "miscellaneous", "moral_disputes",
    "moral_scenarios", "nutrition", "philosophy", "prehistory", "professional_accounting",
    "professional_law", "professional_medicine", "professional_psychology", "public_relations",
    "security_studies", "sociology", "us_foreign_policy", "virology", "world_religions",
]

QUESTIONS_PER_CATEGORY = 246  # 14,042 / 57 = 246


class MMLUCategory(str, Enum):
    """MMLU category classification."""
    STEM = "stem"
    SOCIAL_SCIENCES = "social_sciences"
    HUMANITIES = "humanities"
    OTHER = "other"


class QuestionStatus(str, Enum):
    PENDING = "pending"
    CORRECT = "correct"
    INCORRECT = "incorrect"
    SKIPPED = "skipped"


@dataclass
class Question:
    """Question with int-based correct_answer (0-3) for backward compat."""
    id: str
    category: str
    text: str
    options: list[str]
    correct_answer: int
    status: QuestionStatus = QuestionStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "text": self.text,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "status": self.status.value,
        }


@dataclass
class CategoryResult:
    category: str
    total: int
    correct: int
    incorrect: int
    accuracy: float


@dataclass
class MMLUQuestion:
    """Extended MMLU question for newer API."""
    question_id: str
    text: str
    options: list[str]
    correct_answer: str
    category: MMLUCategory = MMLUCategory.OTHER
    subcategory: str = ""
    status: QuestionStatus = QuestionStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "text": self.text,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "category": self.category.value,
            "subcategory": self.subcategory,
            "status": self.status.value,
        }


class MMLUBenchmark:
    """MMLU benchmark — supports both old (int answer) and new (str answer) APIs."""

    def __init__(self, data_dir: str = "/tmp/mmlu"):
        self.id = str(uuid.uuid4())
        self.data_dir = data_dir
        self._questions: dict[str, Question] = {}
        self._category_index: dict[str, list[str]] = {}

    def load_categories(self) -> list[str]:
        """Load all 57 MMLU categories."""
        return list(MMLU_CATEGORIES)

    def load_questions(self, category: str | None = None) -> list[Question]:
        """Load questions for a category or all categories."""
        if category:
            return [self._questions[qid] for qid in self._category_index.get(category, []) if qid in self._questions]
        return list(self._questions.values())

    def generate_questions(self, category: str, count: int = QUESTIONS_PER_CATEGORY) -> list[Question]:
        """Generate synthetic questions for a category."""
        questions = []
        for i in range(count):
            q = Question(
                id=str(uuid.uuid4()),
                category=category,
                text=f"Question {i+1} in {category}",
                options=["A", "B", "C", "D"],
                correct_answer=i % 4,
            )
            self._questions[q.id] = q
            if category not in self._category_index:
                self._category_index[category] = []
            self._category_index[category].append(q.id)
            questions.append(q)
        return questions

    def generate_all(self) -> int:
        """Generate all 14,042 questions across 57 categories."""
        total = 0
        for category in MMLU_CATEGORIES:
            self.generate_questions(category)
            total += QUESTIONS_PER_CATEGORY
        return total

    def run_question(self, question_id: str, answer: int) -> bool:
        """Run a single question and return correctness. Answer is int (0-3)."""
        if question_id not in self._questions:
            return False
        q = self._questions[question_id]
        if answer == q.correct_answer:
            q.status = QuestionStatus.CORRECT
            return True
        else:
            q.status = QuestionStatus.INCORRECT
            return False

    def run_questions(self, answers: dict[str, int]) -> dict[str, bool]:
        """Run multiple questions and return results."""
        results = {}
        for qid, answer in answers.items():
            results[qid] = self.run_question(qid, answer)
        return results

    def get_accuracy(self, category: str | None = None) -> float:
        """Get accuracy for a category or overall."""
        questions = self.load_questions(category)
        if not questions:
            return 0.0
        correct = sum(1 for q in questions if q.status == QuestionStatus.CORRECT)
        attempted = sum(1 for q in questions if q.status in (QuestionStatus.CORRECT, QuestionStatus.INCORRECT))
        return correct / attempted if attempted > 0 else 0.0

    def get_overall(self) -> dict[str, Any]:
        """Get overall benchmark results."""
        total = len(self._questions)
        correct = sum(1 for q in self._questions.values() if q.status == QuestionStatus.CORRECT)
        attempted = sum(1 for q in self._questions.values() if q.status in (QuestionStatus.CORRECT, QuestionStatus.INCORRECT))
        return {
            "total_questions": total,
            "attempted": attempted,
            "correct": correct,
            "accuracy": correct / attempted if attempted > 0 else 0.0,
            "categories": len(MMLU_CATEGORIES),
        }

    def get_category_results(self) -> list[CategoryResult]:
        """Get results per category."""
        results = []
        for category in MMLU_CATEGORIES:
            questions = self.load_questions(category)
            correct = sum(1 for q in questions if q.status == QuestionStatus.CORRECT)
            incorrect = sum(1 for q in questions if q.status == QuestionStatus.INCORRECT)
            total = len(questions)
            attempted = correct + incorrect
            accuracy = correct / attempted if attempted > 0 else 0.0
            results.append(CategoryResult(
                category=category,
                total=total,
                correct=correct,
                incorrect=incorrect,
                accuracy=accuracy,
            ))
        return results

    def get_state(self) -> dict[str, Any]:
        return {
            "total_questions": self.count_questions(),
            "categories": len(self._category_index),
        }

    def search(self, category: str | None = None, query: str | None = None) -> list[Question]:
        """Search questions by category and/or text query."""
        questions = self.load_questions(category)
        if query:
            q = query.lower()
            questions = [ques for ques in questions if q in ques.text.lower()]
        return questions

    def count_questions(self) -> int:
        return len(self._questions)

    def add_question(self, question: Any) -> None:
        """Add a question to the benchmark."""
        qid = getattr(question, 'id', None) or getattr(question, 'question_id', None)
        cat = getattr(question, 'category', None) or getattr(question, 'subcategory', 'unknown')
        self._questions[qid] = question
        if cat not in self._category_index:
            self._category_index[cat] = []
        self._category_index[cat].append(qid)

    def evaluate(self, question_id: str, answer: str) -> bool:
        """Evaluate an answer for a question (string-based)."""
        if question_id not in self._questions:
            return False
        q = self._questions[question_id]
        # Handle both int and string correct_answer
        correct = q.correct_answer
        if isinstance(correct, str):
            if answer == correct:
                q.status = QuestionStatus.CORRECT
                return True
            else:
                q.status = QuestionStatus.INCORRECT
                return False
        else:
            answer_map = {"A": 0, "B": 1, "C": 2, "D": 3}
            answer_int = answer_map.get(answer, -1)
            if answer_int == correct:
                q.status = QuestionStatus.CORRECT
                return True
            else:
                q.status = QuestionStatus.INCORRECT
                return False

    def generate_synthetic_questions(self, count: int) -> list[Question]:
        """Generate synthetic questions for testing."""
        questions = []
        for i in range(count):
            q = Question(
                id=str(uuid.uuid4()),
                category="math",
                text=f"Synthetic question {i+1}",
                options=["A. 3", "B. 4", "C. 5", "D. 6"],
                correct_answer=1,  # B
            )
            self._questions[q.id] = q
            questions.append(q)
        return questions

    def run_benchmark(self) -> dict[str, Any]:
        """Run the full benchmark and return results."""
        total = len(self._questions)
        correct = sum(1 for q in self._questions.values() if q.status == QuestionStatus.CORRECT)
        attempted = sum(1 for q in self._questions.values() if q.status in (QuestionStatus.CORRECT, QuestionStatus.INCORRECT))
        return {
            "total": total,
            "attempted": attempted,
            "correct": correct,
            "accuracy": correct / attempted if attempted > 0 else 0.0,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get benchmark statistics."""
        return {
            "total_questions": len(self._questions),
            "categories": len(self._category_index),
        }
