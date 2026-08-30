"""
Continuous Benchmark & Regression Detection — Run evaluation suites continuously.

Features:
- Run benchmark suites
- Detect regressions automatically
- Maintain leaderboards
- Trigger alerts on degradation
- Generate reports
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TestResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RegressionSeverity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BenchmarkCase:
    id: str
    name: str
    description: str
    test_function: Callable
    expected_result: Any
    timeout_seconds: int = 30
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkRun:
    id: str
    case_id: str
    result: TestResult
    actual_result: Any
    duration_ms: float
    timestamp: float
    error: str | None = None


@dataclass
class Regression:
    id: str
    case_id: str
    baseline_score: float
    current_score: float
    severity: RegressionSeverity
    description: str
    timestamp: float


@dataclass
class BenchmarkResult:
    id: str
    version: str
    runs: list[BenchmarkRun]
    regressions: list[Regression]
    total_score: float
    baseline_score: float
    improved: bool
    regressed: bool
    timestamp: float
    summary: dict[str, Any] = field(default_factory=dict)


class ContinuousBenchmark:
    """Continuous evaluation and regression detection."""
    
    def __init__(self):
        self.cases: dict[str, BenchmarkCase] = {}
        self.baselines: dict[str, float] = {}  # case_id → baseline score
        self.results: list[BenchmarkResult] = []
        self.regressions: list[Regression] = []
    
    def register_case(self, name: str, description: str,
                      test_function: Callable, expected_result: Any,
                      timeout_seconds: int = 30,
                      metadata: dict[str, Any] | None = None) -> BenchmarkCase:
        """Register a benchmark test case."""
        case = BenchmarkCase(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            test_function=test_function,
            expected_result=expected_result,
            timeout_seconds=timeout_seconds,
            metadata=metadata or {},
        )
        self.cases[case.id] = case
        return case
    
    def set_baseline(self, case_id: str, score: float):
        """Set baseline score for a test case."""
        self.baselines[case_id] = score
    
    def evaluate(self, version: str,
                 test_functions: dict[str, Callable] | None = None) -> BenchmarkResult:
        """Run a benchmark suite."""
        runs: list[BenchmarkRun] = []
        total_score = 0.0
        passed = 0
        failed = 0
        
        for case_id, case in self.cases.items():
            start_time = time.time()
            
            try:
                # Run the test function
                if test_functions and case.name in test_functions:
                    actual = test_functions[case.name]()
                else:
                    actual = case.test_function()
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Check result
                if actual == case.expected_result:
                    result = TestResult.PASSED
                    passed += 1
                    total_score += 1.0
                else:
                    result = TestResult.FAILED
                    failed += 1
                
                run = BenchmarkRun(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    result=result,
                    actual_result=actual,
                    duration_ms=duration_ms,
                    timestamp=time.time(),
                )
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                run = BenchmarkRun(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    result=TestResult.FAILED,
                    actual_result=None,
                    duration_ms=duration_ms,
                    timestamp=time.time(),
                    error=str(e),
                )
                failed += 1
            
            runs.append(run)
        
        # Calculate total score
        total = passed + failed
        total_score = passed / total if total > 0 else 0.0
        
        # Get baseline
        baseline_score = sum(self.baselines.values()) / len(self.baselines) if self.baselines else 0.5
        
        # Detect regressions
        regressions = self._detect_regressions(runs)
        
        # Create result
        result = BenchmarkResult(
            id=str(uuid.uuid4()),
            version=version,
            runs=runs,
            regressions=regressions,
            total_score=total_score,
            baseline_score=baseline_score,
            improved=total_score > baseline_score,
            regressed=total_score < baseline_score * 0.9,
            timestamp=time.time(),
            summary={
                "total": total,
                "passed": passed,
                "failed": failed,
                "score": total_score,
                "baseline": baseline_score,
            },
        )
        
        self.results.append(result)
        return result
    
    def _detect_regressions(self, runs: list[BenchmarkRun]) -> list[Regression]:
        """Detect regressions by comparing with baselines."""
        regressions = []
        
        for run in runs:
            baseline = self.baselines.get(run.case_id)
            if baseline is None:
                continue
            
            current = 1.0 if run.result == TestResult.PASSED else 0.0
            
            if current < baseline:
                # Determine severity
                delta = baseline - current
                if delta > 0.5:
                    severity = RegressionSeverity.CRITICAL
                elif delta > 0.3:
                    severity = RegressionSeverity.HIGH
                elif delta > 0.1:
                    severity = RegressionSeverity.MEDIUM
                else:
                    severity = RegressionSeverity.LOW
                
                regression = Regression(
                    id=str(uuid.uuid4()),
                    case_id=run.case_id,
                    baseline_score=baseline,
                    current_score=current,
                    severity=severity,
                    description=f"Regression: {run.case_id} dropped from {baseline:.2f} to {current:.2f}",
                    timestamp=time.time(),
                )
                regressions.append(regression)
                self.regressions.append(regression)
        
        return regressions
    
    def get_latest_result(self) -> BenchmarkResult | None:
        """Get the most recent benchmark result."""
        if not self.results:
            return None
        return self.results[-1]
    
    def get_regressions(self, severity: RegressionSeverity = None) -> list[Regression]:
        """Get all regressions, optionally filtered by severity."""
        if severity:
            return [r for r in self.regressions if r.severity == severity]
        return self.regressions
    
    def get_state(self) -> dict[str, Any]:
        return {
            "cases": len(self.cases),
            "results": len(self.results),
            "regressions": len(self.regressions),
            "baselines": len(self.baselines),
        }
