"""Playwright-based E2E test runner."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from testpilot.models import TestType


class Browser(Protocol):
    """Protocol for browser abstraction."""
    def goto(self, url: str) -> Any: ...
    def click(self, selector: str) -> None: ...
    def fill(self, selector: str, value: str) -> None: ...
    def screenshot(self, path: str) -> bytes: ...
    def close(self) -> None: ...


@dataclass
class E2EStep:
    """A single step in an E2E test."""
    action: str  # goto, click, fill, wait, assert, screenshot
    selector: str = ""
    value: str = ""
    expected: str = ""
    timeout_ms: int = 5000


@dataclass
class E2EResult:
    """Result of an E2E test run."""
    name: str
    passed: bool
    duration_ms: float = 0.0
    steps_completed: int = 0
    total_steps: int = 0
    error_message: str = ""
    screenshot_path: str = ""
    trace_path: str = ""


@dataclass
class E2ETest:
    """Definition of an E2E test."""
    name: str
    url: str
    steps: list[E2EStep] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class E2ERunner:
    """Runs Playwright-based E2E tests."""

    def __init__(
        self,
        browser: str = "chromium",
        headless: bool = True,
        base_url: str = "http://localhost:3000",
        output_dir: str = "./testpilot-output/e2e",
    ) -> None:
        self.browser_name = browser
        self.headless = headless
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._browser = None

    def start(self) -> None:
        """Initialize Playwright and launch browser."""
        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            browser_type = getattr(self._playwright, self.browser_name)
            self._browser = browser_type.launch(headless=self.headless)
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Install with: pip install playwright"
            )

    def stop(self) -> None:
        """Close browser and stop Playwright."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def run_test(self, test: E2ETest) -> E2EResult:
        """Run a single E2E test."""
        if not self._browser:
            self.start()

        start_time = time.monotonic()
        context = self._browser.new_context()
        page = context.new_page()
        screenshot_dir = self.output_dir / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)

        try:
            full_url = test.url if test.url.startswith("http") else f"{self.base_url}{test.url}"
            page.goto(full_url)

            for i, step in enumerate(test.steps):
                self._execute_step(page, step, str(screenshot_dir), i)

            duration = (time.monotonic() - start_time) * 1000
            return E2EResult(
                name=test.name,
                passed=True,
                duration_ms=duration,
                steps_completed=len(test.steps),
                total_steps=len(test.steps),
            )
        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            screenshot_path = str(screenshot_dir / f"{test.name}_error.png")
            try:
                page.screenshot(path=screenshot_path, full_page=True)
            except Exception:
                pass
            return E2EResult(
                name=test.name,
                passed=False,
                duration_ms=duration,
                error_message=str(e),
                screenshot_path=screenshot_path,
            )
        finally:
            context.close()

    def _execute_step(
        self, page: Any, step: E2EStep, screenshot_dir: str, index: int
    ) -> None:
        """Execute a single E2E step."""
        action = step.action.lower()

        if action == "goto":
            url = step.value if step.value.startswith("http") else f"{self.base_url}{step.value}"
            page.goto(url, timeout=step.timeout_ms)
        elif action == "click":
            page.click(step.selector, timeout=step.timeout_ms)
        elif action == "fill":
            page.fill(step.selector, step.value, timeout=step.timeout_ms)
        elif action == "wait":
            if step.selector:
                page.wait_for_selector(step.selector, timeout=step.timeout_ms)
            else:
                page.wait_for_timeout(int(step.value or "1000"))
        elif action == "screenshot":
            path = f"{screenshot_dir}/step_{index}.png"
            page.screenshot(path=path, full_page=True)
        elif action == "assert_visible":
            page.wait_for_selector(
                step.selector, state="visible", timeout=step.timeout_ms
            )
        elif action == "assert_text":
            element = page.wait_for_selector(
                step.selector, timeout=step.timeout_ms
            )
            text = element.text_content() or ""
            if step.expected not in text:
                raise AssertionError(
                    f"Expected text '{step.expected}' in '{step.selector}', got '{text}'"
                )
        elif action == "assert_url":
            if step.expected not in page.url:
                raise AssertionError(
                    f"Expected URL to contain '{step.expected}', got '{page.url}'"
                )
        else:
            raise ValueError(f"Unknown E2E action: {action}")

    def run_tests(self, tests: list[E2ETest]) -> list[E2EResult]:
        """Run multiple E2E tests and return results."""
        results = []
        for test in tests:
            result = self.run_test(test)
            results.append(result)
        return results

    def generate_report(self, results: list[E2EResult]) -> dict[str, Any]:
        """Generate a JSON report from E2E results."""
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        total_duration = sum(r.duration_ms for r in results)

        return {
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / len(results) if results else 0,
                "total_duration_ms": total_duration,
            },
            "tests": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "error": r.error_message,
                    "screenshot": r.screenshot_path,
                }
                for r in results
            ],
        }

    def save_report(self, results: list[E2EResult], path: str | Path | None = None) -> Path:
        """Save the E2E report to a JSON file."""
        report = self.generate_report(results)
        report_path = Path(path or self.output_dir / "e2e-report.json")
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report_path

    def __enter__(self) -> E2ERunner:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


def create_test_from_yaml(yaml_path: str | Path) -> E2ETest:
    """Create an E2ETest from a YAML definition file."""
    import yaml

    data = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
    steps = [E2EStep(**s) for s in data.get("steps", [])]
    return E2ETest(
        name=data["name"],
        url=data.get("url", ""),
        steps=steps,
        tags=data.get("tags", []),
    )
