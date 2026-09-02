import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--timeout=10", "--tb=short"],
    capture_output=True, text=True, timeout=120
)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
print("RC:", result.returncode)
