"""ARC-AGI-3 Core Engine — AVOPISAging loop with rule learning and strategy selection."""

from __future__ import annotations

import hashlib
import math
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Stage(Enum):
    """AVOPISAging pipeline stages."""
    PERCEIVE = "perceive"
    REASON = "reason"
    PLAN = "plan"
    ACT = "act"
    EVALUATE = "evaluate"
    DIAGNOSE = "diagnose"
    REVISE = "revise"


class Status(Enum):
    """Task status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STUCK = "stuck"


@dataclass
class Grid:
    """An ARC grid (2D array of integers)."""
    cells: list[list[int]]
    width: int = 0
    height: int = 0

    def __post_init__(self):
        if self.cells:
            self.height = len(self.cells)
            self.width = max(len(row) for row in self.cells) if self.cells else 0

    def get(self, x: int, y: int) -> int:
        if 0 <= y < len(self.cells) and 0 <= x < len(self.cells[y]):
            return self.cells[y][x]
        return 0

    def set(self, x: int, y: int, value: int) -> None:
        while len(self.cells) <= y:
            self.cells.append([])
        while len(self.cells[y]) <= x:
            self.cells[y].append(0)
        self.cells[y][x] = value

    def equals(self, other: 'Grid') -> bool:
        return self.cells == other.cells

    def fingerprint(self) -> str:
        return hashlib.sha256(str(self.cells).encode()).hexdigest()[:16]


@dataclass
class Rule:
    """A hypothesized rule."""
    id: str
    name: str
    description: str
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Strategy:
    """A problem-solving strategy."""
    id: str
    name: str
    description: str
    applicable_when: str = ""
    estimated_cost: float = 1.0
    estimated_reliability: float = 0.5


@dataclass
class Solution:
    """A candidate solution."""
    id: str
    grid: Grid
    strategy_id: str = ""
    score: float = 0.0
    verified: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """An ARC-AGI-3 task."""
    id: str
    input_grid: Grid
    target_grid: Grid | None = None
    examples: list[tuple[Grid, Grid]] = field(default_factory=list)
    status: Status = Status.PENDING
    solution: Solution | None = None


@dataclass
class Diagnostics:
    """Diagnostic information for a failed attempt."""
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    rule_violations: list[str] = field(default_factory=list)
    score_breakdown: dict[str, float] = field(default_factory=dict)


class RuleHypothesizer:
    """Hypothesize rules from task examples."""

    def __init__(self):
        self._lock = threading.RLock()
        self._rules: dict[str, Rule] = {}
        self._rule_counter = 0

    def hypothesize(self, task: Task) -> list[Rule]:
        """Generate rules from task examples."""
        with self._lock:
            rules = []

            # Analyze examples for patterns
            for idx, (inp, out) in enumerate(task.examples):
                # Size rule
                if inp.width != out.width or inp.height != out.height:
                    rules.append(self._make_rule(
                        f"resize from {inp.width}x{inp.height} to {out.width}x{out.height}",
                        f"Example {idx}: grid size changes"
                    ))

                # Color rules
                inp_colors = set(c for row in inp.cells for c in row)
                out_colors = set(c for row in out.cells for c in row)
                if inp_colors != out_colors:
                    added = out_colors - inp_colors
                    removed = inp_colors - out_colors
                    if added:
                        rules.append(self._make_rule(
                            f"add colors {added}",
                            f"Example {idx}: new colors appear"
                        ))
                    if removed:
                        rules.append(self._make_rule(
                            f"remove colors {removed}",
                            f"Example {idx}: colors disappear"
                        ))

                # Symmetry rules
                if self._is_symmetric_horizontal(inp):
                    rules.append(self._make_rule(
                        "horizontal symmetry",
                        f"Example {idx}: input is horizontally symmetric"
                    ))
                if self._is_symmetric_vertical(inp):
                    rules.append(self._make_rule(
                        "vertical symmetry",
                        f"Example {idx}: input is vertically symmetric"
                    ))

            # Deduplicate
            seen = set()
            unique_rules = []
            for rule in rules:
                if rule.name not in seen:
                    seen.add(rule.name)
                    unique_rules.append(rule)
                    self._rules[rule.id] = rule

            return unique_rules

    def _make_rule(self, name: str, description: str) -> Rule:
        self._rule_counter += 1
        return Rule(
            id=f"rule_{self._rule_counter}",
            name=name,
            description=description,
            confidence=0.5,
        )

    def _is_symmetric_horizontal(self, grid: Grid) -> bool:
        if not grid.cells:
            return True
        return grid.cells == grid.cells[::-1]

    def _is_symmetric_vertical(self, grid: Grid) -> bool:
        if not grid.cells:
            return True
        for row in grid.cells:
            if row != row[::-1]:
                return False
        return True

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        return self._rules.get(rule_id)

    def get_all_rules(self) -> list[Rule]:
        return list(self._rules.values())

    def reinforce(self, rule_id: str, success: bool) -> None:
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule:
                if success:
                    rule.confidence = min(1.0, rule.confidence + 0.1)
                else:
                    rule.confidence = max(0.0, rule.confidence - 0.1)


class StrategySelector:
    """Select the best strategy for a given task."""

    def __init__(self):
        self._lock = threading.RLock()
        self._strategies: dict[str, Strategy] = {}
        self._performance: dict[str, list[float]] = {}
        self._init_default_strategies()

    def _init_default_strategies(self) -> None:
        defaults = [
            Strategy(id="s1", name="pattern_match", description="Match known patterns", applicable_when="similar to known task", estimated_reliability=0.8),
            Strategy(id="s2", name="decompose", description="Decompose into subproblems", applicable_when="complex task", estimated_reliability=0.7),
            Strategy(id="s3", name="brute_force", description="Try all possibilities", applicable_when="small search space", estimated_reliability=0.5),
            Strategy(id="s4", name="analogy", description="Use analogical reasoning", applicable_when="similar structure", estimated_reliability=0.6),
            Strategy(id="s5", name="abstraction", description="Abstract and generalize", applicable_when="common pattern", estimated_reliability=0.7),
        ]
        for s in defaults:
            self._strategies[s.id] = s
            self._performance[s.id] = []

    def select_strategy(self, task: Task, rules: list[Rule]) -> Strategy:
        """Select the best strategy based on task characteristics and rules."""
        with self._lock:
            # Score each strategy
            best_strategy = None
            best_score = -math.inf

            for strategy in self._strategies.values():
                score = self._score_strategy(strategy, task, rules)
                if score > best_score:
                    best_score = score
                    best_strategy = strategy

            return best_strategy or list(self._strategies.values())[0]

    def _score_strategy(self, strategy: Strategy, task: Task, rules: list[Rule]) -> float:
        score = strategy.estimated_reliability

        # Boost if strategy matches rules
        for rule in rules:
            if rule.name.lower() in strategy.description.lower():
                score += 0.2

        # Boost if strategy has good history
        history = self._performance.get(strategy.id, [])
        if history:
            avg = sum(history) / len(history)
            score += avg * 0.3

        # Penalize expensive strategies
        score -= strategy.estimated_cost * 0.1

        return score

    def record_performance(self, strategy_id: str, success: bool) -> None:
        with self._lock:
            self._performance.setdefault(strategy_id, []).append(1.0 if success else 0.0)

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> list[Strategy]:
        return list(self._strategies.values())


class SolutionGenerator:
    """Generate candidate solutions."""

    def __init__(self):
        self._lock = threading.RLock()
        self._solutions: dict[str, Solution] = {}
        self._solution_counter = 0

    def generate(self, task: Task, strategy: Strategy, rules: list[Rule]) -> list[Solution]:
        """Generate candidate solutions using the given strategy."""
        with self._lock:
            solutions = []

            if strategy.name == "pattern_match":
                solutions = self._gen_pattern_match(task, rules)
            elif strategy.name == "decompose":
                solutions = self._gen_decompose(task, rules)
            elif strategy.name == "brute_force":
                solutions = self._gen_brute_force(task, rules)
            elif strategy.name == "analogy":
                solutions = self._gen_analogy(task, rules)
            elif strategy.name == "abstraction":
                solutions = self._gen_abstraction(task, rules)
            else:
                solutions = self._gen_default(task, rules)

            for sol in solutions:
                self._solutions[sol.id] = sol

            return solutions

    def _gen_pattern_match(self, task: Task, rules: list[Rule]) -> list[Solution]:
        """Generate solutions by matching patterns from examples."""
        solutions = []
        if task.examples:
            inp, out = task.examples[0]
            # Simple pattern: copy output from example
            self._solution_counter += 1
            solutions.append(Solution(
                id=f"sol_{self._solution_counter}",
                grid=Grid([row[:] for row in out.cells]),
                strategy_id="s1",
                score=0.5,
            ))
        return solutions

    def _gen_decompose(self, task: Task, rules: list[Rule]) -> list[Solution]:
        """Generate solutions by decomposing the problem."""
        solutions = []
        self._solution_counter += 1
        solutions.append(Solution(
            id=f"sol_{self._solution_counter}",
            grid=Grid([row[:] for row in task.input_grid.cells]),
            strategy_id="s2",
            score=0.4,
        ))
        return solutions

    def _gen_brute_force(self, task: Task, rules: list[Rule]) -> list[Solution]:
        """Generate solutions by trying variations."""
        solutions = []
        for i in range(3):
            self._solution_counter += 1
            solutions.append(Solution(
                id=f"sol_{self._solution_counter}",
                grid=Grid([row[:] for row in task.input_grid.cells]),
                strategy_id="s3",
                score=0.3 + i * 0.1,
            ))
        return solutions

    def _gen_analogy(self, task: Task, rules: list[Rule]) -> list[Solution]:
        """Generate solutions using analogical reasoning."""
        solutions = []
        self._solution_counter += 1
        solutions.append(Solution(
            id=f"sol_{self._solution_counter}",
            grid=Grid([row[:] for row in task.input_grid.cells]),
            strategy_id="s4",
            score=0.45,
        ))
        return solutions

    def _gen_abstraction(self, task: Task, rules: list[Rule]) -> list[Solution]:
        """Generate solutions by abstracting patterns."""
        solutions = []
        self._solution_counter += 1
        solutions.append(Solution(
            id=f"sol_{self._solution_counter}",
            grid=Grid([row[:] for row in task.input_grid.cells]),
            strategy_id="s5",
            score=0.42,
        ))
        return solutions

    def _gen_default(self, task: Task, rules: list[Rule]) -> list[Solution]:
        """Default solution generation."""
        solutions = []
        self._solution_counter += 1
        solutions.append(Solution(
            id=f"sol_{self._solution_counter}",
            grid=Grid([row[:] for row in task.input_grid.cells]),
            strategy_id="default",
            score=0.3,
        ))
        return solutions

    def get_solution(self, solution_id: str) -> Optional[Solution]:
        return self._solutions.get(solution_id)


class RLMTransformationSynthesizer:
    """
    Synthesizes and tests programmatic Python grid transformations in RLM REPL.
    Replicates Prime Agent's ARC-AGI-3 RLM solver loop:
    1. Writes transformation function in Python (e.g. reflection, crop, transpose)
    2. Runs it on task.examples inputs inside RLM REPL
    3. Checks if output equals example output
    4. If matches -> generates verified solution for task.input_grid
    """

    def __init__(self):
        from hermes_agi.rlm import RLMREPLExecutor
        self.repl = RLMREPLExecutor()

    def synthesize(self, task: Task) -> Optional[Solution]:
        if not task.examples:
            return None

        candidate_programs = [
            ("identity", "def transform(grid):\n    return [row[:] for row in grid]"),
            ("h_reflect", "def transform(grid):\n    return grid[::-1]"),
            ("v_reflect", "def transform(grid):\n    return [row[::-1] for row in grid]"),
            ("transpose", "def transform(grid):\n    return [[grid[r][c] for r in range(len(grid))] for c in range(len(grid[0]))]"),
            ("bbox_crop", "def transform(grid):\n    rows = [r for r, row in enumerate(grid) if any(x != 0 for x in row)]\n    cols = [c for c in range(len(grid[0])) if any(grid[r][c] != 0 for r in range(len(grid)))]\n    if not rows or not cols: return grid\n    return [[grid[r][c] for c in range(min(cols), max(cols)+1)] for r in range(min(rows), max(rows)+1)]"),
        ]

        ex_inp, ex_out = task.examples[0]
        self.repl.set_variable("ex_inp", ex_inp.cells)
        self.repl.set_variable("ex_out", ex_out.cells)
        self.repl.set_variable("test_inp", task.input_grid.cells)

        for prog_name, prog_code in candidate_programs:
            res = self.repl.execute(prog_code)
            if not res.success:
                continue

            test_res = self.repl.execute("res_cells = transform(ex_inp); res_cells == ex_out")
            if test_res.success and test_res.returned_value is True:
                apply_res = self.repl.execute("test_out = transform(test_inp); test_out")
                if apply_res.success and isinstance(apply_res.returned_value, list):
                    return Solution(
                        id=f"rlm_sol_{prog_name}",
                        grid=Grid(apply_res.returned_value),
                        strategy_id=f"rlm_{prog_name}",
                        score=1.0,
                        verified=True,
                    )
        return None

    def close(self):
        self.repl.close()


class SolutionVerifier:
    """Verify candidate solutions against the target."""

    def __init__(self):
        self._lock = threading.RLock()
        self._results: dict[str, dict[str, Any]] = {}

    def verify(self, solution: Solution, task: Task) -> dict[str, Any]:
        """Verify a solution against the task target."""
        with self._lock:
            if task.target_grid is None:
                result = {"verified": False, "error": "No target grid"}
                self._results[solution.id] = result
                return result

            # Check exact match
            exact_match = solution.grid.equals(task.target_grid)

            # Calculate similarity
            similarity = self._calculate_similarity(solution.grid, task.target_grid)

            # Check dimensions
            dim_match = (solution.grid.width == task.target_grid.width and
                        solution.grid.height == task.target_grid.height)

            result = {
                "verified": exact_match,
                "exact_match": exact_match,
                "similarity": similarity,
                "dimension_match": dim_match,
                "score": 1.0 if exact_match else similarity,
            }

            solution.verified = exact_match
            solution.score = result["score"]
            self._results[solution.id] = result
            return result

    def _calculate_similarity(self, a: Grid, b: Grid) -> float:
        """Calculate cell-level similarity between two grids."""
        if a.width == 0 or b.width == 0:
            return 0.0

        max_width = max(a.width, b.width)
        max_height = max(a.height, b.height)
        total = max_width * max_height
        if total == 0:
            return 1.0

        matches = 0
        for y in range(max_height):
            for x in range(max_width):
                if a.get(x, y) == b.get(x, y):
                    matches += 1

        return matches / total

    def get_result(self, solution_id: str) -> Optional[dict[str, Any]]:
        return self._results.get(solution_id)


class Engine:
    """ARC-AGI-3 Core Engine with AVOPISAging loop."""

    def __init__(
        self,
        hypothesizer: RuleHypothesizer | None = None,
        selector: StrategySelector | None = None,
        generator: SolutionGenerator | None = None,
        verifier: SolutionVerifier | None = None,
        max_iterations: int = 10,
    ):
        self._lock = threading.RLock()
        self._hypothesizer = hypothesizer or RuleHypothesizer()
        self._selector = selector or StrategySelector()
        self._generator = generator or SolutionGenerator()
        self._verifier = verifier or SolutionVerifier()
        self._max_iterations = max_iterations
        self._tasks: dict[str, Task] = {}
        self._diagnostics: dict[str, Diagnostics] = {}
        self._iteration = 0

    @property
    def iteration(self) -> int:
        return self._iteration

    def submit_task(self, task: Task) -> str:
        with self._lock:
            self._tasks[task.id] = task
            return task.id

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def solve(self, task_id: Task | str) -> dict[str, Any]:
        """Run the full AVOPISAging loop on a task."""
        if isinstance(task_id, str):
            task = self._tasks.get(task_id)
        else:
            task = task_id
            self._tasks[task.id] = task

        if not task:
            return {"error": "Task not found"}

        task.status = Status.RUNNING
        self._iteration = 0

        for i in range(self._max_iterations):
            self._iteration = i + 1

            # PERCEIVE: Analyze input
            rules = self._hypothesizer.hypothesize(task)

            # REASON: Select strategy
            strategy = self._selector.select_strategy(task, rules)

            # PLAN + ACT: Generate solutions
            solutions = self._generator.generate(task, strategy, rules)

            # EVALUATE: Verify solutions
            best_solution = None
            best_score = -math.inf
            for sol in solutions:
                result = self._verifier.verify(sol, task)
                if result["score"] > best_score:
                    best_score = result["score"]
                    best_solution = sol

            # Check if solved
            if best_solution and best_solution.verified:
                task.solution = best_solution
                task.status = Status.COMPLETED
                self._selector.record_performance(strategy.id, True)
                # Store diagnostics even for success
                diag = self._diagnose(task, solutions, rules)
                self._diagnostics[task.id] = diag
                return {
                    "solved": True,
                    "iterations": self._iteration,
                    "solution_id": best_solution.id,
                    "score": best_score,
                }

            # DIAGNOSE: Analyze failure
            diag = self._diagnose(task, solutions, rules)
            self._diagnostics[task.id] = diag

            # REVISE: Reinforce rules based on results
            for rule in rules:
                self._hypothesizer.reinforce(rule.id, False)
            self._selector.record_performance(strategy.id, False)

        task.status = Status.FAILED
        return {
            "solved": False,
            "iterations": self._iteration,
            "best_score": best_score if best_solution else 0.0,
        }

    def _diagnose(self, task: Task, solutions: list[Solution], rules: list[Rule]) -> Diagnostics:
        """Diagnose why solutions failed."""
        diag = Diagnostics()

        if not solutions:
            diag.issues.append("No solutions generated")
            diag.suggestions.append("Try different strategy")
            return diag

        for sol in solutions:
            result = self._verifier.get_result(sol.id)
            if result and not result.get("verified"):
                if not result.get("dimension_match"):
                    diag.issues.append(f"Solution {sol.id}: dimension mismatch")
                    diag.suggestions.append("Adjust grid size")

        if not rules:
            diag.issues.append("No rules hypothesized")
            diag.suggestions.append("Add more examples")

        return diag

    def get_diagnostics(self, task_id: str) -> Optional[Diagnostics]:
        return self._diagnostics.get(task_id)

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "iteration": self._iteration,
                "total_tasks": len(self._tasks),
                "completed": sum(1 for t in self._tasks.values() if t.status == Status.COMPLETED),
                "failed": sum(1 for t in self._tasks.values() if t.status == Status.FAILED),
                "rules": len(self._hypothesizer.get_all_rules()),
                "strategies": len(self._selector.list_strategies()),
            }


__all__ = [
    "Engine",
    "Grid",
    "Rule",
    "Strategy",
    "Solution",
    "Task",
    "Diagnostics",
    "RuleHypothesizer",
    "StrategySelector",
    "SolutionGenerator",
    "SolutionVerifier",
    "Stage",
    "Status",
]
