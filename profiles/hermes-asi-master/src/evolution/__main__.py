"""Self-test subcommand for the evolution package.

Run with: python -m evolution self-test
"""

from __future__ import annotations

import os
import subprocess
import sys


def self_test() -> bool:
    """Run all evolution tests. Returns True if all pass."""
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(pkg_dir, "tests")

    if not os.path.isdir(tests_dir):
        print(f"ERROR: tests directory not found: {tests_dir}")
        return False

    test_files = sorted(
        f for f in os.listdir(tests_dir)
        if f.startswith("test_") and f.endswith(".py")
    )

    if not test_files:
        print("ERROR: no test files found")
        return False

    all_passed = True
    for test_file in test_files:
        path = os.path.join(tests_dir, test_file)
        print(f"\n{'=' * 60}")
        print(f"  Running: {test_file}")
        print(f"{'=' * 60}")
        result = subprocess.run(
            [sys.executable, path],
            cwd=pkg_dir,
        )
        if result.returncode != 0:
            all_passed = False
            print(f"\n  FAILED: {test_file}")
        else:
            print(f"\n  PASSED: {test_file}")

    print(f"\n{'=' * 60}")
    if all_passed:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
    print(f"{'=' * 60}")
    return all_passed


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "self-test":
        ok = self_test()
        sys.exit(0 if ok else 1)
    else:
        print("Usage: python -m evolution self-test")
        sys.exit(1)


if __name__ == "__main__":
    main()
