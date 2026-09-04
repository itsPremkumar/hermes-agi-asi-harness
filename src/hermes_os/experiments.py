"""
HERMES — EXPERIMENTATION ENGINE (hypothesis → design → execute → observe → verdict)
====================================================================================
First-class empirical loop for software + strategy hypotheses. Runs inside
isolated sandbox dirs under .hermes/experiments/, never in the live tree.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("hermes.os.experiments")


@dataclass
class Experiment:
    exp_id: str
    hypothesis: str
    design: str = ""
    status: str = "designed"  # designed|running|passed|failed
    observation: str = ""
    measurement: float = 0.0
    baseline: float = 0.0
    verdict: str = ""
    elapsed_s: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {"exp_id": self.exp_id, "hypothesis": self.hypothesis, "design": self.design,
                "status": self.status, "observation": self.observation[:2000],
                "measurement": self.measurement, "baseline": self.baseline,
                "verdict": self.verdict, "elapsed_s": round(self.elapsed_s, 2)}


class ExperimentEngine:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.exp_dir = Path(workspace_root) / ".hermes" / "experiments"
        self.exp_dir.mkdir(parents=True, exist_ok=True)

    def design(self, hypothesis: str, design: str = "", baseline: float = 0.0) -> Experiment:
        return Experiment(exp_id=f"exp-{uuid.uuid4().hex[:8]}", hypothesis=hypothesis,
                          design=design or f"Test: {hypothesis}", baseline=baseline)

    def run_code(self, exp: Experiment, code: str, timeout: int = 30) -> Experiment:
        """Execute hypothesis code in isolated sandbox, capture measurement from stdout float."""
        exp.status = "running"
        t0 = time.perf_counter()
        box = self.exp_dir / exp.exp_id
        box.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run([sys.executable, "-c", code], cwd=str(box),
                                  capture_output=True, text=True, timeout=timeout)
            exp.elapsed_s = time.perf_counter() - t0
            exp.observation = (proc.stdout[-1500:] + proc.stderr[-500:]).strip()
            try:
                exp.measurement = float(proc.stdout.strip().split()[-1])
            except Exception:
                exp.measurement = 1.0 if proc.returncode == 0 else 0.0
            exp.status = "passed" if proc.returncode == 0 else "failed"
            exp.verdict = ("HOLD" if exp.measurement > exp.baseline else "REJECT"
                           if exp.status == "passed" else f"ERROR rc={proc.returncode}")
        except Exception as e:
            exp.elapsed_s = time.perf_counter() - t0
            exp.status = "failed"
            exp.observation = str(e)[:1000]
            exp.verdict = f"ERROR {e}"
        (box / "result.json").write_text(__import__("json").dumps(exp.to_dict(), indent=2), encoding="utf-8")
        return exp

    def run_fn(self, exp: Experiment, fn: Callable[[], float]) -> Experiment:
        exp.status = "running"
        t0 = time.perf_counter()
        try:
            exp.measurement = float(fn())
            exp.status = "passed"
            exp.verdict = "HOLD" if exp.measurement > exp.baseline else "REJECT"
            exp.observation = f"fn measurement={exp.measurement}"
        except Exception as e:
            exp.status = "failed"
            exp.observation = str(e)[:1000]
            exp.verdict = f"ERROR {e}"
        exp.elapsed_s = time.perf_counter() - t0
        return exp
