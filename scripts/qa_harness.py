#!/usr/bin/env python3
"""QA harness for hermes-agi-asi-harness (SOUL standing order #5).

Usage: python scripts/qa_harness.py [<repo-root>]
Exit 0 only if EVERY gate passes. Stdlib only.

Gates:
  1. CLI --version / health / self-test (real execution, offline)
  2. Fast pytest subset (per-project isolation: runs under this interpreter)
  3. scripts/verify_imports.py + scripts/check_canonical.py
  4. ruff on the enforced-clean scope (files this team keeps green)
  5. requirements.txt <-> pyproject.toml dependency sync
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
PY = sys.executable

# Files kept ruff-clean by this team. The wider repo has legacy lint debt
# (tracked separately); QA enforces green on code we own and touch.
RUFF_SCOPE = [
    "src/hermes_agi/self_test.py",
    "src/hermes_agi/__main__.py",
    "src/hermes_agi/plugins/core_plugins.py",
    "src/hermes_agi/plugins/real_plugins.py",
    "src/harness/graph.py",
    "src/safety/__init__.py",
    "src/safety/risk_assessor.py",
    "src/core/benchmark/harness.py",
    "src/core/benchmark/__init__.py",
    "src/core/dashboard/__init__.py",
    "scripts/qa_harness.py",
]

FAST_TESTS = [
    "tests/test_harness.py",
    "tests/test_config.py",
    "tests/test_benchmark_harness.py",
    "tests/test_operations.py",
]

results: list[tuple[str, bool, str]] = []


def run_gate(name: str, cmd: list[str], cwd: Path = ROOT) -> bool:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=600)
    except Exception as exc:  # noqa: BLE001 - reported as gate failure
        results.append((name, False, f"could not run: {exc}"))
        print(f"FAIL {name}: could not run: {exc}")
        return False
    ok = proc.returncode == 0
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    tail = "\n".join(tail[-4:]) if tail else "(no output)"
    results.append((name, ok, tail))
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        print("  --- tail ---\n  " + tail.replace("\n", "\n  "))
    return ok


def gate_sync() -> bool:
    """requirements.txt runtime deps must mirror pyproject [project.dependencies]."""
    name = "deps-sync requirements.txt <-> pyproject.toml"
    try:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    except OSError as exc:
        results.append((name, False, str(exc)))
        print(f"FAIL {name}: {exc}")
        return False
    m = re.search(r"dependencies\s*=\s*\[(.*?)\]", pyproject, re.S)
    if not m:
        results.append((name, False, "no [project.dependencies] found"))
        print(f"FAIL {name}: no [project.dependencies] found")
        return False
    py_deps = {
        re.split(r"[<>=!~\s\[]", d.strip().strip('"').strip("'"))[0].lower().replace("-", "_")
        for d in m.group(1).split(",")
        if d.strip().strip('"').strip("'")
    }
    py_deps.discard("")
    req_names: set[str] = set()
    for line in requirements.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        req_names.add(re.split(r"[<>=!~\s\[]", line)[0].lower().replace("-", "_"))
    missing = sorted(py_deps - req_names)
    ok = not missing
    detail = "in sync" if ok else f"missing from requirements.txt: {missing}"
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    return ok


def main() -> int:
    print(f"QA harness — root: {ROOT} — python: {PY}")
    all_ok = True
    all_ok &= run_gate("cli --version", [PY, "-m", "hermes_agi", "--version"])
    all_ok &= run_gate("cli health", [PY, "-m", "hermes_agi", "health"])
    all_ok &= run_gate("cli self-test", [PY, "-m", "hermes_agi", "self-test"])
    all_ok &= run_gate("pytest fast subset", [PY, "-m", "pytest", *FAST_TESTS, "-q"])
    all_ok &= run_gate("verify_imports", [PY, "scripts/verify_imports.py"])
    all_ok &= run_gate("check_canonical", [PY, "scripts/check_canonical.py", "--root", "."])
    all_ok &= run_gate("ruff enforced scope", [PY, "-m", "ruff", "check", *RUFF_SCOPE])
    all_ok &= gate_sync()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\nQA: {passed}/{len(results)} gates passed")
    if all_ok:
        print("QA HARNESS GREEN")
        return 0
    print("QA HARNESS RED — see FAIL lines above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
