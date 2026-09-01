import os
import sys
# Prepend our src directory to ensure it's found first
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# Remove any v9-stage2 paths that might conflict
sys.path = [p for p in sys.path if "v9-stage2" not in p]
