#!/usr/bin/env python3
"""Harness Control Plane (legacy, redirects to hermes_agi_v2 --benchmark).

DEPRECATED: Use hermes_agi_v2.py --benchmark instead.
"""

import sys
from pathlib import Path

_script_dir = Path(__file__).parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

sys.argv[0] = "hermes_agi_v2.py"
sys.argv.insert(1, "--benchmark")

from hermes_agi_v2 import main  # noqa: E402

if __name__ == "__main__":
    main()