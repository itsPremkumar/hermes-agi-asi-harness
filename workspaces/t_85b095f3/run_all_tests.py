import subprocess
import sys
import time

test_files = [
    "tests/test_scheduler.py",
    "tests/test_governor.py",
    "tests/test_state.py",
    "tests/test_bus.py",
    "tests/test_observability.py",
    "tests/test_tenancy.py",
    "tests/test_sandbox.py",
    "tests/test_plugins.py",
    "tests/test_cli.py",
]

for tf in test_files:
    print(f"\n=== {tf} ===")
    start = time.time()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", tf, "-v", "--timeout=5", "--tb=short"],
        capture_output=True, text=True, timeout=30
    )
    elapsed = time.time() - start
    print(f"  RC: {result.returncode} ({elapsed:.1f}s)")
    # Print only summary lines
    for line in result.stdout.split('\n'):
        if 'PASSED' in line or 'FAILED' in line or 'ERROR' in line or 'passed' in line or 'failed' in line:
            print(f"  {line}")
    if result.returncode != 0:
        err_lines = result.stderr.split('\n')
        for line in err_lines:
            if 'ERROR' in line or 'FAIL' in line or 'error' in line.lower():
                print(f"  STDERR: {line}")
