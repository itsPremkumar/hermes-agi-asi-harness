#!/usr/bin/env python3
"""QA harness for AgentOS — runs all tests and validates the project structure."""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

def check_structure():
    """Verify project structure exists."""
    required = [
        "src/agentos/__init__.py",
        "src/agentos/scheduler/__init__.py",
        "src/agentos/governor/__init__.py",
        "src/agentos/sandbox/__init__.py",
        "src/agentos/bus/__init__.py",
        "src/agentos/state/__init__.py",
        "src/agentos/plugins/__init__.py",
        "src/agentos/observability/__init__.py",
        "src/agentos/tenancy/__init__.py",
        "src/agentos/cli/__init__.py",
        "src/agentos/dashboard/__init__.py",
        "tests/test_scheduler.py",
        "tests/test_governor.py",
        "tests/test_state.py",
        "tests/test_bus.py",
        "tests/test_observability.py",
        "tests/test_tenancy.py",
        "tests/test_sandbox.py",
        "tests/test_plugins.py",
        "tests/test_cli.py",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "requirements.txt",
        ".env.example",
    ]
    missing = []
    for f in required:
        if not (ROOT / f).exists():
            missing.append(f)
    if missing:
        print("FAIL: Missing files:")
        for m in missing:
            print(f"  - {m}")
        return False
    print("PASS: Project structure complete")
    return True

def run_imports():
    """Verify all modules can be imported."""
    modules = [
        "agentos",
        "agentos.scheduler",
        "agentos.governor",
        "agentos.sandbox",
        "agentos.bus",
        "agentos.state",
        "agentos.plugins",
        "agentos.observability",
        "agentos.tenancy",
        "agentos.cli",
        "agentos.dashboard",
    ]
    for mod in modules:
        try:
            __import__(mod)
        except ImportError as e:
            print(f"FAIL: Cannot import {mod}: {e}")
            return False
    print("PASS: All modules importable")
    return True

def run_self_test():
    """Run the CLI self-test."""
    result = subprocess.run(
        [sys.executable, "-m", "agentos", "self-test"],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    if result.returncode != 0:
        print("FAIL: CLI self-test failed")
        print(result.stdout)
        print(result.stderr)
        return False
    print("PASS: CLI self-test passed")
    return True

def run_unit_tests():
    """Run the comprehensive test runner."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "test_runner.py")],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    if result.returncode != 0:
        print("FAIL: Unit tests failed")
        print(result.stdout[-2000:])
        print(result.stderr[-1000:])
        return False
    # Extract pass count
    for line in result.stdout.split('\n'):
        if 'TOTAL:' in line:
            print(f"PASS: {line.strip()}")
            return True
    print("PASS: Unit tests passed")
    return True

def main():
    print("=" * 60)
    print("AgentOS QA Harness")
    print("=" * 60)
    
    checks = [
        ("Structure", check_structure),
        ("Imports", run_imports),
        ("Self-test", run_self_test),
        ("Unit tests", run_unit_tests),
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"\n--- {name} ---")
        try:
            results.append((name, check_fn()))
        except Exception as e:
            print(f"FAIL: {name} raised {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary:")
    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_pass = False
    
    if all_pass:
        print("\nAll checks passed!")
        return 0
    else:
        print("\nSome checks failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
