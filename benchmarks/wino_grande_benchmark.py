"""
wino_grande_benchmark.py — Winograd Schema Benchmark.

Winograd Schema contains 440 pronoun resolution problems.
Each problem presents a sentence with a pronoun and two possible referents.
The task is to determine which referent the pronoun refers to.

Example:
  "The city councilmen refused the demonstrators a permit because they feared violence."
  Who feared violence? (a) city councilmen (b) demonstrators
  Answer: (a) city councilmen
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class WinogradProblem:
    """A single Winograd Schema problem."""
    problem_id: str
    sentence: str
    pronoun: str
    options: list[str]  # Two possible referents
    answer: int  # Index of correct option (0 or 1)
    explanation: str = ""
    difficulty: float = 0.5

    def to_dict(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "sentence": self.sentence,
            "pronoun": self.pronoun,
            "options": self.options,
            "answer": self.answer,
            "explanation": self.explanation,
            "difficulty": self.difficulty,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WinogradProblem":
        return cls(
            problem_id=data.get("problem_id", ""),
            sentence=data["sentence"],
            pronoun=data.get("pronoun", ""),
            options=data["options"],
            answer=int(data["answer"]),
            explanation=data.get("explanation", ""),
            difficulty=data.get("difficulty", 0.5),
        )


@dataclass
class ProblemResult:
    """Result of running a problem."""
    problem_id: str
    sentence: str
    pronoun: str
    options: list[str]
    correct_answer: int
    predicted_answer: int | None
    correct: bool
    output: str
    feedback: str

    def to_dict(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "sentence": self.sentence,
            "pronoun": self.pronoun,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "predicted_answer": self.predicted_answer,
            "correct": self.correct,
            "output": self.output,
            "feedback": self.feedback,
        }


@dataclass
class BenchmarkResult:
    """Result of running a benchmark."""
    total_problems: int
    correct: int
    incorrect: int
    accuracy: float
    results: list[ProblemResult]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_problems": self.total_problems,
            "correct": self.correct,
            "incorrect": self.incorrect,
            "accuracy": self.accuracy,
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
        }


# Built-in sample problems (representative of Winograd Schema)
SAMPLE_PROBLEMS = [
    WinogradProblem("win_001", "The city councilmen refused the demonstrators a permit because they feared violence.", "they", ["city councilmen", "demonstrators"], 0, "The councilmen are the ones who would fear violence from demonstrators", 0.3),
    WinogradProblem("win_002", "The city councilmen refused the demonstrators a permit because they advocated violence.", "they", ["city councilmen", "demonstrators"], 1, "The demonstrators are the ones advocating violence", 0.3),
    WinogradProblem("win_003", "The man couldn't lift his son because he was so weak.", "he", ["the man", "his son"], 1, "The son is the one who is weak", 0.4),
    WinogradProblem("win_004", "The man couldn't lift his son because he was so heavy.", "he", ["the man", "his son"], 1, "The son is the one who is heavy", 0.4),
    WinogradProblem("win_005", "I couldn't put the pot on the shelf because it was too high.", "it", ["the pot", "the shelf"], 1, "The shelf is too high", 0.3),
    WinogradProblem("win_006", "I couldn't put the pot on the shelf because it was too tall.", "it", ["the pot", "the shelf"], 0, "The pot is too tall", 0.3),
    WinogradProblem("win_007", "The large ball crashed right through the table because it was made of steel.", "it", ["the large ball", "the table"], 0, "The ball is made of steel", 0.5),
    WinogradProblem("win_008", "The large ball crashed right through the table because it was made of styrofoam.", "it", ["the large ball", "the table"], 1, "The table is made of styrofoam", 0.5),
    WinogradProblem("win_009", "John couldn't see the stage with Billy in front of him because he is so tall.", "he", ["John", "Billy"], 1, "Billy is the one who is tall", 0.4),
    WinogradProblem("win_010", "John couldn't see the stage with Billy in front of him because he is so short.", "he", ["John", "Billy"], 0, "John is the one who is short", 0.4),
    WinogradProblem("win_011", "The trophy doesn't fit into the brown suitcase because it's too small.", "it's", ["the trophy", "the brown suitcase"], 1, "The suitcase is too small", 0.5),
    WinogradProblem("win_012", "The trophy doesn't fit into the brown suitcase because it's too large.", "it's", ["the trophy", "the brown suitcase"], 0, "The trophy is too large", 0.5),
    WinogradProblem("win_013", "Tom threw his schoolbag to Ray after he reached the bottom of the stairs.", "he", ["Tom", "Ray"], 0, "Tom reached the bottom and then threw the bag", 0.6),
    WinogradProblem("win_014", "Tom threw his schoolbag to Ray after he reached the top of the stairs.", "he", ["Tom", "Ray"], 1, "Ray reached the top and Tom threw the bag to him", 0.6),
    WinogradProblem("win_015", "Although they ran at about the same speed, Sue beat Sally because she had such a good start.", "she", ["Sue", "Sally"], 0, "Sue had the good start", 0.5),
    WinogradProblem("win_016", "Although they ran at about the same speed, Sue beat Sally because she had such a bad start.", "she", ["Sue", "Sally"], 1, "Sally had the bad start", 0.5),
    WinogradProblem("win_017", "The painting in Mark's living room shows an oak tree. It is to the right of a bookcase.", "It", ["The painting", "an oak tree"], 0, "The painting is to the right of the bookcase", 0.4),
    WinogradProblem("win_018", "The painting in Mark's living room shows an oak tree. It is to the right of a chair.", "It", ["The painting", "an oak tree"], 0, "The painting is to the right of the chair", 0.4),
    WinogradProblem("win_019", "The fish ate the worm. It was hungry.", "It", ["The fish", "The worm"], 0, "The fish was hungry", 0.2),
    WinogradProblem("win_020", "The fish ate the worm. It was tasty.", "It", ["The fish", "The worm"], 1, "The worm was tasty", 0.2),
]


class WinogradBenchmark:
    """
    Winograd Schema Benchmark.
    """

    def __init__(self, problems: list[WinogradProblem] | None = None):
        self.problems: list[WinogradProblem] = problems or []
        self.results: list[ProblemResult] = []

    def load_problems(self, path: str | None = None) -> int:
        """
        Load problems from a JSON file or use built-in samples.

        Args:
            path: Path to JSON file with problems. If None, uses built-in samples.

        Returns:
            Number of problems loaded
        """
        if path and os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
            self.problems = [WinogradProblem.from_dict(p) for p in data]
        else:
            self.problems = list(SAMPLE_PROBLEMS)
        return len(self.problems)

    def get_problem(self, problem_id: str) -> WinogradProblem | None:
        """Get a problem by ID."""
        for p in self.problems:
            if p.problem_id == problem_id:
                return p
        return None

    def run_problem(
        self,
        problem: WinogradProblem,
        solver: Callable[[str, str, list[str]], int] | None = None,
    ) -> ProblemResult:
        """
        Run a single problem.

        Args:
            problem: The problem to solve
            solver: Optional solver function that takes (sentence, pronoun, options)
                    and returns the index of the chosen option (0 or 1).
                    If None, uses a simple heuristic.

        Returns:
            ProblemResult with the outcome
        """
        if solver is None:
            predicted_answer, output = self._default_solver(problem)
        else:
            predicted_answer = solver(problem.sentence, problem.pronoun, problem.options)
            output = f"Predicted: {predicted_answer}"

        correct = predicted_answer == problem.answer

        result = ProblemResult(
            problem_id=problem.problem_id,
            sentence=problem.sentence,
            pronoun=problem.pronoun,
            options=problem.options,
            correct_answer=problem.answer,
            predicted_answer=predicted_answer,
            correct=correct,
            output=output,
            feedback="Correct!" if correct else f"Incorrect. Expected {problem.options[problem.answer]}, got {problem.options[predicted_answer] if predicted_answer is not None else 'None'}",
        )
        self.results.append(result)
        return result

    def run_sample(
        self,
        n: int,
        solver: Callable[[str, str, list[str]], int] | None = None,
        random_seed: int | None = None,
    ) -> BenchmarkResult:
        """
        Run a sample of n problems.

        Args:
            n: Number of problems to run
            solver: Optional solver function
            random_seed: Optional random seed for reproducibility

        Returns:
            BenchmarkResult with all results
        """
        if random_seed is not None:
            random.seed(random_seed)

        sample = random.sample(self.problems, min(n, len(self.problems)))
        results = []
        for problem in sample:
            result = self.run_problem(problem, solver)
            results.append(result)

        correct = sum(1 for r in results if r.correct)
        incorrect = len(results) - correct
        accuracy = correct / len(results) if results else 0.0

        return BenchmarkResult(
            total_problems=len(results),
            correct=correct,
            incorrect=incorrect,
            accuracy=accuracy,
            results=results,
        )

    def run_all(
        self,
        solver: Callable[[str, str, list[str]], int] | None = None,
    ) -> BenchmarkResult:
        """Run all problems."""
        results = []
        for problem in self.problems:
            result = self.run_problem(problem, solver)
            results.append(result)

        correct = sum(1 for r in results if r.correct)
        incorrect = len(results) - correct
        accuracy = correct / len(results) if results else 0.0

        return BenchmarkResult(
            total_problems=len(results),
            correct=correct,
            incorrect=incorrect,
            accuracy=accuracy,
            results=results,
        )

    def get_accuracy(self) -> dict[str, Any]:
        """
        Get accuracy metrics from stored results.

        Returns:
            Dict with accuracy metrics
        """
        if not self.results:
            return {
                "total_problems": 0,
                "correct": 0,
                "incorrect": 0,
                "accuracy": 0.0,
            }

        correct = sum(1 for r in self.results if r.correct)
        incorrect = len(self.results) - correct
        accuracy = correct / len(self.results)

        return {
            "total_problems": len(self.results),
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": accuracy,
        }

    def _default_solver(self, problem: WinogradProblem) -> tuple[int | None, str]:
        """
        Default solver using simple heuristics.

        This is a placeholder that uses basic pattern matching.
        A real implementation would use an LLM.
        """
        sentence = problem.sentence.lower()
        options = [opt.lower() for opt in problem.options]

        # Heuristic: check for common patterns
        # "because" clauses often refer to the subject of the main clause
        if "because" in sentence:
            # The subject of the main clause is usually the answer
            # This is a very rough heuristic
            return 0, "Heuristic: subject of main clause"

        # "after" clauses often refer to the object
        if "after" in sentence:
            return 1, "Heuristic: object of clause"

        # "although" clauses often refer to the subject
        if "although" in sentence:
            return 0, "Heuristic: subject of main clause"

        # Default: return 0
        return 0, "Default: first option"

    def clear_results(self) -> None:
        """Clear all stored results."""
        self.results.clear()

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics."""
        if not self.results:
            return {"total": 0}

        correct = sum(1 for r in self.results if r.correct)
        return {
            "total": len(self.results),
            "correct": correct,
            "incorrect": len(self.results) - correct,
            "accuracy": correct / len(self.results),
        }

    def get_report(self) -> dict[str, Any]:
        """Get full report including accuracy, statistics, and per-problem results."""
        accuracy = self.get_accuracy()
        stats = self.get_statistics()
        return {
            "accuracy": accuracy,
            "statistics": stats,
            "total_problems": len(self.problems),
            "results_count": len(self.results),
            "results": [r.to_dict() for r in self.results],
        }
