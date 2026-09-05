#!/usr/bin/env python3
"""Fail if canonical modules import legacy generations (see docs/CANONICAL.md).

Usage: python scripts/check_canonical.py [--root .]
Exit 1 with the list of violations.
"""
import argparse
import re
import sys
from pathlib import Path

IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.M)

# Dotted prefixes that are legacy generations. Canonical code must not import them.
LEGACY = [
    "core.runtime.kernel", "core.runtime.planner", "core.runtime.supervisor",
    "core.runtime.agent", "core.runtime.plugin_base", "core.runtime.event_bus",
    "core.planning", "core.kernel", "core.supervisor", "core.brain",
    "core.cognition", "core.memory", "core.world_model",
    "core.dynamic.planning_engine", "core.dynamic.workflow_executor",
    "core.dynamic.scenario_analyzer",
    "harnix.kernel", "harnix.nodes", "harnix.state",
    "plugins.model_router", "plugins.supervisor", "plugins.memory",
    "plugins.verification_engine", "plugins.recovery_engine",
    "plugins.multi_agent", "plugins.debate_engine", "plugins.evolution_engine",
    "plugins.skill_forge", "plugins.skill_learner",
]

# Files allowed to touch legacy (shims, tests live elsewhere).
ALLOW_FILES = {"__init__.py"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    violations = []
    for area in ("src/hermes_os", "src/memory"):
        base = root / area
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts or path.name in ALLOW_FILES:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in IMPORT_RE.finditer(text):
                mod = ((m.group(1) or m.group(2)).split(",")[0].strip())
                mod = re.split(r"\s+as\s+", mod)[0].strip()
                if mod.startswith("."):
                    continue
                for leg in LEGACY:
                    if mod == leg or mod.startswith(leg + "."):
                        violations.append(f"{path.as_posix()}: imports legacy {mod}")
    if violations:
        print("CANONICAL VIOLATIONS:")
        for v in violations:
            print("  " + v)
        return 1
    print("canonical imports OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
