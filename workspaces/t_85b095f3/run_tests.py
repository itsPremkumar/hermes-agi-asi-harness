"""Quick test runner."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-x", "--timeout=10", "-q"],
    capture_output=True, text=True, timeout=60
)
print("STDOUT:", result.stdout[-3000:])
print("STDERR:", result.stderr[-2000:])
print("RC:", result.returncode)
