"""Performance testing integration — Locust and k6."""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from testpilot.models import GateStatus, PerformanceResult, QualityGateResult


@dataclass
class PerfThreshold:
    """Threshold configuration for performance tests."""
    max_p95_ms: float = 500.0
    max_avg_ms: float = 200.0
    max_failure_rate: float = 0.01
    min_rps: float = 10.0


class LocustRunner:
    """Runs Locust performance tests."""

    def __init__(
        self,
        locustfile: str = "locustfile.py",
        host: str = "http://localhost:8080",
    ) -> None:
        self.locustfile = locustfile
        self.host = host

    def run_headless(
        self,
        users: int = 50,
        duration: str = "30s",
        spawn_rate: float = 5.0,
    ) -> PerformanceResult:
        """Run Locust in headless mode and parse results."""
        cmd = [
            "locust",
            "-f", self.locustfile,
            "--host", self.host,
            "--headless",
            "-u", str(users),
            "-r", str(spawn_rate),
            "-t", duration,
            "--json",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return self._parse_json_output(result.stdout)
        except FileNotFoundError:
            raise RuntimeError(
                "Locust is not installed. Install with: pip install locust"
            )
        except subprocess.TimeoutExpired:
            return PerformanceResult(
                tool="locust",
                total_requests=0,
                failed_requests=0,
            )

    def _parse_json_output(self, output: str) -> PerformanceResult:
        """Parse Locust JSON output."""
        try:
            data = json.loads(output)
            stats = data.get("stats", [{}])[0] if data.get("stats") else {}
            return PerformanceResult(
                tool="locust",
                total_requests=stats.get("num_requests", 0),
                failed_requests=stats.get("num_failures", 0),
                avg_response_time_ms=stats.get("avg_response_time", 0),
                p50_ms=stats.get("current_response_time_percentile_50", 0),
                p95_ms=stats.get("current_response_time_percentile_95", 0),
                p99_ms=stats.get("current_response_time_percentile_99", 0),
                requests_per_second=stats.get("current_rps", 0),
                duration_seconds=stats.get("total_response_time", 0) / 1000,
            )
        except (json.JSONDecodeError, IndexError, KeyError):
            return PerformanceResult(tool="locust")


class K6Runner:
    """Runs k6 performance tests."""

    def __init__(self, script_path: str = "perf-test.js") -> None:
        self.script_path = script_path

    def run(self, output_json: str | None = None) -> PerformanceResult:
        """Run a k6 test and parse results."""
        cmd = ["k6", "run", "--out", "json=/tmp/k6-results.json", self.script_path]

        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return self._parse_k6_json("/tmp/k6-results.json", output_json)
        except FileNotFoundError:
            raise RuntimeError("k6 is not installed.")
        except subprocess.TimeoutExpired:
            return PerformanceResult(tool="k6")

    def _parse_k6_json(
        self, json_path: str, output_json: str | None
    ) -> PerformanceResult:
        """Parse k6 JSON output."""
        try:
            lines = Path(json_path).read_text(encoding="utf-8").strip().split("\n")
            metrics: dict[str, Any] = {}
            for line in lines:
                try:
                    data = json.loads(line)
                    if data.get("type") == "Point" and data.get("metric") in {
                        "http_req_duration",
                        "http_reqs",
                        "http_req_failed",
                    }:
                        metric_name = data["metric"]
                        if metric_name not in metrics:
                            metrics[metric_name] = []
                        metrics[metric_name].append(data.get("data", {}).get("value", 0))
                except json.JSONDecodeError:
                    continue

            durations = metrics.get("http_req_duration", [])
            total = len(durations)
            failures = sum(1 for v in metrics.get("http_req_failed", []) if v > 0)

            if durations:
                sorted_d = sorted(durations)
                p50_idx = int(len(sorted_d) * 0.5)
                p95_idx = int(len(sorted_d) * 0.95)
                p99_idx = int(len(sorted_d) * 0.99)
                avg = sum(sorted_d) / len(sorted_d)
                p50 = sorted_d[p50_idx]
                p95 = sorted_d[p95_idx]
                p99 = sorted_d[p99_idx]
            else:
                avg = p50 = p95 = p99 = 0.0

            return PerformanceResult(
                tool="k6",
                total_requests=total,
                failed_requests=failures,
                avg_response_time_ms=avg,
                p50_ms=p50,
                p95_ms=p95,
                p99_ms=p99,
                requests_per_second=total / 30 if total else 0,
                duration_seconds=30.0,
            )
        except Exception:
            return PerformanceResult(tool="k6")


class PerfIntegration:
    """Unified performance testing interface."""

    def __init__(
        self,
        tool: str = "locust",
        host: str = "http://localhost:8080",
        script_path: str | None = None,
    ) -> None:
        self.tool = tool
        self.host = host
        self.script_path = script_path

        if tool == "locust":
            self._runner = LocustRunner(
                locustfile=script_path or "locustfile.py",
                host=host,
            )
        elif tool == "k6":
            self._runner = K6Runner(script_path=script_path or "perf-test.js")
        else:
            raise ValueError(f"Unsupported performance tool: {tool}")

    def run(
        self,
        users: int = 50,
        duration: str = "30s",
    ) -> PerformanceResult:
        """Run performance test."""
        if self.tool == "locust":
            return self._runner.run_headless(users=users, duration=duration)
        elif self.tool == "k6":
            return self._runner.run()
        else:
            raise ValueError(f"Unsupported tool: {self.tool}")

    def check_thresholds(
        self,
        result: PerformanceResult,
        thresholds: PerfThreshold | None = None,
    ) -> QualityGateResult:
        """Check performance results against thresholds."""
        thresholds = thresholds or PerfThreshold()
        failures: list[str] = []

        if result.p95_ms > thresholds.max_p95_ms:
            failures.append(
                f"p95 latency {result.p95_ms:.1f}ms exceeds {thresholds.max_p95_ms}ms"
            )
        if result.avg_response_time_ms > thresholds.max_avg_ms:
            failures.append(
                f"avg latency {result.avg_response_time_ms:.1f}ms exceeds {thresholds.max_avg_ms}ms"
            )
        failure_rate = (
            result.failed_requests / result.total_requests
            if result.total_requests
            else 0
        )
        if failure_rate > thresholds.max_failure_rate:
            failures.append(
                f"failure rate {failure_rate:.2%} exceeds {thresholds.max_failure_rate:.2%}"
            )
        if result.requests_per_second < thresholds.min_rps:
            failures.append(
                f"RPS {result.requests_per_second:.1f} below {thresholds.min_rps}"
            )

        status = GateStatus.PASS if not failures else GateStatus.FAIL
        return QualityGateResult(
            name="performance",
            status=status,
            message="Performance thresholds met" if not failures else "; ".join(failures),
            details={
                "p95_ms": result.p95_ms,
                "avg_ms": result.avg_response_time_ms,
                "failure_rate": failure_rate,
                "rps": result.requests_per_second,
                "total_requests": result.total_requests,
            },
        )


def generate_locustfile(
    endpoints: list[dict[str, Any]],
    output_path: str = "locustfile.py",
) -> Path:
    """Generate a Locust test file from endpoint definitions."""
    lines = [
        "from locust import HttpUser, task, between",
        "",
        "",
        "class TestPilotUser(HttpUser):",
        "    wait_time = between(1, 3)",
        "",
    ]

    for i, ep in enumerate(endpoints):
        method = ep.get("method", "GET").lower()
        path = ep.get("path", "/")
        weight = ep.get("weight", 1)
        name = ep.get("name", f"endpoint_{i}")

        lines.append(f"    @task({weight})")
        lines.append(f"    def {name}(self):")
        if method == "get":
            lines.append(f'        self.client.get("{path}")')
        elif method == "post":
            body = json.dumps(ep.get("body", {}))
            lines.append(f'        self.client.post("{path}", json={body})')
        elif method == "put":
            body = json.dumps(ep.get("body", {}))
            lines.append(f'        self.client.put("{path}", json={body})')
        elif method == "delete":
            lines.append(f'        self.client.delete("{path}")')
        lines.append("")

    content = "\n".join(lines)
    Path(output_path).write_text(content, encoding="utf-8")
    return Path(output_path)


def generate_k6_script(
    endpoints: list[dict[str, Any]],
    output_path: str = "perf-test.js",
) -> Path:
    """Generate a k6 test script from endpoint definitions."""
    lines = [
        "import http from 'k6/http';",
        "import { check, sleep } from 'k6';",
        "",
        "export const options = {",
        "  stages: [",
        "    { duration: '10s', target: 20 },",
        "    { duration: '10s', target: 50 },",
        "    { duration: '10s', target: 0 },",
        "  ],",
        "};",
        "",
        "export default function () {",
    ]

    for ep in endpoints:
        method = ep.get("method", "GET").upper()
        path = ep.get("path", "/")
        body = json.dumps(ep.get("body", None))

        if method == "GET":
            lines.append(f"  let res = http.get('{path}');")
        else:
            lines.append(f"  let res = http.{method.lower()}('{path}', {body});")
        lines.append("  check(res, { 'status was 200': (r) => r.status == 200 });")
        lines.append("  sleep(1);")
        lines.append("")

    lines.append("}")

    content = "\n".join(lines)
    Path(output_path).write_text(content, encoding="utf-8")
    return Path(output_path)
