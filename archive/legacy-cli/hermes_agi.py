#!/usr/bin/env python3
"""Hermes AGI/ASI Harness — Main Entry Point (legacy, redirects to hermes_agi_v2).

DEPRECATED: Use hermes_agi_v2.py or `python -m hermes_agi_v2` instead.
This file redirects to hermes_agi_v2.py for backward compatibility.
"""

import sys
import os
from pathlib import Path

# Redirect to unified entry point
_script_dir = Path(__file__).parent
_sys_path_0 = sys.path[0]
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

# Forward all arguments
sys.argv[0] = "hermes_agi_v2.py"

from hermes_agi_v2 import main  # noqa: E402

if __name__ == "__main__":
    main()