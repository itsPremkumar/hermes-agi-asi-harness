"""CI Debugger — diagnose why tests fail in CI but pass locally."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TestResult:
    test_name: str
    passed: bool
    duration: float
    output: str
    error: str = ""


@dataclass
class CIDebugResult:
    test_name: str
    local_result: TestResult | None
    ci_result: TestResult | None
    root_cause: str
    recommendation: str
    confidence: float


class CIDebugger:
    """Diagnose CI test failures."""

    def __init__(self):
        self._local_results: dict[str, TestResult] = {}
        self._ci_results: dict[str, TestResult] = {}

    def add_local_result(self, result: TestResult) -> None:
        self._local_results[result.test_name] = result

    def add_ci_result(self, result: TestResult) -> None:
        self._ci_results[result.test_name] = result

    def diagnose(self, test_name: str) -> CIDebugResult:
        local = self._local_results.get(test_name)
        ci = self._ci_results.get(test_name)

        if local and ci:
            if local.passed and not ci.passed:
                return CIDebugResult(
                    test_name=test_name,
                    local_result=local,
                    ci_result=ci,
                    root_cause="Environment difference",
                    recommendation="Check OS, Python version, environment variables",
                    confidence=0.7,
                )
            elif not local.passed and ci.passed:
                return CIDebugResult(
                    test_name=test_name,
                    local_result=local,
                    ci_result=ci,
                    root_cause="Local environment issue",
                    recommendation="Check local dependencies, cache, or state",
                    confidence=0.6,
                )
            elif not local.passed and not ci.passed:
                return CIDebugResult(
                    test_name=test_name,
                    local_result=local,
                    ci_result=ci,
                    root_cause="Genuine test failure",
                    recommendation="Fix the test or the code",
                    confidence=0.9,
                )
            else:
                return CIDebugResult(
                    test_name=test_name,
                    local_result=local,
                    ci_result=ci,
                    root_cause="Flaky test",
                    recommendation="Add retry logic or increase timeout",
                    confidence=0.5,
                )
        elif local and not ci:
            return CIDebugResult(
                test_name=test_name,
                local_result=local,
                ci_result=None,
                root_cause="Test not run in CI",
                recommendation="Check CI configuration",
                confidence=0.8,
            )
        elif ci and not local:
            return CIDebugResult(
                test_name=test_name,
                local_result=None,
                ci_result=ci,
                root_cause="Test not run locally",
                recommendation="Run test locally to reproduce",
                confidence=0.8,
            )
        else:
            return CIDebugResult(
                test_name=test_name,
                local_result=None,
                ci_result=None,
                root_cause="No data",
                recommendation="Run test in both environments",
                confidence=0.0,
            )

    def diagnose_all(self) -> list[CIDebugResult]:
        all_tests = set(self._local_results.keys()) | set(self._ci_results.keys())
        return [self.diagnose(test) for test in all_tests]

    def get_flaky_tests(self) -> list[str]:
        flaky = []
        for test_name in set(self._local_results.keys()) & set(self._ci_results.keys()):
            local = self._local_results[test_name]
            ci = self._ci_results[test_name]
            if local.passed != ci.passed:
                flaky.append(test_name)
        return flaky
