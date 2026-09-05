"""Full Evaluation Suite — unified benchmark evaluation and reporting."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvalCategory(Enum):
    CODE = "code"
    REASONING = "reasoning"
    SAFETY = "safety"
    GENERAL = "general"


@dataclass
class EvalResult:
    """Result of evaluating a benchmark."""
    benchmark: str
    category: str
    total: int
    passed: int
    failed: int
    score: float
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalReport:
    """Full evaluation report."""
    timestamp: float
    overall_score: float
    total_problems: int
    total_passed: int
    total_failed: int
    category_scores: dict[str, float]
    results: list[EvalResult]
    metadata: dict[str, Any] = field(default_factory=dict)


class EvaluationSuite:
    """Full evaluation suite — run all benchmarks and generate reports."""

    def __init__(self):
        self._lock = threading.RLock()
        self._benchmarks: dict[str, Any] = {}
        self._results: list[EvalResult] = []
        self._reports: list[EvalReport] = []

    def register_benchmark(self, name: str, benchmark: Any, category: str = "general") -> None:
        """Register a benchmark for evaluation."""
        with self._lock:
            self._benchmarks[name] = {"benchmark": benchmark, "category": category}

    def run_all_benchmarks(self) -> list[EvalResult]:
        """Run all registered benchmarks."""
        with self._lock:
            results = []
            for name, info in self._benchmarks.items():
                start = time.time()
                benchmark = info["benchmark"]
                category = info["category"]

                try:
                    # Load and run
                    if hasattr(benchmark, 'load_problems'):
                        benchmark.load_problems()
                    if hasattr(benchmark, 'run_all'):
                        benchmark.run_all()
                    elif hasattr(benchmark, 'run_sample'):
                        benchmark.run_sample()

                    # Get pass rate
                    if hasattr(benchmark, 'get_pass_rate'):
                        rate = benchmark.get_pass_rate()
                        total = rate.get("total", 0)
                        passed = rate.get("passed", 0)
                        failed = rate.get("failed", 0)
                        score = rate.get("pass_rate", 0.0)
                    elif hasattr(benchmark, 'get_resolution_rate'):
                        rate = benchmark.get_resolution_rate()
                        total = rate.get("total", 0)
                        passed = rate.get("resolved", 0)
                        failed = rate.get("unresolved", 0)
                        score = rate.get("resolution_rate", 0.0)
                    else:
                        total = passed = failed = 0
                        score = 0.0

                except Exception:
                    total = passed = failed = 0
                    score = 0.0

                duration = (time.time() - start) * 1000
                result = EvalResult(
                    benchmark=name,
                    category=category,
                    total=total,
                    passed=passed,
                    failed=failed,
                    score=score,
                    duration_ms=duration,
                )
                results.append(result)

            self._results = results
            return results

    def get_overall_score(self) -> float:
        """Get overall score across all benchmarks."""
        with self._lock:
            if not self._results:
                return 0.0
            total_problems = sum(r.total for r in self._results)
            if total_problems == 0:
                return 0.0
            total_passed = sum(r.passed for r in self._results)
            return total_passed / total_problems

    def get_category_scores(self) -> dict[str, float]:
        """Get scores grouped by category."""
        with self._lock:
            categories: dict[str, list[float]] = {}
            for result in self._results:
                categories.setdefault(result.category, []).append(result.score)

            return {
                cat: sum(scores) / len(scores) if scores else 0.0
                for cat, scores in categories.items()
            }

    def generate_report(self) -> EvalReport:
        """Generate a full evaluation report."""
        with self._lock:
            if not self._results:
                return EvalReport(
                    timestamp=time.time(),
                    overall_score=0.0,
                    total_problems=0,
                    total_passed=0,
                    total_failed=0,
                    category_scores={},
                    results=[],
                )

            total_problems = sum(r.total for r in self._results)
            total_passed = sum(r.passed for r in self._results)
            total_failed = sum(r.failed for r in self._results)
            overall_score = total_passed / total_problems if total_problems else 0.0

            report = EvalReport(
                timestamp=time.time(),
                overall_score=overall_score,
                total_problems=total_problems,
                total_passed=total_passed,
                total_failed=total_failed,
                category_scores=self.get_category_scores(),
                results=list(self._results),
                metadata={
                    "num_benchmarks": len(self._results),
                    "benchmarks": [r.benchmark for r in self._results],
                },
            )
            self._reports.append(report)
            return report

    def get_results(self) -> list[EvalResult]:
        return list(self._results)

    def get_reports(self) -> list[EvalReport]:
        return list(self._reports)

    def get_benchmark_names(self) -> list[str]:
        return list(self._benchmarks.keys())

    def clear(self) -> None:
        with self._lock:
            self._results.clear()


def build_default_evaluation_suite() -> EvaluationSuite:
    """Build evaluation suite with all default benchmarks."""
    suite = EvaluationSuite()

    # Import and register all benchmarks
    try:
        from benchmark.human_eval_benchmark import HumanEvalBenchmark
        suite.register_benchmark("HumanEval", HumanEvalBenchmark(), "code")
    except ImportError:
        pass

    try:
        from benchmark.mbpp_benchmark import MBPPBenchmark
        suite.register_benchmark("MBPP", MBPPBenchmark(), "code")
    except ImportError:
        pass

    try:
        from benchmark.hellaswag_benchmark import HellaSwagBenchmark
        suite.register_benchmark("HellaSwag", HellaSwagBenchmark(), "reasoning")
    except ImportError:
        pass

    try:
        from benchmark.boolq_benchmark import BoolQBenchmark
        suite.register_benchmark("BoolQ", BoolQBenchmark(), "reasoning")
    except ImportError:
        pass

    try:
        from benchmark.swe_bench_pro_benchmark import SWEBenchPro
        suite.register_benchmark("SWE-bench Pro", SWEBenchPro(), "code")
    except ImportError:
        pass

    return suite


__all__ = [
    "EvaluationSuite",
    "EvalResult",
    "EvalReport",
    "EvalCategory",
    "build_default_evaluation_suite",
]
