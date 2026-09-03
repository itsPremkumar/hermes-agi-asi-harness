
"""
Evaluator — deterministic benchmark execution + trace capture.

Extracted & enhanced from agx-harness-main:
- evaluator.py: EvalResult, parse_metric, evaluate, _quote_exe

AVO law: f(candidate) must be deterministic.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class EvalResult:
    __slots__ = ("ok", "score", "trace")

    def __init__(self, ok: bool, score: float | None, trace: dict[str, Any]):
        self.ok = ok
        self.score = score
        self.trace = trace

    def __repr__(self) -> str:
        return f"EvalResult(ok={self.ok!r}, score={self.score!r})"


def parse_metric(stdout: str, metric_name: str) -> tuple[bool, float | None]:
    """Parse metric from stdout."""
    lines = [ln.strip() for ln in (stdout or "").splitlines() if ln.strip()]
    if not lines:
        return False, None
    last = lines[-1]
    if last.startswith("METRIC"):
        try:
            return True, float(last.split()[1])
        except (IndexError, ValueError):
            return False, None
    if last.startswith("{"):
        try:
            obj = json.loads(last)
            val = obj.get(metric_name)
            return isinstance(val, (int, float)), (
                float(val) if isinstance(val, (int, float)) else None)
        except json.JSONDecodeError:
            return False, None
    try:
        return True, float(last)
    except ValueError:
        return False, None


def _quote_exe(cmd: str) -> str:
    """Ensure the leading executable is quoted if its path contains spaces."""
    s = cmd.lstrip()
    if s[:1] in ('"', "'"):
        return cmd
    parts = s.split(" ")
    exe = parts[0]
    for i in range(1, len(parts)):
        cand = " ".join(parts[:i + 1])
        if os.path.isfile(cand) or os.path.isfile(cand + ".exe"):
            exe = cand + (".exe" if os.path.isfile(cand + ".exe") else "")
            break
    if " " in exe and exe[:1] not in ('"', "'"):
        return '"' + exe + '"' + s[len(exe):]
    return cmd


def evaluate(bench_cmd: str, cwd: str | None, metric_name: str = "score",
             timeout: int = 1800) -> EvalResult:
    """Run the deterministic benchmark. Never raises; failures become traces."""
    try:
        r = subprocess.run(_quote_exe(bench_cmd), shell=True, cwd=cwd,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return EvalResult(False, None, {"error": f"bench timeout after {timeout}s"})
    except Exception as e:
        return EvalResult(False, None, {"error": repr(e)})
    
    ok, score = parse_metric(r.stdout or "", metric_name)
    trace = {
        "rc": r.returncode,
        "stdout_tail": (r.stdout or "")[-2000:],
        "stderr_tail": (r.stderr or "")[-2000:],
        "metric_parsed": ok,
    }
    if not ok:
        trace["error"] = "could not parse METRIC from stdout"
    return EvalResult(ok and r.returncode == 0, score, trace)
